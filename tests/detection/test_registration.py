"""T13 transform direction, independent motion, failure gating and schema bridge."""

import builtins
import importlib.util
import json
import os
from pathlib import Path
import sys

import cv2
import numpy as np
import pytest

from app.schemas.result import Detection
from astrotrace.preprocessing.registration import (
    RegistrationConfig, register_sequence, fit_translation,
    add_reference_coordinates, warp_to_reference,
)
from astrotrace.preprocessing.registration_fixtures import create_registration_fixture
from orbittrace.detection import detect_sequence


@pytest.fixture(scope='module')
def scene():
    fixture = create_registration_fixture()
    return fixture, register_sequence(fixture.frames)


@pytest.mark.parametrize('streaks', [False, True])
def test_known_subpixel_camera_shift_and_independent_target_motion(streaks):
    fixture = create_registration_fixture(streaks=streaks)
    result = register_sequence(fixture.frames)
    assert result.status == 'estimated'
    transformed_target = []
    for index, frame in enumerate(result.frames):
        np.testing.assert_allclose(np.asarray(frame.raw_to_reference)[:2, 2],
                                   -fixture.camera_shifts_xy[index], atol=.12)
        points = frame.transform_points(fixture.background_reference_xy+fixture.camera_shifts_xy[index])
        np.testing.assert_allclose(points, fixture.background_reference_xy, atol=.12)
        transformed_target.append(frame.transform_points(fixture.target_raw_xy[index:index+1])[0])
        if index:
            assert frame.validation_inliers >= 4
            assert frame.validation_rmse_px < .15
    np.testing.assert_allclose(np.diff(transformed_target, axis=0), np.tile((3., 1.5), (4, 1)), atol=.2)


def test_shift_consensus_rejects_mismatches_and_moving_objects():
    rng = np.random.default_rng(13)
    reference = rng.uniform(0, 100, (40, 2))
    raw = reference + (7.25, -4.5)
    raw[30:] += rng.uniform(12, 40, (10, 2))
    shift, inliers = fit_translation(reference, raw, .5)
    np.testing.assert_allclose(shift, (-7.25, 4.5), atol=1e-9)
    assert inliers[:30].all() and not inliers[30:].any()


def test_roundtrip_xy_direction_and_warp_validity(scene):
    fixture, result = scene
    frame = result.frames[1]
    points = np.array([[0., 0.], [255., 191.], [73.125, 98.5]])
    np.testing.assert_allclose(frame.transform_points(frame.transform_points(points), inverse=True), points, atol=1e-10)
    pixels = np.zeros((192, 256), np.uint8)
    pixels[61, 83] = 255
    aligned, valid = warp_to_reference(pixels, frame)
    yy, xx = np.mgrid[:192, :256]
    centroid = [float((aligned*xx).sum()/aligned.sum()), float((aligned*yy).sum()/aligned.sum())]
    # Bilinear interpolation can tie two peak pixels at a half-pixel shift;
    # the intensity centroid verifies transform direction without rounding ties.
    np.testing.assert_allclose(centroid, frame.transform_points([[83., 61.]])[0], atol=.04)
    assert not valid[0].all() and not valid[:, -1].all()
    assert valid[30:-30, 30:-30].all()
    assert np.all(aligned[~valid] == 0)
    assert pixels[61, 83] == 255


def test_original_pixels_and_all_raw_detection_fields_preserved(scene):
    fixture, result = scene
    original_bytes = [pixels.tobytes() for pixels in fixture.frames]
    detections = detect_sequence(fixture.frames, sequence_id='registration-preserve')
    converted = add_reference_coordinates(detections, result)
    assert len(converted) == len(detections) > 0
    for before, after in zip(detections, converted):
        assert type(after) is Detection
        assert before.x_reference_px is None
        old = before.model_dump(exclude={'x_reference_px', 'y_reference_px'})
        assert old == after.model_dump(exclude={'x_reference_px', 'y_reference_px'})
        expected = result.frames[before.frame_index].transform_points([[before.x_raw_px, before.y_raw_px]])[0]
        np.testing.assert_allclose([after.x_reference_px, after.y_reference_px], expected)
    assert [pixels.tobytes() for pixels in fixture.frames] == original_bytes
    assert all(not pixels.flags.writeable for pixels in fixture.frames)
    json.dumps([d.model_dump() for d in converted], allow_nan=False)


