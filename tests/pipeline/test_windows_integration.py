"""Real algorithms and HTTP bounds; truth never supplies observations."""
import asyncio
import io
import json
import cv2
import httpx
import numpy as np
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import PipelineConfig
from app.core import upload
from app.services.job_manager import JobManager
from astrotrace.datasets.stress import create_stress_scene
from astrotrace.preprocessing.registration_fixtures import create_registration_fixture
from orbittrace.pipeline import analyze

def manifest(frames, source='user_upload'):
    return {'schema_version':'0.1.0', 'sequence_id':'integration-sequence', 'source_type':source, 'profile':'spotgeo',
        'frames':[{'frame_index':i,'image_ref':f'frame_{i}','width_px':p.shape[1],'height_px':p.shape[0], 'timestamp_s':None} for i,p in enumerate(frames)]}

def submit(client, frames):
    return client.post('/api/analyze/upload', data={'manifest':json.dumps(manifest(frames))},
        files=[('files',(f'{i}.png',cv2.imencode('.png',p)[1].tobytes(),'image/png')) for i,p in enumerate(frames)])

@pytest.mark.parametrize('case,counts', [('counts_change',[5,3,4,5,5]), ('empty_targets',[0,0,0,0,0])])
def test_registered_upload_true_observations_and_exports(case, counts):
    frames=create_stress_scene(case).frames
    with TestClient(app) as client:
        response=submit(client,frames)
        assert response.status_code==202
        job=response.json()['job_id']
        state=client.get(f'/api/jobs/{job}').json()
        assert state['status']=='succeeded',state
        result=client.get(f'/api/jobs/{job}/result').json()
        assert [sum(d['frame_index']==i for d in result['detections']) for i in range(5)]==counts
        assert result['registration']['status']=='estimated' and result['metrics'] is None
        diagnostic=client.get(f'/api/jobs/{job}/diagnostics').json()
        assert len(diagnostic['registration']['frames'])==5
        assert diagnostic['sequence']['input_sha256']==result['provenance']['input_sha256']
        if case=='counts_change':
            assert sum(t['status']=='confirmed' for t in result['tracks'])==5
            assert all(t['trajectory'] is not None for t in result['tracks'])
            assert all(p['detection_id'] is None for t in result['tracks'] for p in t['trajectory']['predictions'])
        assert client.get(f'/api/jobs/{job}/exports/json').json()==result
        csv=client.get(f'/api/jobs/{job}/exports/csv')
        assert csv.status_code==200 and 'point_type' in csv.text
        assert client.get(f'/api/jobs/{job}/frames/4').headers['content-type']=='image/png'

@pytest.mark.parametrize('case,code', [('daylight_like','unsupported_observation'),('noise_only','uncertain_observation')])
def test_unsuitable_upload_has_error_and_no_success(case,code):
    with TestClient(app) as client:
        response=submit(client,create_stress_scene(case).frames)
        assert response.status_code==202
        job=response.json()['job_id']
        state=client.get(f'/api/jobs/{job}').json()
        assert state['status']=='failed' and state['error']['code']==code
        assert client.get(f'/api/jobs/{job}/result').status_code==409
        assert client.get(f'/api/jobs/{job}/exports/json').status_code==409

def test_supported_registration_failure_blocks_whole_stream():
    frames=list(create_registration_fixture().frames)
    frames[1]=cv2.warpAffine(frames[0],cv2.getRotationMatrix2D((128,96),5,1),(256,192))
    with TestClient(app) as client:
        response=submit(client,frames)
        assert response.status_code==202
        job=response.json()['job_id']
        state=client.get(f'/api/jobs/{job}').json()
        assert state['status']=='failed' and state['error']['code']=='registration_failed'
        diagnostic=client.get(f'/api/jobs/{job}/diagnostics').json()
        assert diagnostic['suitability']['status']=='supported'
        assert diagnostic['registration']['frames'][1]['raw_to_reference'] is None

def test_pixel_metadata_and_no_ground_truth_io(monkeypatch):
    from app.schemas.sequence import SequenceInput
    from pathlib import Path
    import builtins
    scene=create_stress_scene('counts_change')
    copies=[p.copy() for p in scene.frames]
    def forbidden(*args,**kwargs): raise AssertionError('Inference attempted file IO')
    monkeypatch.setattr(builtins,'open',forbidden)
    monkeypatch.setattr(Path,'open',forbidden)
    result=analyze(SequenceInput.model_validate(manifest(scene.frames)),PipelineConfig(),frame_pixels=scene.frames)
    assert len(result.detections)==22
    assert all(np.array_equal(a,b) for a,b in zip(scene.frames,copies))
    assert len({d.detection_id for d in result.detections})==22

def test_decode_checks_large_header_before_allocation():
    from types import SimpleNamespace
    stream=io.BytesIO(); Image.new('L',(2001,2000)).save(stream,format='PNG')
    from app.schemas.sequence import FrameInput
    meta=FrameInput(frame_index=0,image_ref='frame_0',width_px=320,height_px=240)
    with pytest.raises(Exception,match='4 megapixels'):
        upload.decode_upload(stream.getvalue(),SimpleNamespace(filename='huge.png',content_type='image/png'),meta)

@pytest.mark.parametrize('kind', ['invalid_type','corrupt','wrong_count','too_large','rgb'])
def test_upload_validation(kind):
    frames=create_stress_scene('empty_targets').frames
    encoded=cv2.imencode('.png',frames[0])[1].tobytes()
    files=[('files',(f'{i}.png',encoded,'image/png')) for i in range(5)]
    if kind=='invalid_type': files[0]=('files',('bad.txt',encoded,'text/plain'))
    if kind=='corrupt': files[0]=('files',('bad.png',b'not an image','image/png'))
    if kind=='wrong_count': files=files[:4]
    if kind=='too_large': files[0]=('files',('big.png',b'x'*(10*1024*1024+1),'image/png'))
    if kind=='rgb': files[0]=('files',('color.png',cv2.imencode('.png',np.repeat(frames[0][...,None],3,axis=2))[1].tobytes(),'image/png'))
    with TestClient(app) as client:
        response=client.post('/api/analyze/upload',data={'manifest':json.dumps(manifest(frames))},files=files)
        assert response.status_code==(413 if kind=='too_large' else 422)

def test_request_stream_limit_without_content_length(monkeypatch):
    monkeypatch.setattr(upload,'REQUEST_BYTES',256)
    async def check():
        async def body():
            yield b'--boundary\r\nContent-Disposition: form-data; name="manifest"\r\n\r\n'
            yield b'x'*512
            yield b'\r\n--boundary--\r\n'
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            response=await client.post('/api/analyze/upload',content=body(),headers={'content-type':'multipart/form-data; boundary=boundary'})
            assert response.status_code==413,response.text
    asyncio.run(check())

def test_job_capacity_is_reserved_atomically():
    manager=JobManager()
    from app.schemas.sequence import SequenceInput
    frames=create_stress_scene('empty_targets').frames
    class Tasks:
        def add_task(self,*args): pass
    manager.submit_job(SequenceInput.model_validate(manifest(frames)),frames,PipelineConfig(),Tasks())
    with pytest.raises(RuntimeError,match='Capacity'):
        manager.submit_job(SequenceInput.model_validate(manifest(frames)),frames,PipelineConfig(),Tasks())
    manager.executor.shutdown()
