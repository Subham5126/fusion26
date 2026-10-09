"""Comprehensive unit tests for Task T06: Evaluator and Benchmark Splits.

Covers:
1. Perfect match (100% precision, 100% recall, 0.0 RMSE)
2. Partial match (expected TP, FP, FN counts)
3. False positives only (no ground truth -> recall is None, precision is 0.0)
4. False negatives only (no predictions -> precision is None, recall is 0.0)
5. Empty negative scene (0 predictions, 0 ground truth -> precision, recall, RMSE are None with null_reasons)
6. Distance gating: points exceeding matching_gate_px remain unmatched
7. One-to-one assignment: no duplicate counting when multiple candidates compete
8. Tracking metrics: ID switches, identity coverage, and false confirmed tracks
9. Benchmark split generation: strictly disjoint sequence splits with zero leakage
10. Strict Pydantic contract validation of BenchmarkMetrics
"""
import math
import pytest

from app.schemas.result import BenchmarkMetrics, Detection, Track, TrackPoint
from orbittrace.evaluation.evaluator import (
    GroundTruthPoint,
    create_sequence_splits,
    evaluate_detections,
    evaluate_tracks,
    match_points_frame,
)


def make_detection(
    detection_id: str,
    frame_index: int,
    x: float,
    y: float,
) -> Detection:
    bbox = (max(0.0, x - 2.0), max(0.0, y - 2.0), x + 2.0, y + 2.0)
    return Detection(
        detection_id=detection_id,
        frame_index=frame_index,
        x_raw_px=x,
        y_raw_px=y,
        bbox_raw_px=bbox,
        kind="compact",
        quality_score=0.8,
        detector_name="test_det",
        x_reference_px=x,
        y_reference_px=y,
    )


# 1. Perfect match
def test_perfect_match():
    preds = [
        make_detection("d0", 0, 10.0, 10.0),
        make_detection("d1", 1, 15.0, 15.0),
        make_detection("d2", 2, 20.0, 20.0),
    ]
    gt = [
        GroundTruthPoint(frame_index=0, x=10.0, y=10.0, target_id="tgt1"),
        GroundTruthPoint(frame_index=1, x=15.0, y=15.0, target_id="tgt1"),
        GroundTruthPoint(frame_index=2, x=20.0, y=20.0, target_id="tgt1"),
    ]

    metrics = evaluate_detections(preds, gt, matching_gate_px=5.0)

    assert metrics.tp == 3
    assert metrics.fp == 0
    assert metrics.fn == 0
    assert metrics.precision == pytest.approx(1.0)
    assert metrics.recall == pytest.approx(1.0)
    assert metrics.localization_rmse_px == pytest.approx(0.0)
    assert metrics.null_reasons == {}


# 2. Partial match
def test_partial_match():
    # Frame 0: 1 match (dx=3, dy=4 -> dist=5.0 <= gate 5.0), 1 FP, 1 FN
    preds = [
        make_detection("p_match", 0, 13.0, 14.0),
        make_detection("p_extra", 0, 50.0, 50.0),
    ]
    gt = [
        GroundTruthPoint(frame_index=0, x=10.0, y=10.0, target_id="tgt1"),
        GroundTruthPoint(frame_index=0, x=90.0, y=90.0, target_id="tgt2"),
    ]

    metrics = evaluate_detections(preds, gt, matching_gate_px=5.0)

    assert metrics.tp == 1
    assert metrics.fp == 1
    assert metrics.fn == 1
    assert metrics.precision == pytest.approx(0.5)  # 1 / (1 + 1)
    assert metrics.recall == pytest.approx(0.5)     # 1 / (1 + 1)
    assert metrics.localization_rmse_px == pytest.approx(5.0)


# 3. False positives only
def test_false_positives_only_no_ground_truth():
    preds = [
        make_detection("p0", 0, 10.0, 10.0),
        make_detection("p1", 1, 20.0, 20.0),
    ]
    gt = []

    metrics = evaluate_detections(preds, gt, matching_gate_px=5.0)

    assert metrics.tp == 0
    assert metrics.fp == 2
    assert metrics.fn == 0
    assert metrics.precision == pytest.approx(0.0)
    assert metrics.recall is None
    assert metrics.localization_rmse_px is None
    assert "recall" in metrics.null_reasons
    assert "localization_rmse_px" in metrics.null_reasons


# 4. False negatives only
def test_false_negatives_only_no_predictions():
    preds = []
    gt = [
        GroundTruthPoint(frame_index=0, x=10.0, y=10.0, target_id="tgt1"),
        GroundTruthPoint(frame_index=1, x=20.0, y=20.0, target_id="tgt1"),
    ]

    metrics = evaluate_detections(preds, gt, matching_gate_px=5.0)

    assert metrics.tp == 0
    assert metrics.fp == 0
    assert metrics.fn == 2
    assert metrics.precision is None
    assert metrics.recall == pytest.approx(0.0)
    assert metrics.localization_rmse_px is None
    assert "precision" in metrics.null_reasons


# 5. Empty negative scene
def test_empty_negative_scene():
    metrics = evaluate_detections([], [], matching_gate_px=5.0)

    assert metrics.tp == 0
    assert metrics.fp == 0
    assert metrics.fn == 0
    assert metrics.precision is None
    assert metrics.recall is None
    assert metrics.localization_rmse_px is None
    assert "precision" in metrics.null_reasons
    assert "recall" in metrics.null_reasons
    assert "localization_rmse_px" in metrics.null_reasons


