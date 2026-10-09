"""Algorithm-level integration test: T04 (Tracker) -> T05 (Trajectory Fitting) -> AnalysisResult.

Verifies:
1. Candidate A: Confirmed target moving across frames 0-4 (5 observations), fitted constant-velocity
   trajectory (vx ≈ 4.0, vy ≈ 3.0, speed ≈ 5.0 px/frame), exactly 2 forward predictions at frames 5 and 6.
2. Candidate B: Short 2-observation target (frames 0 and 1) that ends after missing frames 2-4 without
   a fitted trajectory (requires >= 3 observations).
3. Candidate C: Single-observation isolated flash (frame 2) that misses subsequent frames without
   a fitted trajectory.
4. Gated separation preventing cross-association between candidates A, B, and C.
5. Strict 1-to-1 detection assignment (no duplicate detection IDs).
6. Complete validation through frozen Contract 0.1.0 AnalysisResult schema.
7. Empty sequence handling.
8. Second-based time basis integration with non-null float timestamps.
"""
import pytest

from app.schemas.result import (
    AnalysisResult,
    Detection,
    Provenance,
    RegistrationResult,
)
from orbittrace.tracking.tracker import Tracker
from orbittrace.trajectory.fit import attach_trajectories


def make_detection(
    detection_id: str,
    frame_index: int,
    x: float,
    y: float,
    kind: str = "compact",
    quality_score: float = 0.8,
    timestamp_s: float | None = None,
) -> Detection:
    """Construct a valid Detection within exclusive bounding box bounds."""
    bbox = (max(0.0, x - 2.0), max(0.0, y - 2.0), x + 2.0, y + 2.0)
    return Detection(
        detection_id=detection_id,
        frame_index=frame_index,
        x_raw_px=x,
        y_raw_px=y,
        bbox_raw_px=bbox,
        kind=kind,
        quality_score=quality_score,
        detector_name="synthetic_detector",
        x_reference_px=x,
        y_reference_px=y,
    )


