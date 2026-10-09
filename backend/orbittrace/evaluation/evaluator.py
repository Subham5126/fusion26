"""Evaluator and benchmark split generation for OrbitTrace (Task T06).

Complies with Contract 0.1.0, docs/CONTRACTS.md, and docs/EVALUATION.md:
- Evaluator-only matching: ground-truth labels remain strictly isolated from inference.
- Bounded 1-to-1 gated Euclidean distance matching via scipy.optimize.linear_sum_assignment.
- Truthful TP, FP, FN counts, precision, recall, and localization RMSE.
- Safe handling of zero denominators: returns null with human-readable null_reasons.
- Tracking-level metrics: identity coverage, ID switches, false confirmed tracks.
- Sequence-based split partitioning: strict zero-leakage disjoint sets.
"""
from dataclasses import dataclass, field
import hashlib
import math
from typing import Any, Literal, Sequence

import numpy as np
from scipy.optimize import linear_sum_assignment

from app.schemas.result import BenchmarkMetrics, Track, TrackPoint


@dataclass
class GroundTruthPoint:
    """Evaluator-only ground truth observation."""

    frame_index: int
    x: float
    y: float
    target_id: str | None = None
    visible: bool = True


@dataclass
class MatchResult:
    """Detailed frame-level or sequence-level match outcome."""

    tp: int
    fp: int
    fn: int
    precision: float | None
    recall: float | None
    localization_rmse_px: float | None
    null_reasons: dict[str, str] = field(default_factory=dict)
    matched_pairs: list[tuple[Any, GroundTruthPoint, float]] = field(default_factory=list)


def match_points_frame(
    predicted_points: Sequence[Any],
    ground_truth_points: Sequence[GroundTruthPoint],
    matching_gate_px: float = 5.0,
) -> tuple[list[tuple[int, int, float]], list[int], list[int]]:
    """Perform 1-to-1 minimum-cost gated matching for a single frame.

    predicted_points can be TrackPoint instances, Detection instances,
    or tuples (x, y).

    Returns:
        (matched_pairs, unmatched_pred_indices, unmatched_gt_indices)
        where matched_pairs is list of (pred_idx, gt_idx, distance).
    """
    m = len(predicted_points)
    n = len(ground_truth_points)

    if m == 0 and n == 0:
        return [], [], []
    if m == 0:
        return [], [], list(range(n))
    if n == 0:
        return [], list(range(m)), []

    # Extract coordinates
    def _coords(p: Any) -> tuple[float, float]:
        if hasattr(p, "x_reference_px") and p.x_reference_px is not None:
            return float(p.x_reference_px), float(p.y_reference_px)
        if hasattr(p, "x_raw_px") and p.x_raw_px is not None:
            return float(p.x_raw_px), float(p.y_raw_px)
        if hasattr(p, "x") and hasattr(p, "y"):
            return float(p.x), float(p.y)
        if isinstance(p, (tuple, list)) and len(p) >= 2:
            return float(p[0]), float(p[1])
        raise ValueError(f"Cannot extract (x, y) coordinates from {type(p)}")

    preds_arr = np.array([_coords(p) for p in predicted_points], dtype=np.float64)
    gts_arr = np.array([(float(gt.x), float(gt.y)) for gt in ground_truth_points], dtype=np.float64)

    # Compute Euclidean distance matrix: shape (m, n)
    diff = preds_arr[:, np.newaxis, :] - gts_arr[np.newaxis, :, :]
    dist_matrix = np.hypot(diff[:, :, 0], diff[:, :, 1])

    # Build cost matrix with penalty for distances exceeding gate
    cost_matrix = dist_matrix.copy()
    penalty = matching_gate_px + 1e6
    cost_matrix[dist_matrix > matching_gate_px] = penalty

    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    matched_pairs: list[tuple[int, int, float]] = []
    matched_preds: set[int] = set()
    matched_gts: set[int] = set()

    for r, c in zip(row_ind, col_ind):
        d = float(dist_matrix[r, c])
        if d <= matching_gate_px:
            matched_pairs.append((int(r), int(c), d))
            matched_preds.add(int(r))
            matched_gts.add(int(c))

    unmatched_preds = [i for i in range(m) if i not in matched_preds]
    unmatched_gts = [j for j in range(n) if j not in matched_gts]

    return matched_pairs, unmatched_preds, unmatched_gts