# 6. Distance gating
def test_distance_gating_forbidden_matches():
    # Distance is 5.5 px > gate 5.0 px
    preds = [make_detection("p0", 0, 15.5, 10.0)]
    gt = [GroundTruthPoint(frame_index=0, x=10.0, y=10.0, target_id="tgt1")]

    metrics = evaluate_detections(preds, gt, matching_gate_px=5.0)

    assert metrics.tp == 0
    assert metrics.fp == 1
    assert metrics.fn == 1
    assert metrics.precision == pytest.approx(0.0)
    assert metrics.recall == pytest.approx(0.0)


# 7. One-to-one assignment prevents duplicate matches
def test_one_to_one_assignment_no_duplicates():
    # Two predictions at (10, 11) and (10, 12) competing for one GT at (10, 10)
    preds = [
        make_detection("p_closer", 0, 10.0, 11.0),   # dist 1.0
        make_detection("p_farther", 0, 10.0, 12.0),  # dist 2.0
    ]
    gt = [GroundTruthPoint(frame_index=0, x=10.0, y=10.0, target_id="tgt1")]

    matched, unmatched_p, unmatched_g = match_points_frame(preds, gt, matching_gate_px=5.0)

    # Exactly 1 match to the closer prediction
    assert len(matched) == 1
    assert matched[0][0] == 0  # p_closer
    assert matched[0][1] == 0  # gt
    assert matched[0][2] == pytest.approx(1.0)
    assert unmatched_p == [1]  # p_farther is unmatched FP
    assert unmatched_g == []


# 8. Tracking metrics: ID switches, coverage, and false confirmed tracks
def test_tracking_evaluation_metrics():
    # Ground truth: target 'tgt1' visible at frames 0, 1, 2
    gt = [
        GroundTruthPoint(frame_index=0, x=10.0, y=10.0, target_id="tgt1"),
        GroundTruthPoint(frame_index=1, x=14.0, y=13.0, target_id="tgt1"),
        GroundTruthPoint(frame_index=2, x=18.0, y=16.0, target_id="tgt1"),
    ]

    # Track 1 matches frame 0; Track 2 matches frames 1 and 2 (1 ID switch!)
    pt0 = TrackPoint(frame_index=0, x_reference_px=10.0, y_reference_px=10.0, point_type="observed", detection_id="d0")
    pt1 = TrackPoint(frame_index=1, x_reference_px=14.0, y_reference_px=13.0, point_type="observed", detection_id="d1")
    pt2 = TrackPoint(frame_index=2, x_reference_px=18.0, y_reference_px=16.0, point_type="observed", detection_id="d2")

    track1 = Track(
        track_id="trk-1", status="tentative", candidate_label="orbital-object candidate; identity unverified",
        points=[pt0], observed_count=1, quality_score=0.8, warnings=[], trajectory=None
    )
    track2 = Track(
        track_id="trk-2", status="tentative", candidate_label="orbital-object candidate; identity unverified",
        points=[pt1, pt2], observed_count=2, quality_score=0.8, warnings=[], trajectory=None
    )

    # Track 3 is a false confirmed track far away with no GT match
    pt_fc0 = TrackPoint(frame_index=0, x_reference_px=100.0, y_reference_px=100.0, point_type="observed", detection_id="dfc0")
    pt_fc1 = TrackPoint(frame_index=1, x_reference_px=104.0, y_reference_px=104.0, point_type="observed", detection_id="dfc1")
    pt_fc2 = TrackPoint(frame_index=2, x_reference_px=108.0, y_reference_px=108.0, point_type="observed", detection_id="dfc2")
    track3 = Track(
        track_id="trk-3-false-confirmed", status="confirmed", candidate_label="orbital-object candidate; identity unverified",
        points=[pt_fc0, pt_fc1, pt_fc2], observed_count=3, quality_score=0.8, warnings=[], trajectory=None
    )

    metrics, ext = evaluate_tracks([track1, track2, track3], gt, matching_gate_px=5.0)

    assert metrics.tp == 3
    assert metrics.fp == 3  # track3 points are FPs
    assert metrics.fn == 0
    assert metrics.recall == pytest.approx(1.0)
    assert ext["id_switches"] == 1  # trk-1 at frame 0 -> trk-2 at frame 1
    assert ext["coverage"] == pytest.approx(1.0)
    assert ext["false_confirmed_tracks"] == 1  # track3 is confirmed without GT correspondence


# 9. Sequence splits: disjoint partition, no leakage
def test_create_sequence_splits_zero_leakage():
    seq_ids = [f"sequence_{i:03d}" for i in range(20)]
    splits = create_sequence_splits(seq_ids, dev_ratio=0.6, val_ratio=0.2, test_ratio=0.2, seed=42)

    dev = set(splits["development"])
    val = set(splits["validation"])
    test = set(splits["test"])

    # All sequences accounted for
    assert dev | val | test == set(seq_ids)

    # Zero leakage between splits
    assert len(dev & val) == 0
    assert len(dev & test) == 0
    assert len(val & test) == 0

    # Determinism with same seed
    splits_repeat = create_sequence_splits(seq_ids, dev_ratio=0.6, val_ratio=0.2, test_ratio=0.2, seed=42)
    assert splits == splits_repeat


# 10. Strict Pydantic contract validation
def test_benchmark_metrics_pydantic_validation():
    metrics = evaluate_detections([], [], split="validation")
    assert isinstance(metrics, BenchmarkMetrics)
    assert metrics.split == "validation"
    # Serializes and deserializes without mutation
    json_str = metrics.model_dump_json()
    assert BenchmarkMetrics.model_validate_json(json_str) == metrics