@pytest.mark.parametrize('kind', ['blank', 'constant', 'noise', 'single_feature'])
def test_low_feature_or_noise_scene_fails_explicitly(kind):
    rng = np.random.default_rng(13)
    frames = []
    for i in range(5):
        pixels = np.zeros((128, 160), np.uint8)
        if kind == 'constant':
            pixels.fill(60)
        elif kind == 'noise':
            pixels = np.clip(50+rng.normal(0, 10, pixels.shape), 0, 255).astype(np.uint8)
        elif kind == 'single_feature':
            pixels[50:54, 40+i:44+i] = 200
        frames.append(pixels)
    result = register_sequence(frames)
    assert result.status == 'failed'
    assert all(frame.status == 'failed' and frame.raw_to_reference is None for frame in result.frames[1:])
    with pytest.raises(ValueError, match='mix raw/reference'):
        add_reference_coordinates([], result)
    with pytest.raises(ValueError, match='failed'):
        result.frames[1].transform_points([[2., 3.]])
    with pytest.raises(ValueError, match='failed'):
        warp_to_reference(frames[1], result.frames[1])
    json.dumps(result.to_dict(), allow_nan=False)


def test_unrelated_images_and_large_transform_rejected(scene):
    fixture, _ = scene
    unrelated = create_registration_fixture(seed=99)
    assert register_sequence([fixture.frames[0], unrelated.frames[0]]).status == 'failed'
    shifted = cv2.warpAffine(fixture.frames[0], np.array([[1., 0., 60.], [0., 1., 20.]]), (256, 192))
    result = register_sequence([fixture.frames[0], shifted], {'max_shift_px': 20.})
    assert result.frames[1].status == 'failed'
    assert 'coarse_shift_exceeds_limit' in result.frames[1].warnings


def test_inadequate_overlap_is_failure(scene):
    fixture, _ = scene
    shifted = cv2.warpAffine(fixture.frames[0], np.array([[1., 0., 60.], [0., 1., 20.]]), (256, 192))
    result = register_sequence([fixture.frames[0], shifted], {'min_overlap': .95})
    assert result.frames[1].status == 'failed'


@pytest.mark.parametrize('bad', [[], 'image', [np.empty((0, 0), np.uint8)],
    [np.zeros((20, 20), np.uint8)], [np.zeros((50, 50, 3), np.uint8)],
    [np.zeros((50, 50), np.int32)], [np.full((50, 50), np.nan)],
    [np.ones((50, 50), np.float32)*2], [np.zeros((40, 40), np.uint8), np.zeros((40, 41), np.uint8)]])
def test_invalid_inputs_fail(bad):
    with pytest.raises(ValueError):
        register_sequence(bad)


@pytest.mark.parametrize('config', [{'truth': [1, 2]}, {'max_features': True},
    {'feature_snr': float('nan')}, {'min_inlier_ratio': 1.2}, {'min_inliers': 0},
    {'inlier_radius_px': -1}, {'max_shift_px': float('inf')}, 'path'])
def test_invalid_config_no_truth_or_paths(config):
    with pytest.raises(ValueError):
        RegistrationConfig.from_mapping(config)


def test_uint16_and_normalized_float_inputs_match_uint8(scene):
    fixture, base = scene
    for converted in ([p.astype(np.uint16)*257 for p in fixture.frames],
                      [p.astype(np.float32)/255 for p in fixture.frames]):
        result = register_sequence(converted)
        assert result.status == 'estimated'
        for expected, actual in zip(base.frames, result.frames):
            np.testing.assert_allclose(actual.raw_to_reference, expected.raw_to_reference, atol=.05)


def test_repeatable_inference_without_files_or_annotations(scene, monkeypatch):
    fixture, expected = scene
    def forbidden(*args, **kwargs):
        raise AssertionError('Registration inference must not read files/truth')
    monkeypatch.setattr(builtins, 'open', forbidden)
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    monkeypatch.setattr(Path, 'read_text', forbidden)
    actual = register_sequence(fixture.frames)
    assert [f.raw_to_reference for f in actual.frames] == [f.raw_to_reference for f in expected.frames]
    assert [f.inlier_flags for f in actual.frames] == [f.inlier_flags for f in expected.frames]


def test_no_double_registration_wrong_frame_or_out_of_image(scene):
    fixture, registration = scene
    original = detect_sequence(fixture.frames, sequence_id='schema-reject')[0]
    converted = add_reference_coordinates([original], registration)
    with pytest.raises(ValueError, match='previous registration'):
        add_reference_coordinates(converted, registration)
    wrong = Detection.model_validate({**original.model_dump(), 'frame_index': 5})
    with pytest.raises(ValueError, match='in-sequence'):
        add_reference_coordinates([wrong], registration)
    wrong = Detection.model_validate({**original.model_dump(), 'bbox_raw_px': (0., 0., 300., 200.)})
    with pytest.raises(ValueError, match='outside'):
        add_reference_coordinates([wrong], registration)
    assert add_reference_coordinates([], registration) == []