def evaluate_detections(
    predictions: Sequence[Any],
    ground_truth: Sequence[GroundTruthPoint],
    benchmark_id: str = "benchmark-eval",
    split: Literal["development", "validation", "test"] = "development",
    matching_gate_px: float = 5.0,
) -> BenchmarkMetrics:
    """Evaluate predicted observed detections against ground-truth points.

    Excludes any non-observed predictions (interpolated/extrapolated points).
    Aggregates TP, FP, FN across all frames.
    Computes precision, recall, and localization RMSE.
    Handles zero denominators with explicit null_reasons.
    """
    # Filter only observed points if TrackPoints are passed
    valid_preds = []
    for p in predictions:
        if hasattr(p, "point_type") and p.point_type != "observed":
            continue
        valid_preds.append(p)

    # Group by frame_index
    preds_by_frame: dict[int, list[Any]] = {}
    for p in valid_preds:
        fi = getattr(p, "frame_index", 0)
        preds_by_frame.setdefault(fi, []).append(p)

    gt_by_frame: dict[int, list[GroundTruthPoint]] = {}
    for gt in ground_truth:
        if gt.visible:
            gt_by_frame.setdefault(gt.frame_index, []).append(gt)

    all_frames = sorted(set(preds_by_frame.keys()) | set(gt_by_frame.keys()))

    total_tp = 0
    total_fp = 0
    total_fn = 0
    squared_errors: list[float] = []

    for fi in all_frames:
        frame_preds = preds_by_frame.get(fi, [])
        frame_gts = gt_by_frame.get(fi, [])

        matched, unmatched_p, unmatched_g = match_points_frame(
            frame_preds, frame_gts, matching_gate_px=matching_gate_px
        )

        total_tp += len(matched)
        total_fp += len(unmatched_p)
        total_fn += len(unmatched_g)

        for _, _, dist in matched:
            squared_errors.append(dist ** 2)

    null_reasons: dict[str, str] = {}

    # Precision: TP / (TP + FP)
    if total_tp + total_fp == 0:
        precision = None
        null_reasons["precision"] = "No predicted detections (TP + FP == 0)"
    else:
        precision = float(total_tp / (total_tp + total_fp))

    # Recall: TP / (TP + FN)
    if total_tp + total_fn == 0:
        recall = None
        null_reasons["recall"] = "No ground truth targets (TP + FN == 0)"
    else:
        recall = float(total_tp / (total_tp + total_fn))

    # Localization RMSE: sqrt(mean(squared_errors))
    if total_tp == 0:
        localization_rmse_px = None
        null_reasons["localization_rmse_px"] = "No matched detections (TP == 0)"
    else:
        rmse = float(math.sqrt(float(np.mean(squared_errors))))
        localization_rmse_px = 0.0 if rmse < 1e-12 else rmse

    return BenchmarkMetrics(
        benchmark_id=benchmark_id,
        split=split,
        matching_gate_px=float(matching_gate_px),
        tp=total_tp,
        fp=total_fp,
        fn=total_fn,
        precision=precision,
        recall=recall,
        localization_rmse_px=localization_rmse_px,
        null_reasons=null_reasons,
    )


