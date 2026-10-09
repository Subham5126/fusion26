"""CV-T04 substantive filtering, leakage, coordinate and contract checks."""

import builtins
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from app.schemas.result import Detection
from astrotrace.datasets.spotgeo import Frame, Sequence
from astrotrace.detection.baseline import CandidateLimitWarning, OpenCVBaselineDetector
from astrotrace.detection.interface import FrameContext
from astrotrace.detection.optimized import OptimizedConfig, OptimizedDetector, detect_optimized_sequence


def image(points=(), *, noise=0., seed=26):
    yy, xx = np.mgrid[:96, :128]
    pixels = 40 + np.random.default_rng(seed).normal(0, noise, xx.shape)
    for x, y, amplitude, sx, sy in points:
        pixels += amplitude * np.exp(-.5 * (((xx-x)/sx)**2 + ((yy-y)/sy)**2))
    return np.rint(np.clip(pixels, 0, 255)).astype(np.uint8)


def detect(pixels, **config):
    ctx = FrameContext(0, pixels.shape[1], pixels.shape[0], "spotgeo")
    return OptimizedDetector().detect(pixels, ctx, config)


@pytest.mark.parametrize("level", [0, 40, 255])
@pytest.mark.parametrize("step", [1, 4])
def test_empty_frames(level, step):
    assert detect(np.full((96, 128), level, dtype=np.uint8), background_step=step) == []


def test_noise_only_rejected():
    assert detect(image(noise=5), background_step=4, threshold_sigma=6.) == []


def test_single_pixel_spike_rejected_without_losing_spread_source():
    pixels = image([(80.2, 61.4, 110, 1.1, 1.1)], noise=1)
    pixels[25, 30] = 255
    broad = detect(pixels, max_peak_fraction=1., max_context_elongation=20.)
    filtered = detect(pixels)
    assert any(np.hypot(d.x_raw_px-30, d.y_raw_px-25) < 1 for d in broad)
    assert all(np.hypot(d.x_raw_px-30, d.y_raw_px-25) > 3 for d in filtered)
    assert any(np.hypot(d.x_raw_px-80.2, d.y_raw_px-61.4) < .5 for d in filtered)


def test_context_shape_rejects_streak_with_broad_proposal_gate():
    pixels = image([(32, 30, 100, 3.5, .9), (90, 70, 80, 1.1, 1.1)], noise=1)
    broad = detect(pixels, max_elongation=20, max_context_elongation=20.)
    filtered = detect(pixels, max_elongation=20, max_context_elongation=2.)
    assert len(broad) >= 2
    assert len(filtered) == 1 and np.hypot(filtered[0].x_raw_px-90, filtered[0].y_raw_px-70) < .5


def test_component_aspect_and_area_filters_independently():
    pixels = image([(35, 30, 90, 1.8, 1.), (90, 70, 80, 1.1, 1.1)], noise=1)
    broad = detect(pixels, max_context_elongation=20., max_elongation=20.)
    assert len(broad) == 2
    narrow = detect(pixels, max_context_elongation=20., max_elongation=20., max_component_aspect=1.)
    assert len(narrow) == 1 and abs(narrow[0].x_raw_px-90) < .5
    assert detect(pixels, min_area_px=100, max_context_elongation=20.) == []


def test_threshold_controls_faint_proposals():
    pixels = image([(45.25, 60.75, 15, 1.1, 1.1)], noise=3)
    low = detect(pixels, threshold_sigma=3., max_context_elongation=3.)
    high = detect(pixels, threshold_sigma=15.)
    assert any(np.hypot(d.x_raw_px-45.25, d.y_raw_px-60.75) < 1 for d in low)
    assert high == []


def test_faint_moving_target_each_frame_independently():
    for index in range(5):
        x, y = 40.25 + 3*index, 60.75 - 1.5*index
        results = detect(image([(x, y, 18, 1.1, 1.1)], noise=2, seed=40+index),
                         threshold_sigma=3.5, max_context_elongation=3., background_step=4)
        assert any(np.hypot(d.x_raw_px-x, d.y_raw_px-y) < 1 for d in results)


def test_score_and_aperture_gates():
    pixels = image([(70, 50, 80, 1.1, 1.1)], noise=2)
    result = detect(pixels)
    assert len(result) == 1
    assert detect(pixels, min_score=1.) == []
    assert detect(pixels, min_aperture_snr=100.) == []
    assert detect(pixels, min_score=result[0].quality_score) == result