def test_validation_points_can_reject_false_consensus(scene, monkeypatch):
    fixture, _ = scene
    # A corrupt fit must fail on correspondences held out of the fit, instead of
    # receiving a success flag just because an estimator returned a matrix.
    monkeypatch.setattr('astrotrace.preprocessing.registration.fit_translation',
                        lambda ref, raw, radius: (np.array([20., 20.]), np.ones(len(raw), bool)))
    result = register_sequence(fixture.frames[:2])
    assert result.status == 'failed'
    assert 'validation_residual_or_support_failed' in result.frames[1].warnings
    json.dumps(result.to_dict(), allow_nan=False)


def test_rotation_not_silently_accepted_as_translation(scene):
    fixture, _ = scene
    rotated = cv2.warpAffine(fixture.frames[0], cv2.getRotationMatrix2D((128, 96), 5, 1), (256, 192))
    result = register_sequence([fixture.frames[0], rotated])
    assert result.status == 'failed'


@pytest.mark.parametrize('points', [[[float('nan'), 0]], [[1, 2, 3]], [1, 2]])
def test_invalid_transform_points(scene, points):
    _, registration = scene
    with pytest.raises(ValueError, match='finite Nx2'):
        registration.frames[1].transform_points(points)


def test_transformed_out_of_field_detection_preserves_raw_box(scene):
    _, registration = scene
    original = Detection(detection_id='border', frame_index=1, x_raw_px=.5, y_raw_px=20.,
        bbox_raw_px=(0., 19., 2., 22.), kind='compact', quality_score=.5, detector_name='authored-test')
    converted = add_reference_coordinates([original], registration)[0]
    assert converted.x_reference_px < 0  # Valid finite reference geometry; never clip.
    assert converted.x_raw_px == .5 and converted.bbox_raw_px == original.bbox_raw_px


def _snapshot_modules():
    snapshot = os.environ.get('CV_T06_TRACKING_SNAPSHOT')
    if not snapshot:
        pytest.skip('Set CV_T06_TRACKING_SNAPSHOT to actual unchanged Member3 source')
    modules = []
    for name, filename in (('_test_t13_tracker', 'tracker.py'), ('_test_t13_fit', 'fit.py')):
        path = Path(snapshot)/filename
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        modules.append(module)
    return modules


def test_latest_tracker_consumes_reference_points_preserving_raw(scene):
    module, _ = _snapshot_modules()
    fixture, result = scene
    detections = detect_sequence(fixture.frames, sequence_id='registered-tracker')
    registered = add_reference_coordinates(detections, result)
    tracks = module.Tracker().process_sequence(registered, frame_indices=range(5))
    observations = [p for t in tracks for p in t.points if p.point_type == 'observed']
    assert {p.detection_id for p in observations} == {d.detection_id for d in registered}
    by_id = {d.detection_id: d for d in registered}
    for point in observations:
        d = by_id[point.detection_id]
        assert (point.x_raw_px, point.y_raw_px) == (d.x_raw_px, d.y_raw_px)
        assert (point.x_reference_px, point.y_reference_px) == (d.x_reference_px, d.y_reference_px)


def test_actual_isolated_target_detections_track_independent_compensated_motion():
    module, trajectory = _snapshot_modules()
    fixture = create_registration_fixture(streaks=True, isolated_target=True)
    registration = register_sequence(fixture.frames)
    detections = detect_sequence(fixture.frames, sequence_id='independent-moving-target')
    registered = add_reference_coordinates(detections, registration)
    tracks = module.Tracker().process_sequence(registered, frame_indices=range(5))
    fitted = trajectory.attach_trajectories(tracks, coordinate_frame='reference_frame_0',
        time_basis='frame', frame_dimensions=(256, 192))
    # Truth is used ONLY for post-inference identification/evaluation; all track
    # observations above were actual detector outputs, never truth positions.
    target_ids = set()
    for index in range(5):
        candidates = [d for d in registered if d.frame_index == index]
        best = min(candidates, key=lambda d: np.linalg.norm(np.array([d.x_reference_px, d.y_reference_px])-fixture.target_reference_xy[index]))
        assert np.linalg.norm(np.array([best.x_reference_px, best.y_reference_px])-fixture.target_reference_xy[index]) < .15
        target_ids.add(best.detection_id)
    target_tracks = [t for t in fitted if target_ids <= {p.detection_id for p in t.points}]
    assert len(target_tracks) == 1
    track = target_tracks[0]
    assert track.status == 'confirmed' and track.observed_count == 5
    assert track.trajectory.vx == pytest.approx(3., abs=.05)
    assert track.trajectory.vy == pytest.approx(1.5, abs=.05)
    assert all(p.point_type == 'observed' for p in track.points)
    assert all(p.point_type == 'extrapolated' and p.detection_id is None for p in track.trajectory.predictions)
