"""New manifest contract survives CV integration, native decoding and failures."""
import json
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.result import AnalysisResult
from astrotrace.datasets.stress import create_stress_scene

def payload(frames):
    return {'schema_version':'0.1.0','sequence_id':'latest-native-test','source_type':'user_upload','profile':'spotgeo',
        'frames':[{'frame_index':i,'image_ref':f'frame_{i}','width_px':p.shape[1],'height_px':p.shape[0],'timestamp_s':None} for i,p in enumerate(frames)]}

def files(frames):
    return [('files',(f'{i}.png',cv2.imencode('.png',p)[1].tobytes(),'image/png')) for i,p in enumerate(frames)]

def test_native_16bit_tracking_manifest_diagnostics_and_exports():
    frames=tuple(p.astype(np.uint16)*257 for p in create_stress_scene('counts_change').frames)
    with TestClient(app) as client:
        response=client.post('/api/analyze/upload',data={'manifest':json.dumps(payload(frames))},files=files(frames))
        assert response.status_code==202
        job=response.json()['job_id']
        assert client.get(f'/api/jobs/{job}').json()['status']=='succeeded'
        result=AnalysisResult.model_validate(client.get(f'/api/jobs/{job}/result').json())
        assert len(result.detections)==22 and sum(t.status=='confirmed' for t in result.tracks)==5
        assert all(t.trajectory and t.trajectory.speed_unit=='px/frame' for t in result.tracks)
        manifest=client.get(f'/api/jobs/{job}/manifest').json()
        assert manifest['frame_count']==5 and all(f['timestamp_s'] is None for f in manifest['frames'])
        diagnostic=client.get(f'/api/jobs/{job}/diagnostics').json()
        assert diagnostic['registration']['status']=='estimated'
        assert diagnostic['sequence']['input_sha256']==result.provenance.input_sha256
        for i,pixels in enumerate(frames):
            frame=client.get(f'/api/jobs/{job}/frames/{i}')
            decoded=cv2.imdecode(np.frombuffer(frame.content,np.uint8),cv2.IMREAD_UNCHANGED)
            assert np.array_equal(decoded,pixels) and decoded.dtype==np.uint16
        assert client.get(f'/api/jobs/{job}/exports/json').json()==result.model_dump(mode='json')
        assert 'extrapolated' in client.get(f'/api/jobs/{job}/exports/csv').text

@pytest.mark.parametrize('case,code',[('daylight_like','unsupported_observation'),('noise_only','uncertain_observation')])
def test_scientific_failure_preserves_manifest_and_has_no_result(case,code):
    frames=create_stress_scene(case).frames
    with TestClient(app) as client:
        response=client.post('/api/analyze/upload',data={'manifest':json.dumps(payload(frames))},files=files(frames))
        job=response.json()['job_id']
        assert client.get(f'/api/jobs/{job}').json()['error']['code']==code
        assert client.get(f'/api/jobs/{job}/manifest').json()['frame_count']==5
        assert client.get(f'/api/jobs/{job}/result').status_code==409
        assert client.get(f'/api/jobs/{job}/exports/json').status_code==409

def test_cors_and_predecode_request_budget():
    with TestClient(app) as client:
        response=client.options('/api/analyze/upload',headers={'Origin':'http://127.0.0.1:5174','Access-Control-Request-Method':'POST'})
        assert response.headers['access-control-allow-origin']=='http://127.0.0.1:5174'
        response=client.post('/api/analyze/upload',content=b'',headers={'Content-Length':str(52*1024*1024)})
        assert response.status_code==413 and response.json()['error']['code']=='upload_too_large'
