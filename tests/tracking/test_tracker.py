"""Comprehensive unit tests for Task T04: Gated Association and Track Lifecycle.

Covers:
1. Moving object matched over consecutive frames
2. Two objects moving near one another without duplicate assignments
3. Detection rejected when exceeding the distance gate
4. Track surviving an allowed missed frame and ending after miss limit
5. Empty frames and empty detection lists
6. Track confirmation after exactly three observed detections, but not before
7. Unique and deterministic track IDs matching OpaqueId conventions
8. Reproducible results for identical inputs
9. Full integration round-trip with AnalysisResult schema validation
10. Reference coordinate preference with raw fallback
"""
import json
from pathlib import Path

import pytest

from app.core.config import PipelineConfig
from app.schemas.result import AnalysisResult, Detection, Provenance, RegistrationResult
from orbittrace.tracking.tracker import Tracker, extract_detection_coords

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/contracts/fixtures"


def make_detection(
    detection_id: str,
    frame_index: int,
    x: float,
    y: float,
    kind: str = "compact",
    quality_score: float = 0.8,
    x_ref: float | None = None,
    y_ref: float | None = None,
) -> Detection:
    """Helper to construct a valid Detection within exclusive bounding box."""
    bbox = (max(0.0, x - 2.0), max(0.0, y - 2.0), x + 2.0, y + 2.0)
    return Detection(
        detection_id=detection_id,
        frame_index=frame_index,
        x_raw_px=x,
        y_raw_px=y,
        bbox_raw_px=bbox,
        kind=kind,
        quality_score=quality_score,
        detector_name="test_detector",
        x_reference_px=x_ref,
        y_reference_px=y_ref,
    )


# 1. A moving object matched over consecutive frames
def test_moving_object_matched_over_consecutive_frames():
    tracker = Tracker(gate_distance_px=20.0, confirmation_observations=3)
    detections = [
        make_detection("d0", 0, 10.0, 10.0),
        make_detection("d1", 1, 14.0, 13.0),
        make_detection("d2", 2, 18.0, 16.0),
        make_detection("d3", 3, 22.0, 19.0),
    ]

    tracks = tracker.process_sequence(detections)

    assert len(tracks) == 1
    track = tracks[0]
    assert track.track_id == "track-0001"
    assert track.status == "confirmed"
    assert track.observed_count == 4
    assert len(track.points) == 4
    for i, pt in enumerate(track.points):
        assert pt.frame_index == i
        assert pt.point_type == "observed"
        assert pt.detection_id == f"d{i}"


# 2. Two objects moving near one another without duplicate assignments
def test_two_objects_moving_near_one_another_no_duplicate_assignments():
    tracker = Tracker(gate_distance_px=20.0)
    detections = [
        # Frame 0: two distinct targets separated by 10 px
        make_detection("d0_a", 0, 20.0, 20.0),
        make_detection("d0_b", 0, 20.0, 30.0),
        # Frame 1: both move right by 3 px
        make_detection("d1_a", 1, 23.0, 20.0),
        make_detection("d1_b", 1, 23.0, 30.0),
        # Frame 2: both move right by 3 px
        make_detection("d2_a", 2, 26.0, 20.0),
        make_detection("d2_b", 2, 26.0, 30.0),
    ]

    tracks = tracker.process_sequence(detections)

    assert len(tracks) == 2
    assert {t.status for t in tracks} == {"confirmed"}

    # Ensure no detection ID is assigned more than once
    assigned_det_ids = [pt.detection_id for t in tracks for pt in t.points]
    assert len(assigned_det_ids) == 6
    assert len(set(assigned_det_ids)) == 6

    # Verify track point continuity per track
    track_a = next(t for t in tracks if t.points[0].detection_id == "d0_a")
    track_b = next(t for t in tracks if t.points[0].detection_id == "d0_b")

    assert [p.detection_id for p in track_a.points] == ["d0_a", "d1_a", "d2_a"]
    assert [p.detection_id for p in track_b.points] == ["d0_b", "d1_b", "d2_b"]


