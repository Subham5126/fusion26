"""Behavior/leakage/association tests; synthetic truth is evaluator-only."""

import builtins
import importlib.util
import json
from pathlib import Path
import subprocess

import numpy as np
import pytest

from astrotrace.datasets.inventory import inspect_csv, inspect_yolo_labels
from astrotrace.datasets.stress import CASES, create_stress_scene
from astrotrace.detection.stress_evaluation import evaluate_stress
from astrotrace.preprocessing.registration import register_sequence, add_reference_coordinates
from astrotrace.preprocessing.suitability import validate_sequence_suitability
from orbittrace.detection import detect_sequence
from orbittrace.detection.example import _load_snapshot


@pytest.mark.parametrize('value', [None, 'pixels', np.zeros((0, 0), dtype=np.uint8),
    np.zeros((40, 40, 3), dtype=np.uint8), np.full((40, 40), np.nan),
    np.ones((40, 40), dtype=np.int32), np.full((40, 40), 2., dtype=np.float32)])
def test_invalid_input_is_explicitly_unsupported(value):
    result = validate_sequence_suitability([value]*5)
    assert result['status'] == 'unsupported'
    assert not result['inference_allowed']
    assert 'invalid_pixels' in result['reason_codes']
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('frames', [[], [np.zeros((40, 40), dtype=np.uint8)]*4,
                                  [np.zeros((40, 40), dtype=np.uint8)]*6])
def test_profile_requires_five_frames(frames):
    assert validate_sequence_suitability(frames)['reason_codes'] == ['sequence_length']


def test_dimensions_and_clipping_rejected():
    dark = np.zeros((40, 40), dtype=np.uint8)
    assert 'inconsistent_dimensions' in validate_sequence_suitability([dark]*4+[dark[:35]])['reason_codes']
    assert 'dimensions_too_small' in validate_sequence_suitability([dark[:20]]*5)['reason_codes']
    assert 'severe_clipping' in validate_sequence_suitability([np.full_like(dark, 255)]*5)['reason_codes']


@pytest.mark.parametrize('name,status,reason', [('counts_change', 'supported', None),
    ('empty_targets', 'supported', None), ('daylight_like', 'unsupported', 'broad_bright_field'),
    ('noise_only', 'uncertain', 'low_feature_evidence'), ('blurred', 'uncertain', 'possible_blur'),
    ('registration_failure', 'uncertain', 'low_feature_evidence')])
def test_controlled_suitability_labels(name, status, reason):
    result = validate_sequence_suitability(create_stress_scene(name).frames)
    assert result['status'] == status
    assert result['inference_allowed'] == (status == 'supported')
    if reason:
        assert reason in result['reason_codes']


def test_bright_star_is_not_broad_daylight_rule():
    frames = [a.copy() for a in create_stress_scene('empty_targets').frames]
    for a in frames:
        a[5:15, 5:15] = 255
    assert 'broad_bright_field' not in validate_sequence_suitability(frames)['reason_codes']


def test_noise_and_background_change_produce_review_reasons():
    rng = np.random.default_rng(14)
    noisy = tuple(np.clip(rng.normal(110, 65, (64, 64)), 0, 255).astype(np.uint8) for _ in range(5))
    assert 'excessive_noise' in validate_sequence_suitability(noisy)['reason_codes']
    frames = [a.copy() for a in create_stress_scene('empty_targets').frames]
    frames[-1] = np.clip(frames[-1].astype(np.int16)+80, 0, 255).astype(np.uint8)
    result = validate_sequence_suitability(frames)
    assert 'background_inconsistency' in result['reason_codes'] and not result['inference_allowed']


@pytest.mark.parametrize('name', CASES)
def test_fixtures_repeatable_and_visibility_bbox_bounds(name):
    a, b = create_stress_scene(name), create_stress_scene(name)
    assert a.truth == b.truth
    assert len(a.frames) == 5
    for first, second in zip(a.frames, b.frames):
        assert np.array_equal(first, second)
        assert first.shape == (240, 320) and first.dtype == np.uint8
    for frame in a.truth['frames']:
        for obj in frame['objects']:
            if obj['visible']:
                x0, y0, x1, y1 = obj['bbox_raw_xyxy_px']
                assert 0 <= x0 < x1 <= 320 and 0 <= y0 < y1 <= 240
            else:
                assert obj['bbox_raw_xyxy_px'] is None


