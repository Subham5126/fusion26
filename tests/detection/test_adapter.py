"""CV-T06 boundary regressions using actual detector image inputs."""

import builtins
import json
from pathlib import Path

import numpy as np
import pytest

from app.schemas.result import Detection
from astrotrace.detection.baseline import CandidateLimitWarning, OpenCVBaselineDetector
from astrotrace.detection.optimized import OptimizedConfig, OptimizedDetector
from orbittrace.detection import FrameContext, detect_frame, detect_sequence


def image(points=((24.25, 31.75),), shape=(64, 80)):
    yy, xx = np.mgrid[:shape[0], :shape[1]]
    pixels = np.full(shape, 30.0)
    for x, y in points:
        pixels += 100 * np.exp(-.5 * ((xx-x)**2 + (yy-y)**2))
    return np.rint(np.clip(pixels, 0, 255)).astype(np.uint8)


def ctx(pixels, index=0):
    return FrameContext(index, pixels.shape[1], pixels.shape[0], "spotgeo")


@pytest.mark.parametrize("method", ["baseline", "optimized"])
def test_preserved_algorithm_geometry_and_schema(method):
    pixels = image(((24.25, 31.75), (79., 63.)))
    if method == "optimized":
        original = OptimizedDetector().detect(pixels, ctx(pixels), OptimizedConfig(
            threshold_sigma=4.5, max_context_elongation=2.).to_dict())
    else:
        original = OpenCVBaselineDetector().detect(pixels, ctx(pixels), {})
    adapted = detect_frame(pixels, ctx(pixels), method=method, sequence_id="geometry")
    assert len(adapted) == len(original) == 2
    for before, after in zip(original, adapted):
        assert type(after) is Detection
        assert {k: v for k, v in before.model_dump().items() if k != "detection_id"} == {
            k: v for k, v in after.model_dump().items() if k != "detection_id"}
        json.dumps(after.model_dump(), allow_nan=False)
        assert 0 <= after.quality_score <= 1
        assert after.x_reference_px is None and after.y_reference_px is None
    edge = next(d for d in adapted if d.x_raw_px > 70)
    assert edge.bbox_raw_px[2:] == (80., 64.)
    assert edge.x_raw_px < 80 and edge.y_raw_px < 64


def test_unique_ids_and_correct_frame_indices_with_empty_gap():
    frames = [image(), image(), np.zeros((64, 80), np.uint8), image(), image()]
    first = detect_sequence(frames, sequence_id="first")
    assert [d.frame_index for d in first] == [0, 1, 3, 4]
    assert len({d.detection_id for d in first}) == len(first)
    assert first == detect_sequence(frames, sequence_id="first")
    assert {d.detection_id for d in first}.isdisjoint(
        d.detection_id for d in detect_sequence(frames, sequence_id="second"))
    assert {d.detection_id for d in first}.isdisjoint(
        d.detection_id for d in detect_sequence(frames, sequence_id="first", method="baseline"))


@pytest.mark.parametrize("method", ["baseline", "optimized"])
@pytest.mark.parametrize("level", [0, 30, 255])
def test_constant_frames_and_empty_sequence(method, level):
    frames = [np.full((64, 80), level, np.uint8)] * 5
    assert detect_sequence(frames, sequence_id="empty", method=method) == []
    assert detect_sequence([], sequence_id="empty", method=method) == []


@pytest.mark.parametrize("method", ["baseline", "optimized"])
def test_cap_keeps_best_candidates_and_warns(method):
    pixels = image(((12, 12), (40, 32), (68, 52)))
    all_detections = detect_frame(pixels, ctx(pixels), method=method)
    assert len(all_detections) == 3
    with pytest.warns(CandidateLimitWarning):
        capped = detect_frame(pixels, ctx(pixels), {"max_candidates": 1}, method=method)
    assert capped == all_detections[:1]


def test_memory_only_no_truth_or_file_access(monkeypatch):
    pixels = image()
    before = pixels.copy()

    def forbidden(*args, **kwargs):
        raise AssertionError("Image-only detector attempted filesystem access")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    output = detect_sequence([pixels]*5, sequence_id="no-truth")
    assert len(output) == 5 and np.array_equal(pixels, before)
    with pytest.raises(ValueError):
        detect_sequence([pixels]*5, sequence_id="no-truth", config={"truth_path": "forbidden"})


@pytest.mark.parametrize("pixels", [np.empty((0, 2), np.uint8), np.zeros((2, 2, 3), np.uint8),
                                    np.zeros((2, 2), np.int16), np.full((2, 2), np.nan),
                                    np.full((2, 2), np.inf), np.full((2, 2), 1.1),
                                    np.zeros((2001, 2000), np.uint8)])
def test_invalid_and_excessive_images_fail(pixels):
    with pytest.raises(ValueError):
        detect_sequence([pixels], sequence_id="invalid")


@pytest.mark.parametrize("kwargs", [
    {"sequence_id": "../path"}, {"method": "unknown"}, {"profile": "unknown"},
    {"config": {"quality_score": .5}}, {"config": {"max_candidates": 0}},
    {"config": {"max_candidates": 2001}}, {"config": {"threshold_sigma": float("inf")}},
    {"config": []}, {"timestamps_s": [None, 1.]}, {"timestamps_s": [1., 1.]},
    {"timestamps_s": [1., 0.]}, {"timestamps_s": [float("nan"), 2.]},
    {"timestamps_s": [1.]}, {"timestamps_s": "12"},
])
def test_invalid_metadata_and_config_fail(kwargs):
    params = {"sequence_id": "invalid", **kwargs}
    with pytest.raises(ValueError):
        detect_sequence([image()]*2, **params)


def test_invalid_sequence_shape_count_and_frame_context():
    with pytest.raises(ValueError):
        detect_sequence([image(), image(shape=(65, 80))], sequence_id="dimensions")
    with pytest.raises(ValueError):
        detect_sequence([image()]*31, sequence_id="count")
    with pytest.raises(ValueError):
        detect_sequence(image(), sequence_id="ambiguous-array")
    with pytest.raises(ValueError):
        detect_frame(image(), FrameContext(0, 81, 64, "spotgeo"))
    with pytest.raises(ValueError):
        detect_frame(image(), FrameContext(-1, 80, 64, "spotgeo"))


def test_valid_times_and_arbitrary_direct_frame_index():
    pixels = image()
    output = detect_sequence([pixels]*3, sequence_id="timed", timestamps_s=[0., .5, 1.5])
    assert [d.frame_index for d in output] == [0, 1, 2]
    single = detect_frame(pixels, ctx(pixels, index=17), sequence_id="timed")
    assert single[0].frame_index == 17


@pytest.mark.parametrize("override", [
    {"frame_index": 1}, {"detector_name": "wrong"},
    {"x_raw_px": 81., "y_raw_px": 1., "bbox_raw_px": (79., 0., 82., 2.)},
])
def test_bridge_rejects_wrong_frame_name_or_geometry(monkeypatch, override):
    pixels = image()
    valid = OptimizedDetector().detect(pixels, ctx(pixels), {})[0]
    corrupted = Detection.model_validate({**valid.model_dump(), **override})
    monkeypatch.setattr(OptimizedDetector, "detect", lambda *args, **kwargs: [corrupted])
    with pytest.raises(ValueError):
        detect_frame(pixels, ctx(pixels))
