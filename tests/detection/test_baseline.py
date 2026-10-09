"""T03 image-only behavior, schema, point evaluation and integration evidence."""

from dataclasses import replace
import builtins
import json
from pathlib import Path
import shutil
import subprocess
import sys

import cv2
import numpy as np
import pytest

from app.schemas.result import Detection
from astrotrace.datasets import SpotGeoDataset
from astrotrace.datasets.fixtures import create_fixture
from astrotrace.datasets.validation import discover_annotations, discover_root, validate_dataset
from astrotrace.detection.baseline import BaselineConfig, CandidateLimitWarning, OpenCVBaselineDetector, MinimalThresholdDetector
from astrotrace.detection.evaluation import evaluate_sequences, freeze_membership, match_points, summarize_frames
from astrotrace.detection.interface import FrameContext
from astrotrace.detection.runner import detect_sequence
from astrotrace.detection.visualization import save_detection_panels
from astrotrace.preprocessing.candidates import normalize_grayscale


def context(pixels, index=0):
    return FrameContext(index, pixels.shape[1], pixels.shape[0], "spotgeo")


def image(points=(), *, seed=26, noise=0, streak=False):
    yy, xx = np.mgrid[:96, :128]
    pixels = np.full(xx.shape, 40, dtype=np.float64)
    rng = np.random.default_rng(seed)
    pixels += rng.normal(0, noise, pixels.shape)
    for x, y, amplitude in points:
        pixels += amplitude * np.exp(-((xx - x)**2 + (yy - y)**2) / (2 * 1.1**2))
    if streak:
        # Long thin star streak; target elsewhere must survive shape rejection.
        pixels += 120 * np.exp(-((yy - 25)**2) / 0.8) * ((xx >= 10) & (xx <= 95))
    return np.rint(np.clip(pixels, 0, 255)).astype(np.uint8)


def detect(pixels, **overrides):
    return OpenCVBaselineDetector().detect(pixels, context(pixels), overrides)


@pytest.mark.parametrize("level", [0, 40, 255])
def test_constant_empty_frames(level):
    pixels = np.full((96, 128), level, dtype=np.uint8)
    assert detect(pixels) == []


def test_noise_only_high_threshold_has_no_proposals():
    assert detect(image(noise=5), threshold_sigma=6.0) == []


def test_bright_fractional_centroid_and_schema():
    pixels = image([(76.25, 41.75, 180)])
    detections = detect(pixels)
    assert len(detections) == 1
    candidate = detections[0]
    assert abs(candidate.x_raw_px - 76.25) < 0.35 and abs(candidate.y_raw_px - 41.75) < 0.35
    assert candidate.x_reference_px is None and candidate.y_reference_px is None
    assert 0 < candidate.quality_score < 1
    assert Detection.model_validate_json(candidate.model_dump_json()) == candidate
    left, top, right, bottom = candidate.bbox_raw_px
    assert 0 <= left <= candidate.x_raw_px < right <= 128
    assert 0 <= top <= candidate.y_raw_px < bottom <= 96


def test_faint_moving_target_is_detected_independently_each_frame():
    for frame in range(5):
        x, y = 40.25 + frame * 3, 60.75 - frame * 1.5
        pixels = image([(x, y, 18)], noise=2, seed=40 + frame)
        predictions = detect(pixels, threshold_sigma=3.5)
        assert any(np.hypot(d.x_raw_px - x, d.y_raw_px - y) < 1.0 for d in predictions)


def test_star_streak_rejection_keeps_compact_source():
    predictions = detect(image([(105.2, 68.7, 90)], noise=1, streak=True), max_elongation=2.5)
    assert any(np.hypot(d.x_raw_px - 105.2, d.y_raw_px - 68.7) < 0.6 for d in predictions)
    assert all(abs(d.y_raw_px - 25) > 10 for d in predictions)


def test_multiple_candidates_and_border_coordinate():
    predictions = detect(image([(0.25, 65.5, 100), (42.3, 35.7, 130), (101.2, 79.4, 120)]))
    assert len(predictions) == 3
    assert len({d.detection_id for d in predictions}) == 3
    assert min(d.x_raw_px for d in predictions) < 1.0


def test_uint8_uint16_and_normalized_float_have_same_geometry():
    pixels = image([(76.25, 41.75, 160)], noise=1)
    a = detect(pixels)[0]
    b = detect(pixels.astype(np.uint16) * 257)[0]
    c = detect(pixels.astype(np.float32) / 255)[0]
    np.testing.assert_allclose(normalize_grayscale(pixels)[0],
                               normalize_grayscale(pixels.astype(np.uint16) * 257)[0], atol=1e-7)
    for other in (b, c):
        # Dtype quantization floors can alter component boundary pixels. Normalized
        # intensities agree; subpixel geometry must still agree within 0.1 px.
        assert abs(other.x_raw_px - a.x_raw_px) < 0.1
        assert abs(other.y_raw_px - a.y_raw_px) < 0.1