def test_synthetic_pipeline_integration_a_b_c():
    """Deterministic integration of Candidate A (5 obs), B (2 obs), and C (1 obs)."""
    # 1. Generate deterministic detections across 5 frames (0-4)
    # Candidate A: moves from (20, 20) with vx=4.0, vy=3.0
    dets_a = [
        make_detection("det_a_0", 0, 20.0, 20.0),
        make_detection("det_a_1", 1, 24.0, 23.0),
        make_detection("det_a_2", 2, 28.0, 26.0),
        make_detection("det_a_3", 3, 32.0, 29.0),
        make_detection("det_a_4", 4, 36.0, 32.0),
    ]

    # Candidate B: observed at frames 0 and 1, positioned far from A (>80 px)
    dets_b = [
        make_detection("det_b_0", 0, 100.0, 100.0),
        make_detection("det_b_1", 1, 104.0, 103.0),
    ]

    # Candidate C: single observation at frame 2, positioned far from A and B (>100 px)
    dets_c = [
        make_detection("det_c_2", 2, 200.0, 200.0),
    ]

    all_detections = dets_a + dets_b + dets_c

    # 2. Run T04 Tracker
    # Config: 20 px gate, 3 confirmation observations, max 2 consecutive misses
    tracker = Tracker(
        gate_distance_px=20.0,
        confirmation_observations=3,
        max_consecutive_misses=2,
    )
    raw_tracks = tracker.process_sequence(all_detections, frame_indices=range(5))

    # Must produce exactly 3 tracks
    assert len(raw_tracks) == 3

    # 3. Run T05 Trajectory Fitting
    coordinate_frame = "reference_frame_0"
    time_basis = "frame"
    tracks_with_traj = attach_trajectories(
        raw_tracks,
        coordinate_frame=coordinate_frame,
        time_basis=time_basis,
        prediction_horizon=2,
    )

    assert len(tracks_with_traj) == 3

    # 4. Identify tracks by observation contents (independent of ID order)
    track_a = next(
        t for t in tracks_with_traj
        if any(p.detection_id == "det_a_0" for p in t.points)
    )
    track_b = next(
        t for t in tracks_with_traj
        if any(p.detection_id == "det_b_0" for p in t.points)
    )
    track_c = next(
        t for t in tracks_with_traj
        if any(p.detection_id == "det_c_2" for p in t.points)
    )

    # 5. Assertions on Candidate A
    assert track_a.status == "confirmed"
    assert track_a.observed_count == 5
    assert len(track_a.points) == 5
    assert [p.detection_id for p in track_a.points] == [
        "det_a_0", "det_a_1", "det_a_2", "det_a_3", "det_a_4"
    ]
    assert track_a.trajectory is not None
    traj_a = track_a.trajectory
    assert traj_a.model == "constant_velocity"
    assert traj_a.coordinate_frame == coordinate_frame
    assert traj_a.time_basis == time_basis
    assert traj_a.vx == pytest.approx(4.0, abs=1e-5)
    assert traj_a.vy == pytest.approx(3.0, abs=1e-5)
    assert traj_a.speed == pytest.approx(5.0, abs=1e-5)
    assert traj_a.speed_unit == "px/frame"
    assert traj_a.fit_rmse_px == pytest.approx(0.0, abs=1e-5)
    assert traj_a.observations_used == 5
    assert traj_a.reference_epoch == 0.0
    assert traj_a.x_at_epoch_px == pytest.approx(20.0, abs=1e-5)
    assert traj_a.y_at_epoch_px == pytest.approx(20.0, abs=1e-5)

    # Candidate A predictions: exactly 2 forward predictions at frames 5 and 6
    assert len(traj_a.predictions) == 2
    pred1, pred2 = traj_a.predictions
    assert pred1.frame_index == 5
    assert pred1.point_type == "extrapolated"
    assert pred1.detection_id is None
    assert pred1.timestamp_s is None
    assert pred1.x_reference_px == pytest.approx(40.0, abs=1e-5)
    assert pred1.y_reference_px == pytest.approx(35.0, abs=1e-5)

    assert pred2.frame_index == 6
    assert pred2.point_type == "extrapolated"
    assert pred2.detection_id is None
    assert pred2.timestamp_s is None
    assert pred2.x_reference_px == pytest.approx(44.0, abs=1e-5)
    assert pred2.y_reference_px == pytest.approx(38.0, abs=1e-5)

    # 6. Assertions on Candidate B
    # Disappeared after frame 1; misses frames 2, 3, 4 (3 misses > 2 limit) -> ended
    assert track_b.status == "ended"
    assert track_b.observed_count == 2
    assert len(track_b.points) == 2
    assert [p.detection_id for p in track_b.points] == ["det_b_0", "det_b_1"]
    assert track_b.trajectory is None  # Insufficient observations (< 3)

    # 7. Assertions on Candidate C
    # Observed only at frame 2; misses frames 3 and 4 (2 misses <= 2 limit) -> tentative
    assert track_c.status == "tentative"
    assert track_c.observed_count == 1
    assert len(track_c.points) == 1
    assert track_c.points[0].detection_id == "det_c_2"
    assert track_c.trajectory is None  # Insufficient observations (< 3)

    # 8. Verify no duplicate detection assignments
    assigned_det_ids = [
        p.detection_id for t in tracks_with_traj for p in t.points if p.point_type == "observed"
    ]
    assert len(assigned_det_ids) == len(all_detections) == 8
    assert len(set(assigned_det_ids)) == 8

    # 9. Build and validate full AnalysisResult schema
    result = AnalysisResult(
        schema_version="0.1.0",
        job_id="job-integration-001",
        sequence_id="seq-integration-001",
        source_type="synthetic",
        profile="synthetic_static_stars",
        status="succeeded",
        time_basis=time_basis,
        coordinate_frame=coordinate_frame,
        registration=RegistrationResult(status="identity", warnings=[]),
        detections=all_detections,
        tracks=tracks_with_traj,
        metrics=None,
        runtime_ms=8.5,
        warnings=[],
        provenance=Provenance(
            input_sha256=None,
            config_sha256=None,
            code_commit=None,
            dataset_version=None,
        ),
    )

    # Pydantic validation guarantees full contract adherence
    assert result.status == "succeeded"
    assert len(result.tracks) == 3
    assert len(result.detections) == 8


