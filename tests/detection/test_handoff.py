"""Member 3 artifact validation and truth-free readiness checks, without ESA files."""

from copy import deepcopy
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import spotgeo_handoff as handoff

from app.schemas.result import Detection
from astrotrace.datasets.spotgeo import Frame, Sequence
from astrotrace.detection.optimized import OptimizedConfig


def sample_sequence(empty=False):
    yy, xx = np.mgrid[:48, :64]
    frames = []
    for index in range(5):
        image = np.full(xx.shape, 40., dtype=np.float64)
        if not empty:
            image += 90*np.exp(-((xx-(20.25+index))**2 + (yy-30.75)**2)/(2*1.1**2))
            image += 70*np.exp(-((xx-49.25)**2 + (yy-15.75)**2)/(2*1.1**2))
        pixels = np.rint(np.clip(image, 0, 255)).astype(np.uint8)
        pixels.setflags(write=False)
        frames.append(Frame(index, index+1, pixels))
    return Sequence("1", "train", tuple(frames))


@pytest.mark.parametrize("empty", [False, True])
def test_guarded_real_interfaces_roundtrip_empty_and_multiple(empty):
    sequence = sample_sequence(empty)
    result = handoff.verified_inference(sequence, OptimizedConfig(
        threshold_sigma=4.5, max_context_elongation=2.).to_dict(), repeat=True)
    parsed = handoff.validate_payload(result.to_dict(), 64, 48)
    assert len(parsed) == 5
    assert all(len(frame) == (0 if empty else 2) for frame in parsed)
    assert all(isinstance(d, Detection) for frame in parsed for d in frame)


def test_file_guard_rejects_inference_io(monkeypatch):
    def leaking(*args, **kwargs):
        Path("train_anno.json").read_text()
    monkeypatch.setattr(handoff, "detect_optimized_sequence", leaking)
    with pytest.raises(RuntimeError, match="annotation access"):
        handoff.verified_inference(sample_sequence(), {})


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(coordinate_system="reference_frame_0"),
    lambda p: p.update(score_type="calibrated_probability"),
    lambda p: p.update(tracking_performed=True),
    lambda p: p.update(frames=p["frames"][:4]),
    lambda p: p["frames"][0].update(frame_index=True),
    lambda p: p["frames"][0].update(detections=None),
    lambda p: p["frames"][0]["detections"][0].update(frame_index=1),
    lambda p: p["frames"][0]["detections"][0].update(x_raw_px=float("nan")),
    lambda p: p["frames"][0]["detections"][0].update(bbox_raw_px=[-1., 0., 64., 48.]),
    lambda p: p["frames"][0]["detections"][0].update(x_reference_px=1., y_reference_px=2.),
])
def test_wrong_artifact_metadata_schema_or_coordinates_fail(mutation):
    result = handoff.verified_inference(sample_sequence(), OptimizedConfig().to_dict())
    payload = deepcopy(result.to_dict())
    mutation(payload)
    with pytest.raises(ValueError):
        handoff.validate_payload(payload, 64, 48)


def test_duplicate_proposal_ids_rejected():
    result = handoff.verified_inference(sample_sequence(), OptimizedConfig().to_dict())
    payload = result.to_dict()
    payload["frames"][1]["detections"][0]["detection_id"] = payload["frames"][0]["detections"][0]["detection_id"]
    with pytest.raises(ValueError, match="Duplicate"):
        handoff.validate_payload(payload, 64, 48)


def test_final_membership_is_disjoint_deterministic_not_annotation_selected():
    ids = tuple(str(i) for i in range(1, 31))
    excluded = {("test", "1"), ("test", "2"), ("test", "30"), ("train", "3")}
    first = handoff.select_final_ids(ids, excluded, 20, 20261009)
    assert first == handoff.select_final_ids(ids, excluded, 20, 20261009)
    assert len(first) == len(set(first)) == 20
    assert not {("test", key) for key in first} & excluded
    assert first == sorted(first, key=int)
    with pytest.raises(ValueError):
        handoff.select_final_ids(ids, excluded, 31, 0)
    with pytest.raises(ValueError):
        handoff.select_final_ids(ids, excluded, True, 0)


def test_current_backend_read_only_probe_reports_absence_without_fake_tracking():
    report = handoff.integration_report()
    assert report["tracker_available"]
    assert "Tracker" in report["tracker_callables"]
    assert "extract_detection_coords" in report["tracker_callables"]
    assert report["end_to_end_tracker_test"].startswith("not_run")
    assert report["backend_detector_selection"] == "neither"
    assert report["pipeline"]["status"] == "not_implemented"
    assert report["health_status_code"] == 200
    assert not report["health"]["capabilities"]["detection"]
    assert not report["health"]["capabilities"]["tracking"]
    assert report["analysis_route_status_code"] == 404
