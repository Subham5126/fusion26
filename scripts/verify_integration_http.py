"""Fresh local TCP evidence, preserving datasets and historical reports."""
import argparse
import json
from pathlib import Path
import time
import cv2
import httpx
from PIL import Image
from app.schemas.result import AnalysisResult
from astrotrace.datasets import SpotGeoDataset
from astrotrace.datasets.stress import create_stress_scene
from astrotrace.preprocessing.registration_fixtures import create_registration_fixture
import numpy as np

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8000')
    parser.add_argument('--origin',default='http://127.0.0.1:5174',help='Actual browser frontend origin for CORS verification')
    parser.add_argument('--esa',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); args.output.mkdir(parents=True,exist_ok=False)
    with httpx.Client(base_url=args.url,timeout=60) as client:
        receipt={'url':args.url,'checks':{},'cases':[]}
        for path in ['/api/health','/docs','/openapi.json']:
            response=client.get(path); assert response.status_code==200
            receipt['checks'][path]=response.status_code
        response=client.options('/api/analyze/upload',headers={'Origin':args.origin,'Access-Control-Request-Method':'POST'})
        assert response.headers['access-control-allow-origin']==args.origin
        receipt['checks']['cors']=response.status_code
        def poll(name,response,frames=None,expected='succeeded',error=None):
            assert response.status_code==202,response.text
            polling_started = time.perf_counter()
            job=response.json()['job_id']; states=[]
            for _ in range(300):
                state=client.get(f'/api/jobs/{job}').json(); states.append(state['status'])
                if state['status'] in ('succeeded','failed'): break
                time.sleep(.1)
            assert state['status']==expected,state
            result_response=client.get(f'/api/jobs/{job}/result')
            case={'name':name,'submission_http':202,'job_id':job,'poll_states':states,'state':state,'result_http':result_response.status_code,
                'submission_http_s':response.elapsed.total_seconds(),
                'poll_to_result_s':round(time.perf_counter() - polling_started, 4)}
            if error: assert state['error']['code']==error,state
            if expected=='succeeded':
                assert result_response.status_code==200
                result=AnalysisResult.model_validate(result_response.json())
                assert result.metrics is None
                case.update(detections_per_frame=[sum(d.frame_index==i for d in result.detections) for i in range(5)],
                    tracks=len(result.tracks),confirmed_tracks=sum(t.status=='confirmed' for t in result.tracks),
                    fitted_trajectories=sum(t.trajectory is not None for t in result.tracks),registration=result.registration.status)
                (args.output/f'{name}_result.json').write_text(result.model_dump_json(indent=2),encoding='utf-8')
                for format in ('json','csv'):
                    export=client.get(f'/api/jobs/{job}/exports/{format}'); assert export.status_code==200
                for index in range(5):
                    frame=client.get(f'/api/jobs/{job}/frames/{index}'); assert frame.status_code==200
                    if frames is not None:
                        decoded=cv2.imdecode(np.frombuffer(frame.content,np.uint8),cv2.IMREAD_UNCHANGED)
                        assert np.array_equal(decoded,frames[index])
            else: assert result_response.status_code==409
            diagnostics=client.get(f'/api/jobs/{job}/diagnostics'); assert diagnostics.status_code==200
            (args.output/f'{name}_diagnostics.json').write_text(json.dumps(diagnostics.json(),indent=2),encoding='utf-8')
            receipt['cases'].append(case)
            return case
        def post(name,frames,expected='succeeded',error=None):
            folder=args.output/name; folder.mkdir()
            for i,pixels in enumerate(frames): Image.fromarray(pixels).save(folder/f'{i+1}.png')
            manifest={'schema_version':'0.1.0','sequence_id':name,'source_type':'user_upload','profile':'spotgeo',
                'frames':[{'frame_index':i,'image_ref':f'frame_{i}','width_px':p.shape[1],'height_px':p.shape[0],'timestamp_s':None} for i,p in enumerate(frames)]}
            (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
            files=[('files',(f'{i+1}.png',cv2.imencode('.png',pixels)[1].tobytes(),'image/png')) for i,pixels in enumerate(frames)]
            return poll(name,client.post('/api/analyze/upload',data={'manifest':json.dumps(manifest)},files=files),frames,expected,error)
        demo=poll('synthetic-demo',client.post('/api/analyze/demo'))
        assert demo['confirmed_tracks']>=1 and demo['fitted_trajectories']>=1
        counts=post('counts-change',create_stress_scene('counts_change').frames)
        assert counts['detections_per_frame']==[5,3,4,5,5] and counts['confirmed_tracks']==5
        empty=post('empty-targets',create_stress_scene('empty_targets').frames)
        assert empty['tracks']==0 and empty['detections_per_frame']==[0]*5
        post('daylight-like',create_stress_scene('daylight_like').frames,'failed','unsupported_observation')
        post('noise-only',create_stress_scene('noise_only').frames,'failed','uncertain_observation')
        rotated=list(create_registration_fixture().frames)
        rotated[1]=cv2.warpAffine(rotated[0],cv2.getRotationMatrix2D((128,96),5,1),(256,192))
        post('registration-failure',rotated,'failed','registration_failed')
        for sid,expected,error in [('84','succeeded',None),('438','failed','registration_failed')]:
            sequence=SpotGeoDataset(args.esa,split='train').load_sequence(sid)
            post(f'esa-train-{sid}',[f.pixels for f in sequence.frames],expected,error)
        frames=create_stress_scene('empty_targets').frames
        manifest=json.loads((args.output/'empty-targets/manifest.json').read_text())
        files=[('files',(f'{i}.png',cv2.imencode('.png',p)[1].tobytes(),'image/png')) for i,p in enumerate(frames)]
        for name,badfiles,status in [('wrong-count',files[:4],422),('invalid-type',[('files',('bad.txt',b'bad','text/plain'))]+files[1:],422),
                                    ('oversized-file',[('files',('big.png',b'x'*(10*1024*1024+1),'image/png'))]+files[1:],413)]:
            response=client.post('/api/analyze/upload',data={'manifest':json.dumps(manifest)},files=badfiles)
            assert response.status_code==status,response.text
            receipt['checks'][name]={'status':status,'error':response.json()}
        (args.output/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        for case in receipt['cases']: print(json.dumps({k:case.get(k) for k in ('name','state','detections_per_frame','tracks','fitted_trajectories')}))
        print('HTTP evidence:',args.output/'receipt.json')
    return 0

if __name__=='__main__': raise SystemExit(main())
