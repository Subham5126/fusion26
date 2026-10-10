"""Presets must produce distinct, genuinely detected/associated objects."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.job_manager import job_manager


@pytest.mark.parametrize('preset,count', [('1',2), ('2',2), ('3',3), ('4',3)])
def test_demo_preset_real_pipeline(preset, count):
    with TestClient(app) as client:
        response = client.post(f'/api/analyze/demo?preset={preset}')
        assert response.status_code == 202, response.text
        job = response.json()['job_id']
        try:
            assert client.get(f'/api/jobs/{job}').json()['status'] == 'succeeded'
            result = client.get(f'/api/jobs/{job}/result').json()
            assert result['source_type'] == 'synthetic'
            assert result['sequence_id'].startswith(f'demo-{preset}-')
            assert len(result['detections']) == 5*count
            assert len(result['tracks']) == count
            for track in result['tracks']:
                assert track['status'] == 'confirmed'
                assert [p['frame_index'] for p in track['points']] == list(range(5))
            manifest = client.get(f'/api/jobs/{job}/manifest').json()
            assert all((f['width_px'],f['height_px']) == (640,480) for f in manifest['frames'])
            assert client.get(f'/api/jobs/{job}/frames/4').headers['content-type'] == 'image/png'
        finally:
            for collection in (job_manager.jobs,job_manager.results,job_manager.frames,job_manager.manifests,job_manager.diagnostics):
                collection.pop(job,None)


def test_unknown_demo_preset_does_not_create_job():
    existing = set(job_manager.jobs)
    with TestClient(app) as client:
        assert client.post('/api/analyze/demo?preset=5').status_code == 422
    assert set(job_manager.jobs) == existing
