"""Comprehensive unit tests for Task T05: Constant-Velocity Trajectory Fitting.

Covers:
1. Horizontal linear trajectory with known velocity
2. Vertical and diagonal trajectory
3. Exactly three valid observations
4. Fewer than three observations (returns None)
5. Irregular frame indices
6. Irregular timestamps with time_basis == 'second'
7. Correct RMSE for noisy observations
8. Exactly two forward predictions
9. Predictions always have detection_id = None and point_type = 'extrapolated'
10. Correct prediction timestamps for both time bases
11. Coordinate-frame consistency
12. Exclusion of interpolated and extrapolated points from fitting
13. Invalid, duplicated, or missing timestamps
14. Degenerate inputs and validation rules
15. Compatibility with authored track-result.json fixture
"""
import json
import math
from pathlib import Path

import pytest

from app.schemas.result import AnalysisResult, Detection, Provenance, RegistrationResult, Track, TrackPoint
from orbittrace.trajectory.fit import attach_trajectories, fit_track_trajectory, fit_trajectory

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/contracts/fixtures"


def make_track_point(
    frame_index: int,
    x: float,
    y: float,
    point_type: str = "observed",
    detection_id: str | None = "d0",
    timestamp_s: float | None = None,
    out_of_field: bool | None = None,
) -> TrackPoint:
    """Helper to create TrackPoint adhering to Contract 0.1.0."""
    det_id = detection_id if point_type == "observed" else None
    return TrackPoint(
        frame_index=frame_index,
        timestamp_s=timestamp_s,
        x_reference_px=x,
        y_reference_px=y,
        x_raw_px=x,
        y_raw_px=y,
        point_type=point_type,
        detection_id=det_id,
        out_of_field=out_of_field,
    )


# 1. A horizontal linear trajectory with known velocity
def test_horizontal_linear_trajectory():
    points = [
        make_track_point(0, 10.0, 50.0, detection_id="d0"),
        make_track_point(1, 15.0, 50.0, detection_id="d1"),
        make_track_point(2, 20.0, 50.0, detection_id="d2"),
        make_track_point(3, 25.0, 50.0, detection_id="d3"),
    ]
    traj = fit_trajectory(points, time_basis="frame")

    assert traj is not None
    assert traj.model == "constant_velocity"
    assert traj.vx == pytest.approx(5.0)
    assert traj.vy == pytest.approx(0.0)
    assert traj.speed == pytest.approx(5.0)
    assert traj.speed_unit == "px/frame"
    assert traj.fit_rmse_px == pytest.approx(0.0)
    assert traj.reference_epoch == 0.0
    assert traj.x_at_epoch_px == pytest.approx(10.0)
    assert traj.y_at_epoch_px == pytest.approx(50.0)

    # Predictions at frames 4 and 5
    assert len(traj.predictions) == 2
    assert traj.predictions[0].frame_index == 4
    assert traj.predictions[0].x_reference_px == pytest.approx(30.0)
    assert traj.predictions[0].y_reference_px == pytest.approx(50.0)
    assert traj.predictions[1].frame_index == 5
    assert traj.predictions[1].x_reference_px == pytest.approx(35.0)
    assert traj.predictions[1].y_reference_px == pytest.approx(50.0)


# 2. A vertical or diagonal trajectory
def test_diagonal_trajectory():
    points = [
        make_track_point(0, 10.0, 20.0, detection_id="d0"),
        make_track_point(1, 13.0, 24.0, detection_id="d1"),
        make_track_point(2, 16.0, 28.0, detection_id="d2"),
    ]
    traj = fit_trajectory(points, time_basis="frame")

    assert traj is not None
    assert traj.vx == pytest.approx(3.0)
    assert traj.vy == pytest.approx(4.0)
    assert traj.speed == pytest.approx(5.0)  # sqrt(3^2 + 4^2) = 5
    assert traj.fit_rmse_px == pytest.approx(0.0)