@pytest.mark.parametrize("pixels", [None, np.empty((0, 2), dtype=np.uint8), np.zeros((8, 8, 3), dtype=np.uint8),
                                    np.ones((8, 8), dtype=np.int16), np.full((8, 8), np.nan),
                                    np.full((8, 8), np.inf), np.full((8, 8), 255.0),
                                    np.ones((8, 8), dtype=bool), np.zeros((2001, 2000), dtype=np.uint8)])
def test_invalid_images(pixels):
    with pytest.raises(ValueError):
        OpenCVBaselineDetector().detect(pixels, FrameContext(0, 8, 8, "spotgeo"), {})


@pytest.mark.parametrize("changes", [{"frame_index": -1}, {"frame_index": True}, {"width_px": 9},
                                     {"profile": "bad"}, {"timestamp_s": float("nan")}])
def test_bad_frame_context(changes):
    pixels = np.zeros((8, 8), dtype=np.uint8)
    with pytest.raises(ValueError):
        OpenCVBaselineDetector().detect(pixels, replace(context(pixels), **changes), {})


@pytest.mark.parametrize("config", [{"truth": "labels.json"}, {"threshold_sigma": float("nan")},
                                    {"threshold_sigma": True}, {"min_area_px": 0},
                                    {"min_area_px": 100, "max_area_px": 5}, {"max_candidates": 9999},
                                    {"denoise_sigma": 0}, {"denoise_sigma": 2, "background_sigma": 2}])
def test_unknown_or_unbounded_config(config):
    with pytest.raises(ValueError):
        detect(image(), **config)


def test_repeatable_inference_no_input_mutation_or_disk_access(monkeypatch):
    pixels = image([(60.2, 60.8, 50)], noise=2)
    before = pixels.copy()
    pixels.setflags(write=False)

    def fail(*args, **kwargs):
        pytest.fail("Inference attempted to read a filesystem/label path")

    monkeypatch.setattr(Path, "open", fail)
    monkeypatch.setattr(builtins, "open", fail)
    first, second = detect(pixels), detect(pixels)
    assert [d.model_dump() for d in first] == [d.model_dump() for d in second]
    np.testing.assert_array_equal(before, pixels)


def test_cap_warns_and_retains_strongest():
    pixels = image([(30, 30, 180), (85, 68, 70)])
    with pytest.warns(CandidateLimitWarning):
        result = detect(pixels, max_candidates=1)
    assert len(result) == 1 and abs(result[0].x_raw_px - 30) < 0.1


def test_five_frame_runner_and_no_label_reads(tmp_path, monkeypatch):
    root = create_fixture(tmp_path / "sample")
    dataset = SpotGeoDataset(root, expected_size=(64, 48))
    sequence = dataset.load_sequence(1)

    def fail(*args, **kwargs):
        pytest.fail("Sequence inference attempted to load annotations")

    monkeypatch.setattr(dataset, "read_file", fail)
    output = detect_sequence(sequence, OpenCVBaselineDetector(), {})
    assert [frame.frame_index for frame in output.frames] == list(range(5))
    ids = [d.detection_id for frame in output.frames for d in frame.detections]
    assert len(ids) == 5 and len(set(ids)) == 5
    payload = output.to_dict()
    assert payload["sequence_id"] == "1" and payload["tracking_performed"] is False
    assert payload["coordinate_system"] == "raw_top_left_xy_px_integer_centers"
    assert all(frame.processing_ms > 0 for frame in output.frames)
    save_detection_panels(sequence, output, tmp_path / "candidates.png")


def test_minimal_comparator_is_valid():
    pixels = image([(70.1, 40.2, 180)])
    predictions = MinimalThresholdDetector().detect(pixels, context(pixels), {})
    assert any(abs(d.x_raw_px - 70.1) < 0.5 for d in predictions)
    assert all(isinstance(d, Detection) for d in predictions)


def test_matching_empty_duplicate_and_gate_boundary():
    assert match_points([], [], 5) == {"tp": 0, "fp": 0, "fn": 0, "matches": []}
    assert match_points([[1, 1]], [], 5)["fp"] == 1
    assert match_points([], [[1, 1]], 5)["fn"] == 1
    result = match_points([[3, 4], [0, 0]], [[0, 0]], 5)
    assert (result["tp"], result["fp"], result["fn"]) == (1, 1, 0)
    assert result["matches"][0]["distance_px"] == 0
    assert match_points([[3, 4]], [[0, 0]], 5)["tp"] == 1
    assert match_points([[3, 4.01]], [[0, 0]], 5)["tp"] == 0


