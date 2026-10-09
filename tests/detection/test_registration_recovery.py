"""T13: recover a wrong coarse seed without accepting a chained transform."""
from pathlib import Path
import builtins
import json

import cv2
import numpy as np
import pytest

from app.schemas.sequence import SequenceInput
from astrotrace.preprocessing.registration import register_sequence
from astrotrace.preprocessing.registration_fixtures import create_registration_fixture
from orbittrace.cv_tracking import analyze_telescope_sequence


def test_neighbor_only_initializes_independently_validated_frame_zero_fit(monkeypatch):
    scene = create_registration_fixture()
    original = cv2.phaseCorrelate
    calls = 0

    def wrong_last_seed(*args, **kwargs):
        nonlocal calls
        calls += 1
        return ((190., 0.), .5) if calls == 4 else original(*args, **kwargs)

    def no_files(*args, **kwargs):
        raise AssertionError('Registration must be image-only')

    before = [f.tobytes() for f in scene.frames]
    monkeypatch.setattr(cv2, 'phaseCorrelate', wrong_last_seed)
    monkeypatch.setattr(builtins, 'open', no_files)
    monkeypatch.setattr(Path, 'open', no_files)
    result = register_sequence(scene.frames)
    assert result.status == 'estimated'
    recovered = result.frames[4]
    assert recovered.seed_frame_index == 3
    assert recovered.direct_failure_reasons
    assert recovered.validation_inliers >= 4 and recovered.validation_rmse_px <= .8
    assert recovered.fit_inliers >= 12 and recovered.fit_inlier_ratio >= .6
    np.testing.assert_allclose(np.asarray(recovered.raw_to_reference)[:2, 2],
                               -scene.camera_shifts_xy[4], atol=.12)
    np.testing.assert_allclose(recovered.transform_points(scene.background_reference_xy
                               + scene.camera_shifts_xy[4]), scene.background_reference_xy, atol=.12)
    np.testing.assert_allclose(recovered.transform_points(recovered.transform_points(
                               [[50., 60.]], inverse=True)), [[50., 60.]], atol=1e-10)
    assert before == [f.tobytes() for f in scene.frames]
    json.dumps(result.to_dict(), allow_nan=False)


@pytest.mark.parametrize('bad', ['rotation', 'unrelated'])
def test_retry_still_rejects_bad_last_frame_after_four_valid_frames(bad):
    frames = list(create_registration_fixture().frames)
    frames[4] = (cv2.warpAffine(frames[0], cv2.getRotationMatrix2D((128,96),5,1), (256,192))
                 if bad == 'rotation' else create_registration_fixture(seed=99).frames[4])
    result = register_sequence(frames)
    assert result.frames[3].status == 'estimated'
    assert result.frames[4].status == 'failed'
    assert result.frames[4].raw_to_reference is None


@pytest.mark.parametrize('config', [{'neighbor_retry':2}, {'neighbor_retry':True},
                                   {'retry_flow_window_px':20}, {'retry_flow_window_px':100}])
def test_retry_config_is_bounded(config):
    with pytest.raises(ValueError):
        register_sequence(create_registration_fixture().frames, config)


@pytest.mark.parametrize('sequence_id', ['138', '1003'])
def test_requested_real_sequences_are_consumed_by_actual_pipeline(sequence_id):
    folder = Path(__file__).resolve().parents[2] / 'data/raw/SpotGEOv2/test' / sequence_id
    if not folder.is_dir():
        pytest.skip('Optional local ESA sequence unavailable')
    frames = [cv2.imread(str(folder/f'{i}.png'), cv2.IMREAD_UNCHANGED) for i in range(1,6)]
    manifest = SequenceInput(schema_version='0.1.0', sequence_id=f'esa-test-{sequence_id}',
        source_type='user_upload', profile='spotgeo', frames=[dict(frame_index=i,
        image_ref=f'frame_{i}', width_px=640, height_px=480, timestamp_s=None) for i in range(5)])
    diagnostics = {}
    result = analyze_telescope_sequence(frames, sequence=manifest, diagnostics=diagnostics)
    assert result.status == 'succeeded' and result.registration.status == 'estimated'
    assert all(d.x_reference_px is not None for d in result.detections)
    if sequence_id == '1003':
        assert register_sequence(frames, {'neighbor_retry':0}).status == 'failed'
        recovered = diagnostics['registration']['frames'][4]
        assert recovered['seed_frame_index'] == 3 and recovered['validation_inliers'] >= 4
        assert recovered['validation_rmse_px'] <= .8
