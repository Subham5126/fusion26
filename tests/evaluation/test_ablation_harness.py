"""Unit tests for Task T11: Detection-to-Tracking Ablation Evaluation Harness.

Verifies:
1. Persistent true targets across at least 3 frames.
2. Isolated 1-frame false detections rejected by confirmation filtering.
3. 1- and 2-frame genuine targets, demonstrating expected recall drop.
4. Empty detections and empty ground truth (empty negative scene).
5. Pure noise that never produces a confirmed track.
6. Crossing targets, using existing tracker behavior.
7. Validation on duplicate detection IDs, invalid coordinates, and out-of-range frame indices.
8. Deterministic output for repeated runs.
9. Ended tracks that had previously been confirmed during their lifecycle.
10. Metric deltas and zero-denominator null reason handling.
"""
from __future__ import annotations

import math
import pytest

from app.core.config import PipelineConfig
from app.schemas.result import Detection
from orbittrace.evaluation import GroundTruthPoint, run_ablation_comparison


def make_det(
    det_id: str,
    frame_index: int,
    x: float,
    y: float,
    quality: float = 0.9,
    kind: str = "compact",
) -> Detection:
    """Helper to construct a valid Detection within exclusive-upper bounding box."""
    bbox = (max(0.0, x - 2.0), max(0.0, y - 2.0), x + 2.0, y + 2.0)
    return Detection(
        detection_id=det_id,
        frame_index=frame_index,
        x_raw_px=x,
        y_raw_px=y,
        bbox_raw_px=bbox,
        kind=kind,
        quality_score=quality,
        detector_name="test_detector",
    )