@pytest.mark.parametrize("step", [1, 2, 4])
def test_subpixel_multiple_border_coordinates_and_shared_schema(step):
    points = [(0.25, 65.5, 100, 1.1, 1.1), (42.3, 35.7, 130, 1.1, 1.1), (101.2, 79.4, 120, 1.1, 1.1)]
    result = detect(image(points), background_step=step)
    assert len(result) == 3
    for d in result:
        assert Detection.model_validate_json(d.model_dump_json()) == d
        assert d.x_reference_px is None and d.y_reference_px is None
        l, t, r, b = d.bbox_raw_px
        assert 0 <= l <= d.x_raw_px < r <= 128 and 0 <= t <= d.y_raw_px < b <= 96
        assert all(np.isfinite(v) for v in d.evidence_statistics.values())
    for x, y, *_ in points:
        assert min(np.hypot(d.x_raw_px-x, d.y_raw_px-y) for d in result) < .6


def test_dtype_coordinate_conversion():
    pixels = image([(76.25, 41.75, 160, 1.1, 1.1)], noise=1)
    a = detect(pixels, background_step=4)[0]
    for converted in (pixels.astype(np.uint16)*257, pixels.astype(np.float32)/255):
        b = detect(converted, background_step=4)[0]
        assert np.hypot(a.x_raw_px-b.x_raw_px, a.y_raw_px-b.y_raw_px) < .1


def test_disabling_new_gates_keeps_t03_geometry_and_score():
    pixels = image([(76.25, 41.75, 160, 1.1, 1.1)], noise=1)
    config = OptimizedConfig(max_peak_fraction=1., max_context_elongation=20.).to_dict()
    a = detect(pixels, **config)
    b = OpenCVBaselineDetector().detect(pixels, FrameContext(0, 128, 96, "spotgeo"),
                                       OptimizedConfig.from_mapping(config).baseline_mapping())
    assert len(a) == len(b) == 1
    assert (a[0].x_raw_px, a[0].y_raw_px, a[0].quality_score) == (b[0].x_raw_px, b[0].y_raw_px, b[0].quality_score)


def test_repeatable_inference_has_no_io_and_does_not_mutate(monkeypatch):
    pixels = image([(60.2, 60.8, 50, 1.1, 1.1)], noise=2)
    before = pixels.copy()
    pixels.setflags(write=False)

    def fail(*args, **kwargs):
        pytest.fail("Inference accessed filesystem/annotations")

    monkeypatch.setattr(Path, "open", fail)
    monkeypatch.setattr(builtins, "open", fail)
    first = detect(pixels, background_step=4)
    assert [d.model_dump() for d in first] == [d.model_dump() for d in detect(pixels, background_step=4)]
    assert np.array_equal(before, pixels)


def test_sequence_wrapper_contract_and_no_truth(monkeypatch):
    frames = tuple(Frame(i, i+1, image([(40+i, 55, 90, 1.1, 1.1)])) for i in range(5))
    sequence = Sequence("17", "train", frames)

    def fail(*args, **kwargs):
        pytest.fail("Sequence inference accessed annotations")

    monkeypatch.setattr(Path, "open", fail)
    output = detect_optimized_sequence(sequence, {"background_step": 4})
    payload = output.to_dict()
    assert payload["schema_version"] == "0.1.0" and payload["sequence_id"] == "17"
    assert payload["coordinate_system"] == "raw_top_left_xy_px_integer_centers"
    assert payload["score_type"] == "uncalibrated_heuristic" and not payload["tracking_performed"]
    assert [frame.frame_index for frame in output.frames] == list(range(5))
    assert all(len(frame.detections) == 1 for frame in output.frames)
    assert len({d.detection_id for frame in output.frames for d in frame.detections}) == 5
    with pytest.raises(ValueError, match="five frames"):
        detect_optimized_sequence(replace(sequence, frames=frames[:4]), {})


def test_final_cap_after_rejection():
    pixels = image([(80, 60, 100, 1.1, 1.1), (105, 75, 60, 1.1, 1.1)], noise=1)
    pixels[25, 30] = 255
    with pytest.warns(CandidateLimitWarning):
        result = detect(pixels, max_candidates=1)
    assert len(result) == 1 and np.hypot(result[0].x_raw_px-80, result[0].y_raw_px-60) < .5


@pytest.mark.parametrize("config", [{"truth": "labels.json"}, {"background_step": 3}, {"background_step": True},
                                    {"min_score": float("nan")}, {"max_peak_fraction": 0},
                                    {"max_context_elongation": .9}, {"min_aperture_snr": -1},
                                    {"max_component_aspect": float("inf")}])
def test_invalid_config(config):
    with pytest.raises(ValueError):
        detect(image(), **config)


@pytest.mark.parametrize("pixels", [None, np.empty((0, 2), dtype=np.uint8), np.zeros((8, 8, 3), dtype=np.uint8),
                                    np.ones((8, 8), dtype=np.int16), np.full((8, 8), np.nan)])
def test_invalid_images(pixels):
    with pytest.raises(ValueError):
        OptimizedDetector().detect(pixels, FrameContext(0, 8, 8, "spotgeo"), {})
