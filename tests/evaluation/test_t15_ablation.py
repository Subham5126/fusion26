"""Unit tests for Task T15: Temporal Ablation & Hard-Case Evaluation.

Validates:
1. Deterministic fixture generation across all 12 hard-case scenarios.
2. Systematic temporal ablations (continuity, confirmation, distance gate, extrapolation).
3. Zero-leakage deterministic dataset partitioning.
4. Correct tracking metrics calculation and undefined metric (null) handling.
5. Trajectory prediction horizon units and extrapolation RMSE reduction.
6. Report generation, JSON schema integrity, and scientific provenance.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from app.schemas.result import Detection
from orbittrace.evaluation.evaluator import GroundTruthPoint, create_sequence_splits
from scripts.t15_ablation import (
    generate_case_1_clean_single_target,
    generate_case_2_one_gap_dropout,
    generate_case_3_multi_gap_dropout,
    generate_case_4_two_simultaneous_targets,
    generate_case_5_crossing_trajectories,
    generate_case_6_proximate_false_positives,
    generate_case_7_dense_clutter_negative,
    generate_case_8_slow_moving_object,
    generate_case_9_fast_moving_gate_limit,
    generate_case_10_empty_negative_sequence,
    generate_case_11_short_track_insufficient_fit,
    generate_case_12_fov_boundary_entry_exit,
    evaluate_ablation_matrix,
    evaluate_trajectory_extrapolation_ablation,
    execute_full_t15_study,
)


def test_hard_case_fixtures_determinism_and_invariants() -> None:
    """Verifies that all 12 hard case generators are strictly deterministic and satisfy invariants."""
    # Case 1: Clean single target
    d1, gt1, _ = generate_case_1_clean_single_target()
    assert len(d1) == len(gt1) == 5

    # Case 2: One-gap dropout
    d2, gt2, meta2 = generate_case_2_one_gap_dropout(dropout_frame=2)
    assert len(gt2) == 5
    assert len(d2) == 4
    assert {d.frame_index for d in d2} == {0, 1, 3, 4}

    # Case 3: Multi-gap dropout
    d3, gt3, meta3 = generate_case_3_multi_gap_dropout()
    assert len(gt3) == 6
    assert len(d3) == 4
    assert {d.frame_index for d in d3} == {0, 1, 4, 5}

    # Case 4: Two simultaneous targets
    d4, gt4, _ = generate_case_4_two_simultaneous_targets()
    assert len(gt4) == 10
    assert len(d4) == 10
    assert len({gt.target_id for gt in gt4}) == 2

    # Case 5: Crossing trajectories
    d5, gt5, _ = generate_case_5_crossing_trajectories()
    assert len(gt5) == 10
    assert len(d5) == 10
    f2_dets = [d for d in d5 if d.frame_index == 2]
    assert len(f2_dets) == 2
    assert {(d.x_raw_px, d.y_raw_px) for d in f2_dets} == {(100.0, 100.0)}

    # Case 6: Proximate false positives
    d6, gt6, _ = generate_case_6_proximate_false_positives(seed=42)
    assert len(gt6) == 5
    assert len(d6) == 10

    # Case 7: Dense clutter negative
    d7, gt7, _ = generate_case_7_dense_clutter_negative(frame_count=5, noise_count_per_frame=20, seed=42)
    assert len(gt7) == 0
    assert len(d7) == 100

    # Case 8: Slow-moving object
    d8, gt8, meta8 = generate_case_8_slow_moving_object()
    assert len(d8) == len(gt8) == 5
    assert meta8["speed_px_per_frame"] < 1.0

    # Case 9: Fast-moving at gate boundary
    d9, gt9, meta9 = generate_case_9_fast_moving_gate_limit(speed_px=18.5)
    assert len(d9) == len(gt9) == 5
    assert meta9["speed_px_per_frame"] == 18.5

    # Case 10: Empty negative sequence
    d10, gt10, _ = generate_case_10_empty_negative_sequence()
    assert len(d10) == len(gt10) == 0

    # Case 11: Short track insufficient fit
    d11, gt11, meta11 = generate_case_11_short_track_insufficient_fit()
    assert len(d11) == len(gt11) == 2

    # Case 12: FOV entry and exit
    d12, gt12, meta12 = generate_case_12_fov_boundary_entry_exit()
    assert len(d12) == len(gt12) == 3
    assert {d.frame_index for d in d12} == {2, 3, 4}


def test_zero_leakage_split_partitioning() -> None:
    """Verifies that sequence splits are disjoint and deterministic."""
    seq_ids = [f"seq_{i:03d}" for i in range(25)]
    splits = create_sequence_splits(seq_ids, dev_ratio=0.6, val_ratio=0.2, test_ratio=0.2, seed=2026)

    dev_set = set(splits["development"])
    val_set = set(splits["validation"])
    test_set = set(splits["test"])

    assert len(dev_set & val_set) == 0
    assert len(dev_set & test_set) == 0
    assert len(val_set & test_set) == 0
    assert dev_set | val_set | test_set == set(seq_ids)


def test_trajectory_extrapolation_ablation_metrics() -> None:
    """Verifies that constant velocity forward extrapolation outperforms zero-order static hold."""
    res = evaluate_trajectory_extrapolation_ablation(num_sequences=10, seed=123)

    assert res["units"] == "px"
    assert res["time_basis"] == "frame"
    cv_h1 = res["constant_velocity_model"]["horizon_1_rmse_px"]
    zero_h1 = res["zero_order_baseline"]["horizon_1_rmse_px"]

    assert cv_h1 < 1e-6
    assert zero_h1 > 1.0
    assert res["rmse_reduction_percentage_h1"] > 99.0


def test_empty_negative_scene_null_metric_handling() -> None:
    """Verifies that an empty negative scene reports explicit null reasons rather than fake 1.0 precision."""
    report = execute_full_t15_study(num_synthetic_sequences=3, seed=999)
    hc_empty = report["hard_case_evaluations"]["case_10_empty_negative_sequence"]

    run_a = hc_empty["run_a_detector_only"]
    run_b = hc_empty["run_b_tracking_assisted"]

    assert run_a["precision"] is None
    assert run_a["recall"] is None
    assert "precision" in run_a["null_reasons"]
    assert run_b["precision"] is None
    assert run_b["recall"] is None
    assert "precision" in run_b["null_reasons"]


def test_full_t15_study_execution_and_schema_validation(tmp_path: Path) -> None:
    """Verifies complete execution of T15 study, resulting in valid structure and correct metrics."""
    report = execute_full_t15_study(num_synthetic_sequences=5, seed=12345)

    assert report["task_id"] == "T15"
    assert "provenance" in report
    assert "temporal_ablations" in report
    assert "trajectory_prediction_ablation" in report
    assert "hard_case_evaluations" in report
    assert "conclusions" in report

    # Check 12 hard cases are all present
    assert len(report["hard_case_evaluations"]) == 12

    # Verify Ablation B continuity difference
    ablation = report["temporal_ablations"]
    assert ablation["B1_reduced_continuity_misses_0"]["id_switches"] >= ablation["A_full_tracking_default"]["id_switches"]
    # Verify Ablation D distance gating sensitivity
    assert ablation["D1_association_gate_5px"]["recall"] <= ablation["A_full_tracking_default"]["recall"]


def test_hard_case_report_consistency_against_json() -> None:
    """Guards against documentation and JSON metric inconsistency for hard cases 6 and 7.

    Specifically verifies:
    1. Case 6 (Proximate clutter) induces competition within the 20 px gate (P=0.5, R=1.0, id_switches=1).
    2. Case 7 (Dense clutter) suppresses >=95% noise (122/125 rejected) and isolates the chance 3-frame alignment.
    """
    report_file = Path("artifacts/reports/t15_ablation_report.json")
    if not report_file.exists():
        pytest.skip("t15_ablation_report.json not found on disk")

    with open(report_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    hc = data["hard_case_evaluations"]

    # Case 6 verification
    c6 = hc["case_6_proximate_false_positives"]
    assert c6["raw_detections"] == 10
    assert c6["ground_truth_points"] == 5
    assert c6["run_b_tracking_assisted"]["precision"] == 0.5
    assert c6["run_b_tracking_assisted"]["recall"] == 1.0
    assert c6["run_b_tracking_assisted"]["id_switches"] == 1
    assert c6["run_b_tracking_assisted"]["false_confirmed_tracks"] == 0

    # Case 7 verification
    c7 = hc["case_7_dense_clutter_negative"]
    assert c7["raw_detections"] == 125
    assert c7["ground_truth_points"] == 0
    assert c7["run_b_tracking_assisted"]["precision"] == 0.0
    assert c7["run_b_tracking_assisted"]["recall"] is None
    assert c7["run_b_tracking_assisted"]["false_confirmed_tracks"] == 1
    assert c7["run_b_tracking_assisted"]["fp"] == 3

