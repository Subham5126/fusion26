"""Run real detector outputs through available untouched Member 3 source.

CV_T06_TRACKING_SNAPSHOT may point at the two byte-identical files exported by
orbittrace.detection.example. Otherwise use the installed tracking modules.
Real ESA tests skip explicitly if the external local images are unavailable.
"""

import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import numpy as np
import pytest

from app.schemas.result import AnalysisResult, Provenance, RegistrationResult
from astrotrace.datasets import SpotGeoDataset
from astrotrace.detection.optimized import OptimizedConfig, detect_optimized_sequence
from orbittrace.detection import detect_sequence


@pytest.fixture(scope="module")
def tracking():
    snapshot = os.environ.get("CV_T06_TRACKING_SNAPSHOT")
    if snapshot:
        modules = []
        for name, filename in (("_test_cv_t06_tracker", "tracker.py"), ("_test_cv_t06_fit", "fit.py")):
            path = Path(snapshot) / filename
            if not path.is_file():
                pytest.fail(f"Missing explicitly requested snapshot: {path}")
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            modules.append(module)
    else:
        try:
            modules = [importlib.import_module("orbittrace.tracking.tracker"),
                       importlib.import_module("orbittrace.trajectory.fit")]
        except ModuleNotFoundError as exc:
            if exc.name not in ("orbittrace.tracking.tracker", "orbittrace.trajectory.fit"):
                raise
            pytest.skip("Member 3 modules unavailable; set CV_T06_TRACKING_SNAPSHOT after exporting the fetched ref")
    return modules[0].Tracker, modules[1].attach_trajectories


def consume(tracking, detections, frame_count, *, timestamps=None, source_type="synthetic", dimensions=(80, 64)):
    Tracker, attach = tracking
    tracks = Tracker().process_sequence(detections, frame_indices=range(frame_count), frame_timestamps=timestamps)
    tracks = attach(tracks, coordinate_frame="raw", time_basis="second" if timestamps else "frame",
                    frame_dimensions=dimensions, frame_timestamps=timestamps)
    result = AnalysisResult(
        schema_version="0.1.0", job_id="cv-t06-test", sequence_id="test-images",
        source_type=source_type, profile="spotgeo" if source_type == "real" else "synthetic_static_stars",
        status="succeeded", time_basis="second" if timestamps else "frame", coordinate_frame="raw",
        registration=RegistrationResult(status="failed" if source_type == "real" else "identity", warnings=[]),
        detections=detections, tracks=tracks, metrics=None, runtime_ms=None,
        warnings=["Real raw-fallback diagnostic; registration not estimated"] if source_type == "real" else [],
        provenance=Provenance(input_sha256=None, config_sha256=None, code_commit=None, dataset_version=None),
    )
    json.loads(result.model_dump_json())
    assigned = [p for t in tracks for p in t.points]
    assert all(p.point_type == "observed" for p in assigned)
    assert len(assigned) == len(detections)
    assert len({p.detection_id for p in assigned}) == len(assigned)
    lookup = {d.detection_id: d for d in detections}
    for point in assigned:
        detection = lookup[point.detection_id]
        assert detection.frame_index == point.frame_index
        assert (point.x_raw_px, point.y_raw_px) == (detection.x_raw_px, detection.y_raw_px)
    for track in tracks:
        assert track.observed_count == len(track.points)
        if track.trajectory:
            assert track.trajectory.observations_used == track.observed_count
            assert all(p.point_type == "extrapolated" and p.detection_id is None
                       for p in track.trajectory.predictions)
    return result


@pytest.mark.parametrize("timed", [False, True])
def test_actual_synthetic_pixels_with_one_gap(tracking, timed):
    yy, xx = np.mgrid[:64, :80]
    frames = [np.rint(30+100*np.exp(-.5*((xx-(20.25+4*i))**2+(yy-(28.75+1.5*i))**2))).astype(np.uint8)
              if i != 2 else np.full((64, 80), 30, np.uint8) for i in range(5)]
    times = [i*.5 for i in range(5)] if timed else None
    detections = detect_sequence(frames, sequence_id="moving", profile="synthetic_static_stars", timestamps_s=times)
    assert [d.frame_index for d in detections] == [0, 1, 3, 4]
    result = consume(tracking, detections, 5, timestamps=dict(enumerate(times)) if times else None)
    assert len(result.tracks) == 1
    track = result.tracks[0]
    assert track.status == "confirmed" and track.observed_count == 4
    assert [p.frame_index for p in track.points] == [0, 1, 3, 4]
    trajectory = track.trajectory
    assert trajectory.speed_unit == ("px/s" if timed else "px/frame")
    assert trajectory.vx == pytest.approx(8 if timed else 4, abs=.1)
    assert trajectory.vy == pytest.approx(3 if timed else 1.5, abs=.1)
    assert [p.frame_index for p in trajectory.predictions] == [5, 6]


def test_all_empty_images_consumed_with_explicit_frame_indices(tracking):
    detections = detect_sequence([np.zeros((64, 80), np.uint8)]*5, sequence_id="empty")
    assert consume(tracking, detections, 5).tracks == []


@pytest.mark.parametrize("split,sequence_id,counts", [
    ("train", "84", [7, 7, 6, 8, 6]),
    ("test", "57", [7, 4, 7, 4, 14]),
    ("test", "1107", [0, 0, 0, 0, 0]),
])
@pytest.mark.parametrize("profile", ["cv_t04", "precision"])
def test_real_esa_native_geometry_and_tracking(tracking, split, sequence_id, counts, profile):
    source = Path(os.environ.get("CV_T06_REAL_SOURCE", str(Path(__file__).resolve().parents[2] / "data/raw/SpotGEOv2")))
    if not source.is_dir():
        pytest.skip("External ESA images unavailable; set CV_T06_REAL_SOURCE")
    dataset = SpotGeoDataset(source, split=split)
    sequence = dataset.load_sequence(sequence_id)
    frames = [f.pixels for f in sequence.frames]
    from astrotrace.detection.precision import precision_config
    config = (OptimizedConfig(threshold_sigma=4.5, max_context_elongation=2.)
              if profile == "cv_t04" else precision_config()).to_dict()
    actual = detect_sequence(frames, sequence_id=f"{split}-{sequence_id}",
                             config=config if profile == "cv_t04" else None)
    expected = detect_optimized_sequence(sequence, config)
    # Compare every scientific field/evidence value against the unchanged CV-T04.
    original = [d for frame in expected.frames for d in frame.detections]
    assert [{k: v for k, v in d.model_dump().items() if k != "detection_id"} for d in actual] == [
        {k: v for k, v in d.model_dump().items() if k != "detection_id"} for d in original]
    if profile == "cv_t04":
        assert [sum(d.frame_index == i for d in actual) for i in range(5)] == counts
    else:
        assert all(sum(d.frame_index == i for d in actual) <= counts[i] for i in range(5))
    assert len({d.detection_id for d in actual}) == len(actual)
    consume(tracking, actual, 5, source_type="real", dimensions=(640, 480))