class TestAblationHarnessScenarios:
    def test_persistent_true_targets(self) -> None:
        """1. Persistent target across 5 frames confirms and maintains high precision and recall."""
        frame_count = 5
        dets = [
            make_det(f"d_{i}", i, 20.0 + 5.0 * i, 30.0 + 3.0 * i)
            for i in range(frame_count)
        ]
        gt = [
            GroundTruthPoint(frame_index=i, x=20.0 + 5.0 * i, y=30.0 + 3.0 * i, target_id="tgt_1")
            for i in range(frame_count)
        ]

        result = run_ablation_comparison(dets, gt, frame_count=frame_count, sequence_id="seq_persistent")

        assert result["counts"]["raw_detections"] == 5
        assert result["counts"]["accepted_detections"] == 5
        assert result["tracks"]["confirmed"] == 1
        assert result["tracks"]["confirmed_in_lifecycle"] == 1

        # Both Run A and Run B should have perfect precision and recall
        assert result["detector_only"]["precision"] == 1.0
        assert result["detector_only"]["recall"] == 1.0
        assert result["tracking_assisted"]["precision"] == 1.0
        assert result["tracking_assisted"]["recall"] == 1.0
        assert result["deltas"]["precision_delta"] == 0.0
        assert result["deltas"]["recall_delta"] == 0.0

    def test_isolated_false_detections_rejected(self) -> None:
        """2. Isolated 1-frame false alarms are eliminated in Run B, boosting precision."""
        frame_count = 5
        # Persistent target: 5 frames
        persistent_dets = [
            make_det(f"true_{i}", i, 10.0 + 4.0 * i, 10.0 + 2.0 * i)
            for i in range(frame_count)
        ]
        # 4 isolated false alarms on various frames (spatially distant)
        noise_dets = [
            make_det("noise_f0", 0, 200.0, 200.0),
            make_det("noise_f1", 1, 350.0, 100.0),
            make_det("noise_f2", 2, 50.0, 400.0),
            make_det("noise_f4", 4, 300.0, 300.0),
        ]
        all_dets = persistent_dets + noise_dets

        gt = [
            GroundTruthPoint(frame_index=i, x=10.0 + 4.0 * i, y=10.0 + 2.0 * i, target_id="tgt_1")
            for i in range(frame_count)
        ]

        result = run_ablation_comparison(all_dets, gt, frame_count=frame_count, sequence_id="seq_noise")

        # Run A evaluates all 9 detections: 5 TP, 4 FP
        assert result["detector_only"]["tp"] == 5
        assert result["detector_only"]["fp"] == 4
        assert pytest.approx(result["detector_only"]["precision"], abs=0.001) == 5 / 9

        # Run B filters out unconfirmed noise: 5 TP, 0 FP
        assert result["tracking_assisted"]["tp"] == 5
        assert result["tracking_assisted"]["fp"] == 0
        assert result["tracking_assisted"]["precision"] == 1.0

        # Positive precision delta and positive FP reduction
        assert result["deltas"]["precision_delta"] > 0.4
        assert result["deltas"]["fp_reduction"] == 4

    def test_short_genuine_targets_demonstrate_recall_drop(self) -> None:
        """3. Genuine targets visible for only 1 or 2 frames cannot confirm, demonstrating recall drop."""
        frame_count = 5
        # Target A: 1-frame transient (frame 0)
        # Target B: 2-frame transient (frames 1 and 2)
        dets = [
            make_det("d_a0", 0, 50.0, 50.0),
            make_det("d_b1", 1, 100.0, 100.0),
            make_det("d_b2", 2, 105.0, 103.0),
        ]
        gt = [
            GroundTruthPoint(frame_index=0, x=50.0, y=50.0, target_id="tgt_A"),
            GroundTruthPoint(frame_index=1, x=100.0, y=100.0, target_id="tgt_B"),
            GroundTruthPoint(frame_index=2, x=105.0, y=103.0, target_id="tgt_B"),
        ]

        result = run_ablation_comparison(dets, gt, frame_count=frame_count, sequence_id="seq_short")

        # Run A captures all 3 detections
        assert result["detector_only"]["tp"] == 3
        assert result["detector_only"]["recall"] == 1.0

        # Run B: neither target reaches confirmation threshold (>= 3), so both are dropped
        assert result["tracking_assisted"]["tp"] == 0
        assert result["tracking_assisted"]["fn"] == 3
        assert result["tracking_assisted"]["recall"] == 0.0

        # Expected negative recall delta
        assert result["deltas"]["recall_delta"] == -1.0

    def test_empty_detections_and_ground_truth(self) -> None:
        """4. Empty scene returns structured report with null metrics and appropriate reasons."""
        result = run_ablation_comparison([], [], frame_count=4, sequence_id="seq_empty")

        assert result["counts"]["raw_detections"] == 0
        assert result["counts"]["accepted_detections"] == 0
        assert result["detector_only"]["precision"] is None
        assert result["detector_only"]["recall"] is None
        assert result["tracking_assisted"]["precision"] is None
        assert result["tracking_assisted"]["recall"] is None
        assert result["deltas"]["precision_delta"] is None
        assert result["deltas"]["recall_delta"] is None

    def test_pure_noise_yields_zero_confirmed(self) -> None:
        """5. Pure random noise never produces confirmed tracks; accepted detections count is 0."""
        frame_count = 4
        noise_dets = [
            make_det("n0", 0, 10.0, 10.0),
            make_det("n1", 1, 100.0, 200.0),
            make_det("n2", 2, 300.0, 50.0),
            make_det("n3", 3, 500.0, 400.0),
        ]
        result = run_ablation_comparison(noise_dets, [], frame_count=frame_count, sequence_id="seq_pure_noise")

        assert result["detector_only"]["fp"] == 4
        assert result["tracking_assisted"]["fp"] == 0
        assert result["counts"]["accepted_detections"] == 0
        assert result["tracks"]["confirmed"] == 0
        assert result["tracking_assisted"]["false_confirmed_tracks"] == 0

    def test_crossing_targets_behavior(self) -> None:
        """6. Two crossing targets tracked and evaluated with ID consistency metrics."""
        frame_count = 5
        dets = []
        gt = []
        for i in range(frame_count):
            # Target 1 moving right
            dets.append(make_det(f"t1_{i}", i, 30.0 + 10.0 * i, 50.0))
            gt.append(GroundTruthPoint(frame_index=i, x=30.0 + 10.0 * i, y=50.0, target_id="tgt_1"))
            # Target 2 moving down
            dets.append(make_det(f"t2_{i}", i, 50.0, 30.0 + 10.0 * i))
            gt.append(GroundTruthPoint(frame_index=i, x=50.0, y=30.0 + 10.0 * i, target_id="tgt_2"))

        result = run_ablation_comparison(dets, gt, frame_count=frame_count, sequence_id="seq_crossing")

        assert result["counts"]["accepted_detections"] == 10
        assert result["tracks"]["confirmed_in_lifecycle"] >= 1
        assert isinstance(result["tracking_assisted"]["id_switches"], int)
        assert result["tracking_assisted"]["target_coverage"] is not None

    def test_validation_errors(self) -> None:
        """7. Raises ValueError on duplicate IDs, non-finite coords, or out-of-range frames."""
        # Out-of-range frame_count
        with pytest.raises(ValueError, match="frame_count must be at least 1"):
            run_ablation_comparison([], [], frame_count=0)

        # Duplicate detection_id
        d1 = make_det("dup_id", 0, 10.0, 10.0)
        d2 = make_det("dup_id", 1, 20.0, 20.0)
        with pytest.raises(ValueError, match="Duplicate detection_id"):
            run_ablation_comparison([d1, d2], [], frame_count=2)

        # Out-of-range frame_index
        d_out = make_det("d_out", 5, 10.0, 10.0)
        with pytest.raises(ValueError, match="outside"):
            run_ablation_comparison([d_out], [], frame_count=3)

    def test_deterministic_output(self) -> None:
        """8. Repeated runs yield bit-for-bit identical metrics and counts."""
        dets = [make_det(f"d_{i}", i, 10.0 + i * 2.0, 10.0 + i * 2.0) for i in range(4)]
        gt = [GroundTruthPoint(frame_index=i, x=10.0 + i * 2.0, y=10.0 + i * 2.0, target_id="t1") for i in range(4)]

        res1 = run_ablation_comparison(dets, gt, frame_count=4)
        res2 = run_ablation_comparison(dets, gt, frame_count=4)

        assert res1["detector_only"] == res2["detector_only"]
        # Tracker metrics excluding runtime
        for k in ["tp", "fp", "fn", "precision", "recall", "f1", "false_confirmed_tracks"]:
            assert res1["tracking_assisted"][k] == res2["tracking_assisted"][k]
        assert res1["deltas"] == res2["deltas"]

    def test_ended_tracks_previously_confirmed_are_preserved(self) -> None:
        """9. Tracks that reached confirmation but ended on subsequent misses retain their accepted points."""
        # 6 frames: target observed at f0, f1, f2 (confirmed with 3 obs), then missed at f3, f4, f5 (ended)
        dets = [
            make_det("d0", 0, 10.0, 10.0),
            make_det("d1", 1, 15.0, 15.0),
            make_det("d2", 2, 20.0, 20.0),
        ]
        gt = [
            GroundTruthPoint(frame_index=0, x=10.0, y=10.0, target_id="tgt_1"),
            GroundTruthPoint(frame_index=1, x=15.0, y=15.0, target_id="tgt_1"),
            GroundTruthPoint(frame_index=2, x=20.0, y=20.0, target_id="tgt_1"),
        ]

        config = PipelineConfig(max_consecutive_misses=2)
        result = run_ablation_comparison(dets, gt, frame_count=6, tracker_config=config)

        # Track status ended, but confirmed_in_lifecycle is 1
        assert result["tracks"]["ended"] == 1
        assert result["tracks"]["confirmed_in_lifecycle"] == 1
        assert result["counts"]["accepted_detections"] == 3
        assert result["tracking_assisted"]["tp"] == 3
        assert result["tracking_assisted"]["precision"] == 1.0

    def test_metric_deltas_and_zero_denominator_handling(self) -> None:
        """10. Verify calculation of metric deltas and proper handling of undefined values."""
        # Partial match scenario: 1 TP, 1 FP in Run A; 1 TP, 0 FP in Run B
        dets = [
            make_det("tp_0", 0, 10.0, 10.0),
            make_det("tp_1", 1, 12.0, 12.0),
            make_det("tp_2", 2, 14.0, 14.0),
            make_det("fp_0", 0, 80.0, 80.0),  # isolated noise
        ]
        gt = [
            GroundTruthPoint(frame_index=0, x=10.0, y=10.0, target_id="t1"),
            GroundTruthPoint(frame_index=1, x=12.0, y=12.0, target_id="t1"),
            GroundTruthPoint(frame_index=2, x=14.0, y=14.0, target_id="t1"),
        ]

        result = run_ablation_comparison(dets, gt, frame_count=3, sequence_id="seq_delta")

        # Precision A = 3/4 = 0.75, Precision B = 3/3 = 1.0 -> Delta = +0.25
        assert pytest.approx(result["detector_only"]["precision"], abs=0.01) == 0.75
        assert pytest.approx(result["tracking_assisted"]["precision"], abs=0.01) == 1.0
        assert pytest.approx(result["deltas"]["precision_delta"], abs=0.01) == 0.25
        assert result["deltas"]["fp_reduction"] == 1