# 3. Exactly three valid observations
def test_exactly_three_observations():
    points = [
        make_track_point(0, 0.0, 0.0, detection_id="d0"),
        make_track_point(1, 2.0, 1.0, detection_id="d1"),
        make_track_point(2, 4.0, 2.0, detection_id="d2"),
    ]
    traj = fit_trajectory(points)
    assert traj is not None
    assert traj.observations_used == 3


# 4. Fewer than three observations
def test_fewer_than_three_observations_returns_none():
    assert fit_trajectory([]) is None

    one_point = [make_track_point(0, 1.0, 1.0, detection_id="d0")]
    assert fit_trajectory(one_point) is None

    two_points = [
        make_track_point(0, 1.0, 1.0, detection_id="d0"),
        make_track_point(1, 2.0, 2.0, detection_id="d1"),
    ]
    assert fit_trajectory(two_points) is None


# 5. Irregular frame indices
def test_irregular_frame_indices():
    # Observed at frame 0, 2, 5
    # x(f) = 10 + 2*f -> f=0: 10, f=2: 14, f=5: 20
    points = [
        make_track_point(0, 10.0, 10.0, detection_id="d0"),
        make_track_point(2, 14.0, 10.0, detection_id="d1"),
        make_track_point(5, 20.0, 10.0, detection_id="d2"),
    ]
    traj = fit_trajectory(points, time_basis="frame")

    assert traj is not None
    assert traj.vx == pytest.approx(2.0)
    assert traj.vy == pytest.approx(0.0)
    assert traj.fit_rmse_px == pytest.approx(0.0)
    # Next 2 predictions from last frame 5: frames 6 and 7
    assert traj.predictions[0].frame_index == 6
    assert traj.predictions[0].x_reference_px == pytest.approx(22.0)
    assert traj.predictions[1].frame_index == 7
    assert traj.predictions[1].x_reference_px == pytest.approx(24.0)


# 6. Irregular timestamps with time_basis == 'second'
def test_irregular_timestamps_second_basis():
    # t = 0.0, 0.5, 2.0
    # x(t) = 10 + 4*t -> 10.0, 12.0, 18.0
    # y(t) = 20 + 3*t -> 20.0, 21.5, 26.0
    points = [
        make_track_point(0, 10.0, 20.0, detection_id="d0", timestamp_s=0.0),
        make_track_point(1, 12.0, 21.5, detection_id="d1", timestamp_s=0.5),
        make_track_point(2, 18.0, 26.0, detection_id="d2", timestamp_s=2.0),
    ]
    traj = fit_trajectory(points, time_basis="second")

    assert traj is not None
    assert traj.time_basis == "second"
    assert traj.speed_unit == "px/s"
    assert traj.vx == pytest.approx(4.0)
    assert traj.vy == pytest.approx(3.0)
    assert traj.speed == pytest.approx(5.0)
    assert traj.fit_rmse_px == pytest.approx(0.0)
    assert all(isinstance(p.timestamp_s, float) for p in traj.predictions)
    # Predictions must have strictly increasing timestamps > 2.0
    assert traj.predictions[0].timestamp_s > 2.0
    assert traj.predictions[1].timestamp_s > traj.predictions[0].timestamp_s


# 7. Correct RMSE for noisy observations
def test_rmse_noisy_observations():
    # t = [0, 1, 2]
    # Ground truth: x = 10 + 2*t, y = 10
    # Noisy points: x_0 = 10, x_1 = 13 (offset by +1), x_2 = 14
    # Mean t = 1, Mean x = 37/3
    # vx = 2.0, x0 = 10.333333
    # Fitted: x_0_hat = 10.3333, x_1_hat = 12.3333, x_2_hat = 14.3333
    # dx = [-1/3, +2/3, -1/3]
    # sum(dx^2) = 1/9 + 4/9 + 1/9 = 6/9 = 2/3
    # rmse = sqrt((2/3)/3) = sqrt(2/9) ~= 0.47140452
    points = [
        make_track_point(0, 10.0, 10.0, detection_id="d0"),
        make_track_point(1, 13.0, 10.0, detection_id="d1"),
        make_track_point(2, 14.0, 10.0, detection_id="d2"),
    ]
    traj = fit_trajectory(points, time_basis="frame")

    assert traj is not None
    expected_rmse = math.sqrt(2.0 / 9.0)
    assert traj.fit_rmse_px == pytest.approx(expected_rmse, rel=1e-5)


