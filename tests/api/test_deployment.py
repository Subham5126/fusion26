"""Production startup and error confidentiality, without changing scientific contracts."""
import asyncio
import pytest
from fastapi.testclient import TestClient
from app.core.deployment import cors_origins, public_mode, LOCAL_ORIGINS
from app.main import app
from app.schemas.job import JobState
from app.services.job_manager import JobManager

def test_default_local_cors_is_preserved(monkeypatch):
    monkeypatch.delenv('ORBITTRACE_CORS_ORIGINS', raising=False)
    monkeypatch.delenv('ORBITTRACE_PUBLIC_MODE', raising=False)
    assert not public_mode()
    assert cors_origins() == LOCAL_ORIGINS

def test_public_startup_requires_explicit_origin(monkeypatch):
    monkeypatch.setenv('ORBITTRACE_PUBLIC_MODE', '1')
    monkeypatch.delenv('ORBITTRACE_CORS_ORIGINS', raising=False)
    with pytest.raises(ValueError, match='requires ORBITTRACE_CORS_ORIGINS'):
        cors_origins()
    monkeypatch.setenv('ORBITTRACE_CORS_ORIGINS', 'https://frontend.azurestaticapps.net/, https://frontend.azurestaticapps.net')
    assert cors_origins() == ['https://frontend.azurestaticapps.net']

@pytest.mark.parametrize('origin', ['*', 'https://*.example.test', 'http://example.test', 'https://u:p@example.test',
    'https://example.test/private', 'https://example.test?token=secret', '', 'http://127.0.0.1:5192'])
def test_public_cors_rejects_unsafe_origins(monkeypatch, origin):
    monkeypatch.setenv('ORBITTRACE_PUBLIC_MODE', '1')
    monkeypatch.setenv('ORBITTRACE_CORS_ORIGINS', origin)
    with pytest.raises(ValueError):
        cors_origins()

def test_public_job_error_does_not_disclose_internal_paths(monkeypatch):
    monkeypatch.setenv('ORBITTRACE_PUBLIC_MODE', '1')
    def fail(*args, **kwargs):
        raise RuntimeError('/private/internal/file with sensitive details')
    monkeypatch.setattr('app.services.job_manager.analyze', fail)
    manager = JobManager()
    manager.jobs['test-job'] = JobState(job_id='test-job', status='queued', progress_stage='queued', warnings=[])
    manager.diagnostics['test-job'] = {}
    try:
        asyncio.run(manager._run_job('test-job', None, [], None))
        error = manager.jobs['test-job'].error
        assert error.code == 'pipeline_error'
        assert error.message == 'Analysis could not be completed. Retry with supported telescope images.'
        assert error.details is None
    finally:
        manager.executor.shutdown(wait=True)

def test_public_invalid_manifest_does_not_echo_private_input(monkeypatch):
    monkeypatch.setenv('ORBITTRACE_PUBLIC_MODE', '1')
    response = TestClient(app).post('/api/analyze/upload', data={'manifest': '{"private_key":"sensitive-value"}'},
        files=[('files', ('bad.png', b'not png', 'image/png'))])
    assert response.status_code == 422
    assert 'sensitive-value' not in response.text
    assert 'sequence contract' in response.json()['error']['message']