def evaluate_tracks(
    tracks: Sequence[Track],
    ground_truth: Sequence[GroundTruthPoint],
    benchmark_id: str = "benchmark-eval",
    split: Literal["development", "validation", "test"] = "development",
    matching_gate_px: float = 5.0,
) -> tuple[BenchmarkMetrics, dict[str, Any]]:
    """Evaluate tracks against ground truth, returning BenchmarkMetrics and tracking metrics.

    Extended metrics include:
    - id_switches: number of ID switches for identified ground-truth targets
    - coverage: fraction of eligible visible ground truth points recovered
    - false_confirmed_tracks: count of confirmed tracks without true matches
    """
    # 1. Collect all observed points with track_id attached
    observed_points_with_track = []
    for track in tracks:
        for pt in track.points:
            if pt.point_type == "observed":
                observed_points_with_track.append((track.track_id, pt))

    # Group by frame_index
    preds_by_frame: dict[int, list[tuple[str, TrackPoint]]] = {}
    for tid, pt in observed_points_with_track:
        preds_by_frame.setdefault(pt.frame_index, []).append((tid, pt))

    gt_by_frame: dict[int, list[GroundTruthPoint]] = {}
    for gt in ground_truth:
        if gt.visible:
            gt_by_frame.setdefault(gt.frame_index, []).append(gt)

    all_frames = sorted(set(preds_by_frame.keys()) | set(gt_by_frame.keys()))

    total_tp = 0
    total_fp = 0
    total_fn = 0
    squared_errors: list[float] = []

    # Map target_id -> list of (frame_index, matched_track_id)
    target_match_history: dict[str, list[tuple[int, str]]] = {}
    matched_track_ids: set[str] = set()

    for fi in all_frames:
        frame_preds = preds_by_frame.get(fi, [])
        frame_gts = gt_by_frame.get(fi, [])

        pred_pts = [item[1] for item in frame_preds]
        matched, unmatched_p, unmatched_g = match_points_frame(
            pred_pts, frame_gts, matching_gate_px=matching_gate_px
        )

        total_tp += len(matched)
        total_fp += len(unmatched_p)
        total_fn += len(unmatched_g)

        for p_idx, g_idx, dist in matched:
            squared_errors.append(dist ** 2)
            tid = frame_preds[p_idx][0]
            matched_track_ids.add(tid)
            gt_target = frame_gts[g_idx].target_id
            if gt_target:
                target_match_history.setdefault(gt_target, []).append((fi, tid))

    null_reasons: dict[str, str] = {}
    if total_tp + total_fp == 0:
        precision = None
        null_reasons["precision"] = "No predicted detections (TP + FP == 0)"
    else:
        precision = float(total_tp / (total_tp + total_fp))

    if total_tp + total_fn == 0:
        recall = None
        null_reasons["recall"] = "No ground truth targets (TP + FN == 0)"
    else:
        recall = float(total_tp / (total_tp + total_fn))

    if total_tp == 0:
        localization_rmse_px = None
        null_reasons["localization_rmse_px"] = "No matched detections (TP == 0)"
    else:
        rmse = float(math.sqrt(float(np.mean(squared_errors))))
        localization_rmse_px = 0.0 if rmse < 1e-12 else rmse

    metrics = BenchmarkMetrics(
        benchmark_id=benchmark_id,
        split=split,
        matching_gate_px=float(matching_gate_px),
        tp=total_tp,
        fp=total_fp,
        fn=total_fn,
        precision=precision,
        recall=recall,
        localization_rmse_px=localization_rmse_px,
        null_reasons=null_reasons,
    )

    # Count ID switches: whenever consecutive matched observations for a true target change track_id
    id_switches = 0
    for target_id, history in target_match_history.items():
        for i in range(1, len(history)):
            if history[i][1] != history[i - 1][1]:
                id_switches += 1

    # False confirmed tracks: confirmed tracks with no matched ground truth points
    confirmed_tracks = [t for t in tracks if t.status == "confirmed"]
    false_confirmed_tracks = sum(
        1 for t in confirmed_tracks if t.track_id not in matched_track_ids
    )

    total_gt_points = sum(1 for gt in ground_truth if gt.visible)
    coverage = float(total_tp / total_gt_points) if total_gt_points > 0 else None

    extended_report = {
        "id_switches": id_switches,
        "coverage": coverage,
        "false_confirmed_tracks": false_confirmed_tracks,
        "total_tracks": len(tracks),
        "confirmed_tracks": len(confirmed_tracks),
    }

    return metrics, extended_report


def create_sequence_splits(
    sequence_ids: Sequence[str],
    dev_ratio: float = 0.6,
    val_ratio: float = 0.2,
    test_ratio: float = 0.2,
    seed: int = 26,
) -> dict[str, list[str]]:
    """Partition sequence IDs into strictly disjoint development, validation, and test sets.

    Ensures zero leakage: sequences belong to exactly one split.
    Uses deterministic hashing on (seed, sequence_id).
    """
    if not math.isclose(dev_ratio + val_ratio + test_ratio, 1.0, rel_tol=1e-5):
        raise ValueError("Split ratios must sum to 1.0")

    # Deterministic sort and shuffle based on seed
    sorted_ids = sorted(set(sequence_ids))

    def _hash_score(sid: str) -> float:
        h = hashlib.sha256(f"{seed}:{sid}".encode("utf-8")).hexdigest()
        return int(h[:8], 16) / 0xFFFFFFFF

    scored = sorted(sorted_ids, key=_hash_score)
    n = len(scored)

    n_dev = int(round(n * dev_ratio))
    n_val = int(round(n * val_ratio))

    # For datasets with at least 3 sequences, ensure no split is empty
    if n >= 3:
        if n_val == 0:
            n_val = 1
        if n - n_dev - n_val <= 0:
            n_dev = max(1, n - n_val - 1)

    dev_set = scored[:n_dev]
    val_set = scored[n_dev : n_dev + n_val]
    test_set = scored[n_dev + n_val :]

    # Assert zero overlap
    assert not (set(dev_set) & set(val_set)), "Leakage error: dev and val overlap"
    assert not (set(dev_set) & set(test_set)), "Leakage error: dev and test overlap"
    assert not (set(val_set) & set(test_set)), "Leakage error: val and test overlap"

    return {
        "development": dev_set,
        "validation": val_set,
        "test": test_set,
    }
