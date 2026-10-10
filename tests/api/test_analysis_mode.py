"""The additive mode form must stay opt-in and cannot silently weaken registration."""
import json
import cv2
import pytest
from fastapi.testclient import TestClient
from app.main import app
from astrotrace.datasets.stress import create_stress_scene
from app.services.job_manager import job_manager


@pytest.mark.parametrize('mode',[None,'standard','temporal'])
def test_upload_mode_reaches_pipeline_and_preserves_original_proposals(mode):
    frames=create_stress_scene('counts_change').frames
    manifest={'schema_version':'0.1.0','sequence_id':'release-mode','source_type':'user_upload','profile':'spotgeo',
        'frames':[dict(frame_index=i,image_ref=f'frame_{i}',width_px=f.shape[1],height_px=f.shape[0],timestamp_s=None) for i,f in enumerate(frames)]}
    files=[('files',(f'{i}.png',cv2.imencode('.png',f)[1].tobytes(),'image/png')) for i,f in enumerate(frames)]
    data={'manifest':json.dumps(manifest)}
    if mode is not None:data['analysis_mode']=mode
    with TestClient(app) as client:
        response=client.post('/api/analyze/upload',data=data,files=files)
        assert response.status_code==202,response.text
        job=response.json()['job_id']
        try:
            assert client.get(f'/api/jobs/{job}').json()['status']=='succeeded'
            diagnostics=client.get(f'/api/jobs/{job}/diagnostics').json()
            assert diagnostics['config']['shared']['analysis_mode']==(mode or 'standard')
            assert diagnostics['config']['shared']['gate_distance_px']==(25 if mode=='temporal' else 20)
            result=client.get(f'/api/jobs/{job}/result').json()
            assert result['schema_version']=='0.1.0' and result['registration']['status']=='estimated'
            assert ('original_detections' in diagnostics)==(mode=='temporal')
        finally:
            for collection in (job_manager.jobs,job_manager.results,job_manager.frames,job_manager.manifests,job_manager.diagnostics):collection.pop(job,None)


def test_unknown_mode_is_rejected_before_inference():
    existing=set(job_manager.jobs)
    with TestClient(app) as client:
        response=client.post('/api/analyze/upload',data={'manifest':'{}','analysis_mode':'unverified-ai'},
            files=[('files',('x.png',b'x','image/png'))])
        assert response.status_code==422
        assert response.json()['error']['code']=='invalid_input'
        assert set(job_manager.jobs)==existing