# 8. Exactly two forward predictions
def test_exactly_two_forward_predictions():
    points = [
        make_track_point(10, 10.0, 10.0, detection_id="d0"),
        make_track_point(11, 12.0, 12.0, detection_id="d1"),
        make_track_point(12, 14.0, 14.0, detection_id="d2"),
    ]
    traj = fit_trajectory(points, prediction_horizon=2)

    assert traj is not None
    assert len(traj.predictions) == 2
    assert [p.frame_index for p in traj.predictions] == [13, 14]


# 9. Predictions always have detection_id = None
def test_predictions_have_null_detection_id_and_extrapolated():
    points = [
        make_track_point(0, 10.0, 10.0, detection_id="d0"),
        make_track_point(1, 12.0, 12.0, detection_id="d1"),
        make_track_point(2, 14.0, 14.0, detection_id="d2"),
    ]
    traj = fit_trajectory(points)

    assert traj is not None
    for p in traj.predictions:
        assert p.detection_id is None
        assert p.point_type == "extrapolated"
        assert p.x_raw_px is None
        assert p.y_raw_px is None


# 10. Correct prediction timestamps for both time bases
def test_prediction_timestamps_per_time_basis():
    # Frame basis: timestamp_s must be None
    frame_pts = [
        make_track_point(0, 1.0, 1.0, detection_id="d0"),
        make_track_point(1, 2.0, 2.0, detection_id="d1"),
        make_track_point(2, 3.0, 3.0, detection_id="d2"),
    ]
    traj_frame = fit_trajectory(frame_pts, time_basis="frame")
    assert all(p.timestamp_s is None for p in traj_frame.predictions)

    # Second basis: timestamp_s must be float
    sec_pts = [
        make_track_point(0, 1.0, 1.0, detection_id="d0", timestamp_s=0.0),
        make_track_point(1, 2.0, 2.0, detection_id="d1", timestamp_s=1.0),
        make_track_point(2, 3.0, 3.0, detection_id="d2", timestamp_s=2.0),
    ]
    traj_sec = fit_trajectory(sec_pts, time_basis="second")
    assert all(isinstance(p.timestamp_s, float) for p in traj_sec.predictions)


# 11. Coordinate-frame consistency
def test_coordinate_frame_consistency():
    points = [
        make_track_point(0, 1.0, 1.0, detection_id="d0"),
        make_track_point(1, 2.0, 2.0, detection_id="d1"),
        make_track_point(2, 3.0, 3.0, detection_id="d2"),
    ]
    traj = fit_trajectory(points, coordinate_frame="camera_wcs_0")
    assert traj.coordinate_frame == "camera_wcs_0"


# 12. Exclusion of interpolated and extrapolated points from fitting
def test_exclusion_of_non_observed_points():
    points = [
        make_track_point(0, 10.0, 10.0, point_type="observed", detection_id="d0"),
        make_track_point(1, 15.0, 15.0, point_type="interpolated", detection_id=None),
        make_track_point(2, 20.0, 20.0, point_type="observed", detection_id="d2"),
        make_track_point(3, 99.0, 99.0, point_type="extrapolated", detection_id=None),
        make_track_point(4, 30.0, 30.0, point_type="observed", detection_id="d4"),
    ]
    traj = fit_trajectory(points)

    assert traj is not None
    # Only frames 0, 2, 4 are observed
    assert traj.observations_used == 3
    # v = (30 - 10) / (4 - 0) = 5.0
    assert traj.vx == pytest.approx(5.0)
    assert traj.vy == pytest.approx(5.0)
    assert traj.fit_rmse_px == pytest.approx(0.0)