def test_synthetic_pipeline_integration_empty_sequence():
    """Integration handling of empty sequence (zero detections over 5 frames)."""
    tracker = Tracker(gate_distance_px=20.0)
    raw_tracks = tracker.process_sequence(detections=[], frame_indices=range(5))

    tracks_with_traj = attach_trajectories(
        raw_tracks,
        coordinate_frame="reference_frame_0",
        time_basis="frame",
    )

    result = AnalysisResult(
        schema_version="0.1.0",
        job_id="job-empty-001",
        sequence_id="seq-empty-001",
        source_type="synthetic",
        profile="synthetic_static_stars",
        status="succeeded",
        time_basis="frame",
        coordinate_frame="reference_frame_0",
        registration=RegistrationResult(status="identity", warnings=[]),
        detections=[],
        tracks=tracks_with_traj,
        metrics=None,
        runtime_ms=1.2,
        warnings=["Zero detections observed in sequence"],
        provenance=Provenance(
            input_sha256=None, config_sha256=None, code_commit=None, dataset_version=None
        ),
    )

    assert result.status == "succeeded"
    assert result.tracks == []
    assert result.detections == []


def test_synthetic_pipeline_integration_second_basis():
    """Integration test with time_basis='second' and non-null float timestamps."""
    coordinate_frame = "reference_frame_0"
    time_basis = "second"
    frame_timestamps = {0: 0.0, 1: 0.5, 2: 1.0}

    # 3 observations moving at vx = 8.0 px/s, vy = 6.0 px/s (speed = 10.0 px/s)
    detections = [
        make_detection("det_s_0", 0, 10.0, 10.0, timestamp_s=0.0),
        make_detection("det_s_1", 1, 14.0, 13.0, timestamp_s=0.5),
        make_detection("det_s_2", 2, 18.0, 16.0, timestamp_s=1.0),
    ]

    tracker = Tracker(gate_distance_px=20.0)
    raw_tracks = tracker.process_sequence(
        detections, frame_indices=[0, 1, 2], frame_timestamps=frame_timestamps
    )

    tracks_with_traj = attach_trajectories(
        raw_tracks,
        coordinate_frame=coordinate_frame,
        time_basis=time_basis,
        frame_timestamps=frame_timestamps,
    )

    assert len(tracks_with_traj) == 1
    track = tracks_with_traj[0]
    assert track.status == "confirmed"
    assert track.trajectory is not None
    assert track.trajectory.time_basis == "second"
    assert track.trajectory.speed_unit == "px/s"
    assert track.trajectory.vx == pytest.approx(8.0, abs=1e-5)
    assert track.trajectory.vy == pytest.approx(6.0, abs=1e-5)
    assert track.trajectory.speed == pytest.approx(10.0, abs=1e-5)

    # All predictions must carry float timestamp_s in second mode
    assert all(isinstance(p.timestamp_s, float) for p in track.trajectory.predictions)

    result = AnalysisResult(
        schema_version="0.1.0",
        job_id="job-sec-001",
        sequence_id="seq-sec-001",
        source_type="synthetic",
        profile="synthetic_static_stars",
        status="succeeded",
        time_basis=time_basis,
        coordinate_frame=coordinate_frame,
        registration=RegistrationResult(status="identity", warnings=[]),
        detections=detections,
        tracks=tracks_with_traj,
        metrics=None,
        runtime_ms=3.4,
        warnings=[],
        provenance=Provenance(
            input_sha256=None, config_sha256=None, code_commit=None, dataset_version=None
        ),
    )

    assert result.status == "succeeded"
    assert result.tracks[0].trajectory.speed == 10.0