# 3. A detection rejected because it exceeds the distance gate
def test_detection_rejected_exceeds_distance_gate():
    tracker = Tracker(gate_distance_px=15.0)
    detections = [
        make_detection("d0", 0, 10.0, 10.0),
        # Far away detection at frame 1: distance ~85 px > gate 15 px
        make_detection("d1", 1, 70.0, 70.0),
    ]

    tracks = tracker.process_sequence(detections)

    # Must NOT force an invalid assignment
    assert len(tracks) == 2
    track_ids = {t.track_id for t in tracks}
    assert len(track_ids) == 2

    # Track 1 has 1 observation from frame 0; track 2 has 1 observation from frame 1
    for t in tracks:
        assert t.observed_count == 1
        assert t.status == "tentative"


# 4. A track surviving an allowed missed frame and ending after miss limit
def test_track_surviving_allowed_miss_and_ending_after_miss_limit():
    # max_consecutive_misses = 2: survives 1 and 2 misses, ends at 3 misses
    tracker = Tracker(gate_distance_px=20.0, max_consecutive_misses=2)

    # Frame 0: detection -> tentative track
    t0 = tracker.process_frame(0, [make_detection("d0", 0, 10.0, 10.0)])
    assert len(t0) == 1
    assert t0[0].status == "tentative"
    assert t0[0].observed_count == 1

    # Frame 1: empty frame (miss 1) -> survives
    t1 = tracker.process_frame(1, [])
    assert len(tracker.active_tracks) == 1
    assert len(tracker.ended_tracks) == 0

    # Frame 2: detection close to previous -> matches and resets consecutive misses
    t2 = tracker.process_frame(2, [make_detection("d2", 2, 13.0, 12.0)])
    assert len(tracker.active_tracks) == 1
    assert tracker.active_tracks[0].observed_count == 2

    # Frame 3: empty frame (miss 1) -> survives
    tracker.process_frame(3, [])
    assert len(tracker.active_tracks) == 1

    # Frame 4: empty frame (miss 2) -> survives
    tracker.process_frame(4, [])
    assert len(tracker.active_tracks) == 1

    # Frame 5: empty frame (miss 3 > max 2) -> ends!
    tracker.process_frame(5, [])
    assert len(tracker.active_tracks) == 0
    assert len(tracker.ended_tracks) == 1

    ended = tracker.ended_tracks[0]
    assert ended.status == "ended"
    assert ended.observed_count == 2
    assert any("ended after 3 consecutive missed frames" in w for w in ended.warnings)


# 5. Empty frames and empty detection lists
def test_empty_frames_and_empty_detection_lists():
    tracker = Tracker()
    tracks = tracker.process_sequence(detections=[], frame_indices=[0, 1, 2, 3])
    assert tracks == []
    assert tracker.active_tracks == []
    assert tracker.ended_tracks == []


# 6. Track confirmation after three observed detections, but not before
def test_track_confirmation_after_three_observations_not_before():
    tracker = Tracker(gate_distance_px=20.0, confirmation_observations=3)

    # Observation 1
    tracker.process_frame(0, [make_detection("d0", 0, 10.0, 10.0)])
    assert len(tracker.active_tracks) == 1
    assert tracker.active_tracks[0].status == "tentative"
    assert tracker.active_tracks[0].observed_count == 1

    # Observation 2
    tracker.process_frame(1, [make_detection("d1", 1, 12.0, 12.0)])
    assert len(tracker.active_tracks) == 1
    assert tracker.active_tracks[0].status == "tentative"
    assert tracker.active_tracks[0].observed_count == 2

    # Observation 3 -> Promoted to confirmed!
    tracker.process_frame(2, [make_detection("d2", 2, 14.0, 14.0)])
    assert len(tracker.active_tracks) == 1
    assert tracker.active_tracks[0].status == "confirmed"
    assert tracker.active_tracks[0].observed_count == 3


