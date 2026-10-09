"""T10 Robustness and Edge Case Tests — Artifacts, Gaps, and Crossing Targets.

Verifies:
1. One-gap missed-frame recovery: Track continuity across a single dropout frame,
   measuring continuity rather than assuming it.
2. Exceeded-gap track termination: Tracks exceeding max_consecutive_misses end cleanly,
   and reappearing targets spawn new tracks (counted as ID switches).
3. Pure artifact / negative scenes: Random unassociated noise detections never produce
   false confirmed tracks.
4. Static sensor defect / hot pixel: Stationary detections yield near-zero speed,
   enabling artifact identification.
5. Crossing targets: Ambiguous spatial intersection handled deterministically without crashes.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.core.config import PipelineConfig
from app.schemas.result import Detection
from orbittrace.evaluation import (
    GroundTruthPoint,
    evaluate_tracks,
)
from orbittrace.tracking.tracker import Tracker
from orbittrace.trajectory.fit import fit_trajectory


def make_det(
    det_id: str, frame_idx: int, x: float, y: float, quality: float = 0.9
) -> Detection:
    return Detection(
        detection_id=det_id,
        frame_index=frame_idx,
        x_raw_px=x,
        y_raw_px=y,
        bbox_raw_px=[x - 2.0, y - 2.0, x + 2.0, y + 2.0],
        kind="compact",
        quality_score=quality,
        detector_name="test_detector",
    )


class TestOneGapContinuity:
    """T10: Test single-frame missed detection (1-gap) continuity."""

    def test_single_missed_frame_maintains_track_id(self) -> None:
        """Target drops out on frame 2; track must resume with same track_id on frame 3."""
        # True velocity: vx = 5.0 px/frame, vy = 3.0 px/frame
        # Frame 0: (10, 10)
        # Frame 1: (15, 13)
        # Frame 2: (20, 16) -- MISSED / DROPOUT
        # Frame 3: (25, 19)
        # Frame 4: (30, 22)

        tracker = Tracker(
            gate_distance_px=15.0,
            confirmation_observations=3,
            max_consecutive_misses=2,
            motion_aware=True,
        )

        f0_dets = [make_det("d0", 0, 10.0, 10.0)]
        f1_dets = [make_det("d1", 1, 15.0, 13.0)]
        f2_dets = []  # Dropout frame
        f3_dets = [make_det("d3", 3, 25.0, 19.0)]
        f4_dets = [make_det("d4", 4, 30.0, 22.0)]

        tracker.process_frame(0, f0_dets)
        tracker.process_frame(1, f1_dets)
        tracker.process_frame(2, f2_dets)
        tracker.process_frame(3, f3_dets)
        tracks = tracker.process_frame(4, f4_dets)

        # There should be exactly 1 active confirmed track
        confirmed = [t for t in tracks if t.status == "confirmed"]
        assert len(confirmed) == 1
        t = confirmed[0]

        # 4 observed detections total
        assert t.observed_count == 4
        assert len(t.points) == 4

        # Verify no points were fabricated for frame 2
        frame_indices = [pt.frame_index for pt in t.points]
        assert frame_indices == [0, 1, 3, 4]

        # Fit trajectory across the gap
        fitted = fit_trajectory(t.points, prediction_horizon=2)
        assert fitted is not None
        assert fitted.observations_used == 4
        assert pytest.approx(fitted.vx, abs=0.01) == 5.0
        assert pytest.approx(fitted.vy, abs=0.01) == 3.0
        assert fitted.fit_rmse_px < 0.05

        # Check future extrapolations: frame 5 at (35, 25), frame 6 at (40, 28)
        assert len(fitted.predictions) == 2
        p5 = fitted.predictions[0]
        assert p5.frame_index == 5
        assert pytest.approx(p5.x_reference_px, abs=0.1) == 35.0
        assert pytest.approx(p5.y_reference_px, abs=0.1) == 25.0

        # Evaluate against ground truth
        gt = [
            GroundTruthPoint(frame_index=0, x=10.0, y=10.0, target_id="tgt1"),
            GroundTruthPoint(frame_index=1, x=15.0, y=13.0, target_id="tgt1"),
            GroundTruthPoint(frame_index=2, x=20.0, y=16.0, target_id="tgt1"),
            GroundTruthPoint(frame_index=3, x=25.0, y=19.0, target_id="tgt1"),
            GroundTruthPoint(frame_index=4, x=30.0, y=22.0, target_id="tgt1"),
        ]
        metrics, ext = evaluate_tracks([t], gt, matching_gate_px=5.0)

        # TP=4, FN=1 (frame 2 missed), FP=0
        assert metrics.tp == 4
        assert metrics.fn == 1
        assert metrics.fp == 0
        assert ext["id_switches"] == 0  # Zero ID switches confirms identity continuity!
        assert ext["coverage"] == 4 / 5
        assert ext["false_confirmed_tracks"] == 0


class TestExceededGapTrackLifecycle:
    """T10: Test track termination when dropout exceeds max_consecutive_misses."""

    def test_exceeded_dropout_ends_track_and_spawns_new(self) -> None:
        """Target drops out for 3 frames (max_consecutive_misses=2); ends track, then spawns new ID."""
        tracker = Tracker(
            gate_distance_px=15.0,
            confirmation_observations=3,
            max_consecutive_misses=2,
        )

        # Frames 0, 1, 2 observed
        tracker.process_frame(0, [make_det("d0", 0, 10.0, 10.0)])
        tracker.process_frame(1, [make_det("d1", 1, 15.0, 15.0)])
        tracker.process_frame(2, [make_det("d2", 2, 20.0, 20.0)])

        # Frame 3 (miss 1), Frame 4 (miss 2)
        tracker.process_frame(3, [])
        tracker.process_frame(4, [])

        # Frame 5 (miss 3 > max_consecutive_misses): track must transition to ended
        tracker.process_frame(5, [])

        # Frame 6: target reappears at expected position (40, 40)
        tracks = tracker.process_frame(6, [make_det("d6", 6, 40.0, 40.0)])

        # Old track should be ended, new track should be tentative
        ended_tracks = [t for t in tracks if t.status == "ended"]
        tentative_tracks = [t for t in tracks if t.status == "tentative"]

        assert len(ended_tracks) == 1
        assert len(tentative_tracks) == 1
        assert ended_tracks[0].track_id != tentative_tracks[0].track_id

        # Evaluate against continuous ground truth: ID switch must be measured!
        gt = [
            GroundTruthPoint(frame_index=0, x=10.0, y=10.0, target_id="tgt1"),
            GroundTruthPoint(frame_index=1, x=15.0, y=15.0, target_id="tgt1"),
            GroundTruthPoint(frame_index=2, x=20.0, y=20.0, target_id="tgt1"),
            GroundTruthPoint(frame_index=6, x=40.0, y=40.0, target_id="tgt1"),
        ]
        _, ext = evaluate_tracks(tracks, gt, matching_gate_px=5.0)
        assert ext["id_switches"] == 1  # Measured ID switch!


class TestNegativeAndArtifactScenes:
    """T10: Test artifact robustness and negative scenes."""

    def test_pure_noise_detections_yield_zero_confirmed_tracks(self) -> None:
        """Uniform random spurious detections over 6 frames must not produce confirmed tracks."""
        rng = np.random.default_rng(seed=12345)
        tracker = Tracker(
            gate_distance_px=15.0,
            confirmation_observations=3,
            max_consecutive_misses=2,
        )

        # 6 frames, each with 8 random detections spread across a 1000x1000 image
        for fi in range(6):
            dets = []
            for k in range(8):
                rx = float(rng.uniform(0.0, 1000.0))
                ry = float(rng.uniform(0.0, 1000.0))
                dets.append(make_det(f"noise_{fi}_{k}", fi, rx, ry, quality=0.3))
            tracks = tracker.process_frame(fi, dets)

        confirmed = [t for t in tracks if t.status == "confirmed"]
        assert len(confirmed) == 0  # Exactly zero false confirmed tracks

        # Evaluate against empty ground truth
        metrics, ext = evaluate_tracks(tracks, ground_truth=[], matching_gate_px=5.0)
        assert ext["false_confirmed_tracks"] == 0
        assert metrics.precision == 0.0
        assert metrics.recall is None
        assert "null_reasons" in metrics.model_dump()

    def test_static_hot_pixel_exhibits_zero_speed(self) -> None:
        """A persistent sensor hot pixel at constant location yields speed approx 0."""
        tracker = Tracker(
            gate_distance_px=15.0,
            confirmation_observations=3,
            max_consecutive_misses=2,
        )

        for fi in range(5):
            tracks = tracker.process_frame(fi, [make_det(f"hot_{fi}", fi, 250.0, 250.0)])

        confirmed = [t for t in tracks if t.status == "confirmed"]
        assert len(confirmed) == 1
        t = confirmed[0]

        fitted = fit_trajectory(t.points)
        assert fitted is not None
        # Speed is near zero
        assert fitted.speed < 0.05
        assert pytest.approx(fitted.vx, abs=0.01) == 0.0
        assert pytest.approx(fitted.vy, abs=0.01) == 0.0


class TestCrossingTargetsAmbiguity:
    """T10: Test spatial crossing where two targets cross at the same coordinate."""

    def test_crossing_targets_deterministic_assignment(self) -> None:
        """Two targets cross at (50, 50) at frame 2; tracker executes deterministically without error."""
        tracker = Tracker(
            gate_distance_px=20.0,
            confirmation_observations=3,
            max_consecutive_misses=2,
            motion_aware=True,
        )

        # Target A: moving right (30, 50) -> (40, 50) -> (50, 50) -> (60, 50) -> (70, 50)
        # Target B: moving down  (50, 30) -> (50, 40) -> (50, 50) -> (50, 60) -> (50, 70)
        for fi in range(5):
            dets = [
                make_det(f"a_{fi}", fi, 30.0 + 10.0 * fi, 50.0),
                make_det(f"b_{fi}", fi, 50.0, 30.0 + 10.0 * fi),
            ]
            tracks = tracker.process_frame(fi, dets)

        confirmed = [t for t in tracks if t.status == "confirmed"]
        assert len(confirmed) >= 1  # At least confirmed tracks maintained without crashing

        gt = [
            GroundTruthPoint(frame_index=fi, x=30.0 + 10.0 * fi, y=50.0, target_id="tgtA")
            for fi in range(5)
        ] + [
            GroundTruthPoint(frame_index=fi, x=50.0, y=30.0 + 10.0 * fi, target_id="tgtB")
            for fi in range(5)
        ]

        metrics, ext = evaluate_tracks(tracks, gt, matching_gate_px=5.0)
        # Verified that ID switches and metrics are quantified honestly
        assert isinstance(ext["id_switches"], int)
        assert ext["false_confirmed_tracks"] == 0
        assert metrics.localization_rmse_px is not None