def test_counts_truth_and_real_predictions_are_independent():
    scene = create_stress_scene('counts_change')
    assert [sum(o['visible'] for o in f['objects']) for f in scene.truth['frames']] == [5, 3, 4, 5, 5]
    predictions = detect_sequence(scene.frames, sequence_id='counts-test')
    assert [sum(d.frame_index == i for d in predictions) for i in range(5)] == [5, 3, 4, 5, 5]


def test_inference_cannot_open_labels_and_preserves_pixels(monkeypatch):
    scene = create_stress_scene('counts_change')
    originals = [a.copy() for a in scene.frames]
    def forbidden(*args, **kwargs):
        raise AssertionError('Inference attempted file I/O')
    monkeypatch.setattr(builtins, 'open', forbidden)
    monkeypatch.setattr(Path, 'open', forbidden)
    result = validate_sequence_suitability(scene.frames)
    predictions = detect_sequence(scene.frames, sequence_id='io-guard')
    registration = register_sequence(scene.frames)
    compensated = add_reference_coordinates(predictions, registration)
    assert result['status'] == 'supported'
    assert all(np.array_equal(a, b) for a, b in zip(scene.frames, originals))
    assert [(d.x_raw_px, d.y_raw_px, d.bbox_raw_px) for d in compensated] == [(d.x_raw_px, d.y_raw_px, d.bbox_raw_px) for d in predictions]
    assert [d.model_dump() for d in predictions] == [d.model_dump() for d in detect_sequence(scene.frames, sequence_id='io-guard')]


def test_noise_and_empty_scene_rejection():
    for name in ('noise_only', 'empty_targets'):
        scene = create_stress_scene(name)
        assert detect_sequence(scene.frames, sequence_id=name.replace('_', '-')) == []


def test_failed_registration_never_fabricates_reference_coordinates():
    scene = create_stress_scene('registration_failure')
    result = register_sequence(scene.frames)
    assert result.status == 'failed' and result.frames[2].raw_to_reference is None
    with pytest.raises(ValueError):
        add_reference_coordinates(detect_sequence(scene.frames, sequence_id='failed'), result)


@pytest.fixture(scope='module')
def tracker(tmp_path_factory):
    root = Path(__file__).resolve().parents[2]
    ref = 'a015cc949955d0438c8a16789b23746c3206f3d1'
    if subprocess.run(['git', 'cat-file', '-e', ref], cwd=root, capture_output=True).returncode:
        pytest.skip('Optional Member3 snapshot commit absent; fetch feature/tracking-trajectory to run integration')
    _, _, Tracker, _ = _load_snapshot(root, ref, tmp_path_factory.mktemp('cv_t14_tracker'))
    assert Tracker().gate_distance_px == 20.
    return Tracker


def test_actual_tracker_gap_recovery(tracker):
    scene = create_stress_scene('counts_change')
    detections = add_reference_coordinates(detect_sequence(scene.frames, sequence_id='gaps'), register_sequence(scene.frames))
    tracks = tracker().process_sequence(detections, frame_indices=range(5))
    metrics = evaluate_stress(detections, tracks, scene.truth)['association']
    assert metrics['identity_switches'] == metrics['fragmentation'] == 0
    assert metrics['scripted_gaps_recovered'] == 2 and metrics['scripted_gaps_failed'] == 0
    assert metrics['confirmed_tracks'] == 5


def test_actual_tracker_camera_compensation(tracker):
    scene = create_stress_scene('camera_motion')
    predictions = detect_sequence(scene.frames, sequence_id='camera')
    raw = evaluate_stress(predictions, tracker().process_sequence(predictions, frame_indices=range(5)), scene.truth)
    result = register_sequence(scene.frames)
    compensated = add_reference_coordinates(predictions, result)
    registered = evaluate_stress(compensated, tracker().process_sequence(compensated, frame_indices=range(5)), scene.truth)
    assert registered['association']['fragmentation'] < raw['association']['fragmentation']
    errors = [np.linalg.norm(np.asarray(f.raw_to_reference)[:2, 2]+scene.truth['frames'][i]['camera_shift_xy_px']) for i, f in enumerate(result.frames)]
    assert max(errors) < .3