# 7. Unique and deterministic track IDs
def test_unique_and_deterministic_track_ids():
    tracker = Tracker(gate_distance_px=10.0)
    # Five disjoint detections far apart across frames
    detections = [
        make_detection("d0_0", 0, 10.0, 10.0),
        make_detection("d0_1", 0, 50.0, 50.0),
        make_detection("d1_0", 1, 100.0, 100.0),
        make_detection("d2_0", 2, 150.0, 150.0),
    ]

    tracks = tracker.process_sequence(detections)
    track_ids = [t.track_id for t in tracks]

    # Verify uniqueness
    assert len(track_ids) == len(set(track_ids))
    # Verify deterministic naming convention: track-0001, track-0002, ...
    assert track_ids == ["track-0001", "track-0002", "track-0003", "track-0004"]


# 8. Reproducible results for identical inputs
def test_reproducible_results_for_identical_inputs():
    detections = [
        make_detection("d0_a", 0, 10.0, 10.0),
        make_detection("d0_b", 0, 50.0, 50.0),
        make_detection("d1_a", 1, 14.0, 12.0),
        make_detection("d1_b", 1, 55.0, 53.0),
        make_detection("d2_a", 2, 18.0, 14.0),
        make_detection("d2_b", 2, 60.0, 56.0),
    ]

    tracker1 = Tracker(gate_distance_px=20.0)
    tracks1 = tracker1.process_sequence(detections)

    tracker2 = Tracker(gate_distance_px=20.0)
    tracks2 = tracker2.process_sequence(detections)

    assert len(tracks1) == len(tracks2) == 2
    for t1, t2 in zip(tracks1, tracks2):
        assert t1.track_id == t2.track_id
        assert t1.status == t2.status
        assert t1.observed_count == t2.observed_count
        assert len(t1.points) == len(t2.points)
        for p1, p2 in zip(t1.points, t2.points):
            assert p1.frame_index == p2.frame_index
            assert p1.x_reference_px == p2.x_reference_px
            assert p1.y_reference_px == p2.y_reference_px
            assert p1.detection_id == p2.detection_id


# 9. Authored fixture detections validate with AnalysisResult
def test_authored_fixture_detections_roundtrip_with_analysis_result():
    fixture_path = FIXTURES / "track-result.json"
    raw_fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    # Parse fixture detections
    fixture_detections = [Detection.model_validate(d) for d in raw_fixture["detections"]]

    # Run Tracker on fixture detections
    tracker = Tracker(gate_distance_px=20.0)
    tracks = tracker.process_sequence(fixture_detections)

    assert len(tracks) == 1
    assert tracks[0].status == "confirmed"
    assert tracks[0].observed_count == 3

    # Construct complete AnalysisResult and verify strict Pydantic contract validation
    result = AnalysisResult(
        schema_version="0.1.0",
        job_id="job-t04-test",
        sequence_id="seq-t04-test",
        source_type="synthetic",
        profile="synthetic_static_stars",
        status="succeeded",
        time_basis="frame",
        coordinate_frame="reference_frame_0",
        registration=RegistrationResult(status="identity", warnings=[]),
        detections=fixture_detections,
        tracks=tracks,
        metrics=None,
        runtime_ms=None,
        warnings=[],
        provenance=Provenance(
            input_sha256=None, config_sha256=None, code_commit=None, dataset_version=None
        ),
    )

    # Validates cleanly through pydantic
    assert result.status == "succeeded"
    assert len(result.tracks) == 1
    assert result.tracks[0].observed_count == 3


# 10. Reference coordinate preference and raw fallback
def test_reference_coordinate_preference_and_raw_fallback():
    # Detection with distinct reference vs raw coordinates
    d_with_ref = make_detection("d_ref", 0, x=10.0, y=20.0, x_ref=15.0, y_ref=25.0)
    x_ref, y_ref, x_raw, y_raw = extract_detection_coords(d_with_ref)
    assert (x_ref, y_ref) == (15.0, 25.0)
    assert (x_raw, y_raw) == (10.0, 20.0)

    # Detection without reference coordinates (fallback to raw)
    d_no_ref = make_detection("d_raw", 0, x=10.0, y=20.0, x_ref=None, y_ref=None)
    x_ref2, y_ref2, x_raw2, y_raw2 = extract_detection_coords(d_no_ref)
    assert (x_ref2, y_ref2) == (10.0, 20.0)
    assert (x_raw2, y_raw2) == (10.0, 20.0)
