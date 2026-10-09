"""Deployment memory cap evicts completed jobs without dropping active work."""
import numpy as np
import pytest
from app.core.deployment import frame_retention_bytes
from app.core.config import PipelineConfig
from app.schemas.job import JobState
from app.schemas.sequence import SequenceInput
from app.services.job_manager import JobManager


def test_default_retention_preserves_local_budget(monkeypatch):
    monkeypatch.delenv('ORBITTRACE_FRAME_RETENTION_MIB', raising=False)
    assert frame_retention_bytes() == 500 * 1024 * 1024


@pytest.mark.parametrize('value', ['0', '501', '-1', '1.5', ''])
def test_unsafe_retention_budget_fails_startup(monkeypatch, value):
    monkeypatch.setenv('ORBITTRACE_FRAME_RETENTION_MIB', value)
    with pytest.raises(ValueError, match='ORBITTRACE_FRAME_RETENTION_MIB'):
        JobManager()


def test_budget_evicts_completed_frame_storage_before_reserving_next_job(monkeypatch):
    monkeypatch.setenv('ORBITTRACE_FRAME_RETENTION_MIB', '1')
    manager = JobManager()
    manager.jobs['old'] = JobState(job_id='old', status='succeeded', progress_stage='completed', warnings=[])
    manager.frames['old'] = [np.zeros(750_000, np.uint8)]
    pixels = [np.zeros((256, 256), np.uint8) for _ in range(5)]
    sequence = SequenceInput(schema_version='0.1.0', sequence_id='retention-test', source_type='user_upload',
        profile='spotgeo', frames=[{'frame_index': i, 'image_ref': f'frame_{i}', 'width_px': 256,
            'height_px': 256, 'timestamp_s': None} for i in range(5)])
    class Tasks:
        def add_task(self, *args):
            pass
    try:
        state = manager.submit_job(sequence, pixels, PipelineConfig(), Tasks())
        assert state.status == 'queued'
        assert 'old' not in manager.frames and 'old' not in manager.jobs
        assert state.job_id in manager.frames
        assert sum(p.nbytes for frames in manager.frames.values() for p in frames) <= manager.max_frame_bytes
    finally:
        manager.executor.shutdown(wait=True)
