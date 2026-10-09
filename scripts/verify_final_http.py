"""Final-workspace HTTP proof using existing generators and production contracts."""
import argparse, importlib.util, json, subprocess, sys, time
from urllib.parse import urlsplit
from pathlib import Path
import cv2
import httpx
from app.schemas.result import AnalysisResult

# Isolated Python (-I) deliberately omits the script directory from sys.path.
# Load this repository's existing generator by its exact sibling path.
_generator_spec = importlib.util.spec_from_file_location(
    "_orbittrace_http_generator", Path(__file__).with_name("verify_cv_track_01.py")
)
_generator = importlib.util.module_from_spec(_generator_spec)
_generator_spec.loader.exec_module(_generator)
one_object_frames = _generator.one_object_frames

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:5173')
    parser.add_argument('--origin',help='Actual frontend origin when backend uses a separate hostname')
    parser.add_argument('--esa',type=Path,default=Path(__file__).resolve().parents[1]/'data/raw/SpotGEOv2')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    subprocess.run([sys.executable,str(Path(__file__).with_name('verify_integration_http.py')),
        '--url',args.url,'--origin',args.origin or args.url.rstrip('/'),'--esa',str(args.esa),'--output',str(args.output)],check=True)
    receipt_path=args.output/'receipt.json'
    receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
    frames=one_object_frames()
    name='synthetic-upload';folder=args.output/name;folder.mkdir()
    manifest={'schema_version':'0.1.0','sequence_id':name,'source_type':'user_upload','profile':'spotgeo',
        'frames':[{'frame_index':i,'image_ref':f'frame_{i}','width_px':p.shape[1],'height_px':p.shape[0],'timestamp_s':None} for i,p in enumerate(frames)]}
    files=[]
    for i,pixels in enumerate(frames):
        data=cv2.imencode('.png',pixels)[1].tobytes()
        (folder/f'{i+1}.png').write_bytes(data)
        files.append(('files',(f'{i+1}.png',data,'image/png')))
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    with httpx.Client(base_url=args.url,timeout=60) as client:
        submission=client.post('/api/analyze/upload',data={'manifest':json.dumps(manifest)},files=files)
        assert submission.status_code==202,submission.text
        job=submission.json()['job_id'];states=[]
        polling_started = time.perf_counter()
        for _ in range(300):
            state=client.get(f'/api/jobs/{job}').json();states.append(state['status'])
            if state['status'] in ('succeeded','failed'):break
            time.sleep(.1)
        assert state['status']=='succeeded',state
        response=client.get(f'/api/jobs/{job}/result');assert response.status_code==200
        result=AnalysisResult.model_validate(response.json())
        assert [sum(d.frame_index==i for d in result.detections) for i in range(5)]==[1]*5
        assert len(result.tracks)==1 and result.tracks[0].status=='confirmed' and result.tracks[0].trajectory
        assert result.time_basis=='frame' and result.metrics is None
        assert all(p.timestamp_s is None for t in result.tracks for p in t.points+t.trajectory.predictions)
        (args.output/f'{name}_result.json').write_text(result.model_dump_json(indent=2),encoding='utf-8')
        diagnostic=client.get(f'/api/jobs/{job}/diagnostics');assert diagnostic.status_code==200
        (args.output/f'{name}_diagnostics.json').write_text(json.dumps(diagnostic.json(),indent=2,allow_nan=False),encoding='utf-8')
        receipt['cases'].append({'name':name,'submission_http':202,'job_id':job,'poll_states':states,'state':state,
            'result_http':200,'detections_per_frame':[1]*5,'tracks':1,'confirmed_tracks':1,'fitted_trajectories':1,'registration':result.registration.status,
            'submission_http_s':submission.elapsed.total_seconds(),
            'poll_to_result_s':round(time.perf_counter() - polling_started, 4)})
        for case in receipt['cases']:
            response=client.get(f"/api/jobs/{case['job_id']}/manifest");assert response.status_code==200
            native=response.json();assert native['frame_count']==5
            diagnostics=client.get(f"/api/jobs/{case['job_id']}/diagnostics").json()
            timestamps=[f['timestamp_s'] for f in native['frames']]
            assert timestamps==[f['timestamp_s'] for f in diagnostics['sequence']['frames']]
            if case['name']!='synthetic-demo': assert all(t is None for t in timestamps)
        url=urlsplit(args.url)
        origin=args.origin or f'{url.scheme}://{url.netloc}'
        cors=client.options('/api/analyze/upload',headers={'Origin':origin,'Access-Control-Request-Method':'POST'})
        assert cors.headers['access-control-allow-origin']==origin
        receipt['checks']['final-origin-cors']=cors.status_code
    receipt_path.write_text(json.dumps(receipt,indent=2,allow_nan=False),encoding='utf-8')
    print('Final HTTP verification:',len(receipt['cases']),'genuine jobs; manifest timestamps preserved, upload timestamps unknown.')

if __name__=='__main__': main()