def test_matching_uses_unmatched_slots_and_maximizes_cardinality():
    # Greedy nearest first loses a match: first pred can use either target,
    # second can only use the first. Also include a forbidden far-out proposal.
    result = match_points([[0.1, 0], [-0.8, 0], [100, 100]], [[0, 0], [0.9, 0]], 1)
    assert (result["tp"], result["fp"], result["fn"]) == (2, 1, 0)
    assert {m["truth_index"] for m in result["matches"]} == {0, 1}


def test_matching_rejects_nonfinite_and_bad_radius():
    for radius in (0, -1, float("nan")):
        with pytest.raises(ValueError):
            match_points([], [], radius)
    with pytest.raises(ValueError):
        match_points([[float("nan"), 0]], [], 5)


def test_metric_denominators_and_localization():
    result = summarize_frames([match_points([[3, 4], [100, 100]], [[0, 0], [50, 50]], 5)], [12.0])
    assert result["precision"] == result["recall"] == result["f1"] == 0.5
    assert result["localization_mean_px"] == result["localization_rmse_px"] == 5
    assert result["false_positives_per_frame"] == 1
    empty = summarize_frames([match_points([], [], 5)], [1])
    assert empty["precision"] is empty["recall"] is empty["f1"] is None
    assert empty["localization_rmse_px"] is None


def test_membership_is_repeatable_sequence_scoped_and_bounded():
    ids = tuple(str(i) for i in range(1, 21))
    a = freeze_membership(ids, ids, development_count=5, heldout_count=6)
    b = freeze_membership(ids, ids, development_count=5, heldout_count=6)
    assert a == b
    assert a["development"]["split"] == "train" and a["held_out"]["split"] == "test"
    assert len(a["development"]["sequence_ids"]) == 5
    with pytest.raises(ValueError):
        freeze_membership(ids, ids, development_count=21, heldout_count=6)


def test_discovery_uses_annotation_contents_and_rejects_ambiguity(tmp_path):
    root = create_fixture(tmp_path / "data" / "DifferentName")
    (root / "test").mkdir()
    (root / "train_anno.json").rename(root / "unexpected_name.json")
    assert discover_root(tmp_path / "data") == root.resolve()
    dataset = SpotGeoDataset(root, expected_size=(64, 48))
    assert discover_annotations(dataset)[0] == "unexpected_name.json"
    shutil.copy(root / "unexpected_name.json", root / "duplicate.json")
    with pytest.raises(ValueError, match="found 2"):
        discover_annotations(dataset)


def test_validation_missing_records_evidence(tmp_path):
    assert discover_root(tmp_path / "absent") is None
    report = validate_dataset(None, tmp_path / "results")
    assert report["status"] == "missing"
    assert json.loads((tmp_path / "results/validation.json").read_text())["missing_reason"]


def test_detect_cli_does_not_depend_on_annotations(tmp_path):
    root = create_fixture(tmp_path / "sample")
    (root / "train_anno.json").write_text("broken annotations", encoding="utf-8")
    script = Path(__file__).resolve().parents[2] / "scripts/spotgeo_baseline.py"
    completed = subprocess.run([sys.executable, str(script), "detect", "--source", str(root),
                               "--fixture-size", "--sequence", "1", "--output", str(tmp_path / "out")],
                              capture_output=True, text=True, timeout=60)
    assert completed.returncode == 0, completed.stderr
    output = json.loads((tmp_path / "out/detections.json").read_text())
    assert len(output["frames"]) == 5
    assert "\"annotations_read\": false" in completed.stdout


def test_detect_cli_rejects_nonobject_config_without_traceback(tmp_path):
    root = create_fixture(tmp_path / "sample")
    config = tmp_path / "invalid_config.json"
    config.write_text("12", encoding="utf-8")
    script = Path(__file__).resolve().parents[2] / "scripts/spotgeo_baseline.py"
    result = subprocess.run([sys.executable, str(script), "detect", "--source", str(root),
                             "--fixture-size", "--sequence", "1", "--config", str(config),
                             "--output", str(tmp_path / "out")], capture_output=True, text=True, timeout=60)
    assert result.returncode == 2 and "JSON object" in result.stderr
    assert "Traceback" not in result.stderr and not (tmp_path / "out").exists()


def test_duplicate_sequences_cannot_inflate_evaluation_counts(tmp_path):
    root = create_fixture(tmp_path / "sample")
    dataset = SpotGeoDataset(root, expected_size=(64, 48))
    _, labels, _ = discover_annotations(dataset)
    predictions = detect_sequence(dataset.load_sequence(1), OpenCVBaselineDetector(), {})
    with pytest.raises(ValueError, match="unique complete"):
        evaluate_sequences([predictions, predictions], labels, 5)