def test_actual_tracker_does_not_certify_artifact_identity(tracker):
    scene = create_stress_scene('artifacts')
    predictions = detect_sequence(scene.frames, sequence_id='artifacts')
    tracks = tracker().process_sequence(predictions, frame_indices=range(5))
    assert evaluate_stress(predictions, tracks, scene.truth)['association']['false_confirmed_tracks'] >= 1


def test_predicted_points_never_count_as_truth_observations(tracker):
    scene = create_stress_scene('counts_change')
    detections = detect_sequence(scene.frames, sequence_id='points')
    tracks = tracker().process_sequence(detections, frame_indices=range(5))
    scored = evaluate_stress(detections, tracks, scene.truth)
    assert scored['predicted_points_scored'] is False
    with pytest.raises(ValueError, match='exactly'):
        evaluate_stress(detections, [], scene.truth)


def test_label_audit_handles_empty_malformed_and_outside_boxes(tmp_path):
    empty, bad, outside = [tmp_path/f'{name}.txt' for name in ('empty', 'bad', 'outside')]
    empty.write_text('')
    bad.write_text('1 .5 .5 .1 .1\n0 nan 0 .1 .1\n0 .5 .5\n')
    outside.write_text('0 .99 .5 .2 .2\n')
    result = inspect_yolo_labels([empty, bad, outside], ['empty', 'bad', 'outside', 'missing'])
    assert result['empty_files'] == 1 and len(result['errors']) == 3
    assert result['boxes_extend_outside_image'] == 1 and result['missing_labels'] == ['missing']


def test_csv_audit_does_not_execute_literals_or_assume_coordinates(tmp_path):
    path = tmp_path/'labels.csv'
    path.write_text('ImageID,bboxes\n0,[]\n1,__import__("os").system("bad")\n')
    result = inspect_csv(path, ['0', '1', '2'])
    assert result['empty_rows'] == 1 and len(result['errors']) == 1
    assert result['missing_annotation_ids'] == ['2']
    assert result['coordinate_semantics'].startswith('unverified')


def _script():
    path = Path(__file__).resolve().parents[2]/'scripts/spotgeo_robustness.py'
    spec = importlib.util.spec_from_file_location('_cv_t14_test_script', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unsupported_demo_does_not_return_empty_success(tmp_path, monkeypatch):
    module = _script()
    def forbidden(*args, **kwargs):
        raise AssertionError('Unsupported input reached detection')
    monkeypatch.setattr(module, 'detect_sequence', forbidden)
    scene = create_stress_scene('daylight_like')
    report = module.process(scene.frames, 'blocked', tmp_path/'blocked', None)
    assert not report['inference_executed'] and report['detections_per_frame'] is None
    output = json.loads((tmp_path/'blocked/detections.json').read_text())
    assert output['detections'] is None and output['input_status'] == 'unsupported'
    assert not list((tmp_path/'blocked').glob('tracking_*.json'))


def test_reproduction_refuses_to_overwrite_results(tmp_path):
    sentinel = tmp_path/'keep.txt'
    sentinel.write_text('existing results')
    with pytest.raises(FileExistsError):
        _script().main(['--output', str(tmp_path), '--tracking-ref', 'unused'])
    assert sentinel.read_text() == 'existing results'


def test_generated_report_links_resolve_to_actual_outputs(tmp_path, monkeypatch, tracker):
    """Exercise the real renderer/runner for accepted and rejected image cases."""
    import re
    module = _script()
    monkeypatch.setattr(module, 'CASES', ('counts_change', 'daylight_like'))
    output = tmp_path / 'report'
    assert module.main(['--output', str(output), '--synthetic-only',
                        '--tracking-ref', 'a015cc949955d0438c8a16789b23746c3206f3d1']) == 0
    targets = re.findall(r'(?:href|src)="([^"]+)"', (output / 'index.html').read_text())
    assert targets
    for target in targets:
        path = (output / target).resolve()
        assert path.is_relative_to(output.resolve())
        assert path.is_file(), f'Generated report links to absent output: {target}'
