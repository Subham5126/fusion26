import builtins
from pathlib import Path
import numpy as np
import pytest
from app.core.config import PipelineConfig
from app.schemas.sequence import SequenceInput
from astrotrace.datasets.stress import create_stress_scene
from orbittrace.cv_tracking import analyze_telescope_sequence


def manifest(frames):
    return SequenceInput(schema_version='0.1.0',sequence_id='temporal-test',source_type='user_upload',profile='spotgeo',
        frames=[dict(frame_index=i,image_ref=f'frame_{i}',width_px=f.shape[1],height_px=f.shape[0],timestamp_s=None) for i,f in enumerate(frames)])


@pytest.mark.parametrize('case',['counts_change','empty_targets','camera_motion'])
def test_temporal_mode_is_image_only_native_finite_and_preserves_originals(monkeypatch,case):
    frames=create_stress_scene(case).frames;before=[f.copy() for f in frames];seq=manifest(frames)
    standard=analyze_telescope_sequence(frames,sequence=seq);diagnostic={}
    def forbidden(*args,**kwargs): raise AssertionError('Inference read a file/label')
    monkeypatch.setattr(builtins,'open',forbidden);monkeypatch.setattr(Path,'open',forbidden)
    result=analyze_telescope_sequence(frames,sequence=seq,config=PipelineConfig(analysis_mode='temporal',gate_distance_px=25),diagnostics=diagnostic)
    assert [d['detection_id'] for d in diagnostic['original_detections']]==[d.detection_id for d in standard.detections]
    assert len({d.detection_id for d in result.detections})==len(result.detections)
    assert all(np.array_equal(a,b) for a,b in zip(frames,before))
    for d in result.detections:
        x0,y0,x1,y1=d.bbox_raw_px; h,w=frames[d.frame_index].shape
        assert 0<=x0<=d.x_raw_px<x1<=w and 0<=y0<=d.y_raw_px<y1<=h
        assert 0<=d.quality_score<=1 and d.detector_name=='opencv_temporal_residual_v1'
        reg=diagnostic['registration']['frames'][d.frame_index]
        native=np.array(reg['reference_to_raw']) @ [d.x_reference_px,d.y_reference_px,1]
        assert np.allclose(native[:2],[d.x_raw_px,d.y_raw_px])
    if case=='empty_targets': assert not result.detections and not result.tracks
    else: assert any(t.observed_count>=3 for t in result.tracks)


def test_mode_default_remains_standard_and_only_known_modes_are_accepted():
    assert PipelineConfig().analysis_mode=='standard'
    with pytest.raises(ValueError): PipelineConfig(analysis_mode='fake-ai')