# 13. Invalid, duplicated, or missing timestamps
def test_invalid_or_missing_timestamps_in_second_mode():
    # Missing timestamp in second mode
    missing_ts = [
        make_track_point(0, 1.0, 1.0, detection_id="d0", timestamp_s=1.0),
        make_track_point(1, 2.0, 2.0, detection_id="d1", timestamp_s=None),
        make_track_point(2, 3.0, 3.0, detection_id="d2", timestamp_s=3.0),
    ]
    with pytest.raises(ValueError, match="timestamp_s"):
        fit_trajectory(missing_ts, time_basis="second")

    # Non-increasing / duplicated timestamps
    dup_ts = [
        make_track_point(0, 1.0, 1.0, detection_id="d0", timestamp_s=1.0),
        make_track_point(1, 2.0, 2.0, detection_id="d1", timestamp_s=1.0),
        make_track_point(2, 3.0, 3.0, detection_id="d2", timestamp_s=2.0),
    ]
    with pytest.raises(ValueError, match="strictly increasing"):
        fit_trajectory(dup_ts, time_basis="second")


# 14. Degenerate inputs and contract validation
def test_degenerate_identical_frame_indices():
    # All points have identical frame index -> cannot fit
    points = [
        make_track_point(0, 1.0, 1.0, detection_id="d0"),
        make_track_point(0, 2.0, 2.0, detection_id="d1"),
        make_track_point(0, 3.0, 3.0, detection_id="d2"),
    ]
    assert fit_trajectory(points) is None


# 15. Existing authored fixture compatibility
def test_authored_fixture_compatibility():
    fixture_path = FIXTURES / "track-result.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))

    track_data = data["tracks"][0]
    points = [TrackPoint.model_validate(p) for p in track_data["points"]]

    traj = fit_trajectory(
        points=points,
        coordinate_frame=data["coordinate_frame"],
        time_basis=data["time_basis"],
    )

    assert traj is not None
    assert traj.vx == pytest.approx(4.0)
    assert traj.vy == pytest.approx(3.0)
    assert traj.speed == pytest.approx(5.0)
    assert traj.speed_unit == "px/frame"
    assert traj.reference_epoch == 0.0
    assert traj.x_at_epoch_px == pytest.approx(10.0)
    assert traj.y_at_epoch_px == pytest.approx(12.0)

    # Attach to track and test full AnalysisResult round-trip
    track = Track(
        track_id="fixture-track-1",
        status="confirmed",
        candidate_label="orbital-object candidate; identity unverified",
        points=points,
        observed_count=len(points),
        quality_score=0.5,
        warnings=["Fitted trajectory test"],
        trajectory=traj,
    )

    detections = [Detection.model_validate(d) for d in data["detections"]]
    result = AnalysisResult(
        schema_version="0.1.0",
        job_id="test-job-t05",
        sequence_id="test-seq-t05",
        source_type="synthetic",
        profile="synthetic_static_stars",
        status="succeeded",
        time_basis="frame",
        coordinate_frame="reference_frame_0",
        registration=RegistrationResult(status="identity", warnings=[]),
        detections=detections,
        tracks=[track],
        metrics=None,
        runtime_ms=None,
        warnings=[],
        provenance=Provenance(
            input_sha256=None, config_sha256=None, code_commit=None, dataset_version=None
        ),
    )

    assert result.status == "succeeded"
    assert result.tracks[0].trajectory.speed == 5.0


def test_attach_trajectories_helper():
    points = [
        make_track_point(0, 10.0, 10.0, detection_id="d0"),
        make_track_point(1, 14.0, 13.0, detection_id="d1"),
        make_track_point(2, 18.0, 16.0, detection_id="d2"),
    ]
    track = Track(
        track_id="track-0001",
        status="confirmed",
        candidate_label="orbital-object candidate; identity unverified",
        points=points,
        observed_count=3,
        quality_score=0.8,
        warnings=[],
        trajectory=None,
    )

    updated_tracks = attach_trajectories([track])
    assert len(updated_tracks) == 1
    assert updated_tracks[0].trajectory is not None
    assert updated_tracks[0].trajectory.observations_used == 3
    assert len(updated_tracks[0].trajectory.predictions) == 2
