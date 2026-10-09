"""Separate point-localization benchmark helpers, never imported by inference."""

import math
from typing import Iterable

import numpy as np
from scipy.optimize import linear_sum_assignment

from .runner import SequenceDetections


def match_points(predicted: Iterable, truth: Iterable, radius_px: float) -> dict:
    """Maximum-cardinality one-to-one gated matching, then minimum total distance.

    Dummy columns explicitly leave predictions unmatched. Gate is inclusive in raw
    pixels. Normalized distance/(max_matches+1) makes any extra valid match win
    before distance optimization, and forbidden edges are never forced.
    This is detection evaluation, not cross-frame association or official ESA scoring.
    """
    if type(radius_px) not in (int, float) or not math.isfinite(radius_px) or radius_px <= 0:
        raise ValueError("Matching radius must be finite and positive")
    pred = np.asarray(list(predicted), dtype=np.float64).reshape(-1, 2)
    target = np.asarray(list(truth), dtype=np.float64).reshape(-1, 2)
    if not np.isfinite(pred).all() or not np.isfinite(target).all():
        raise ValueError("Evaluation coordinates must be finite")
    p, t = len(pred), len(target)
    matches = []
    if p and t:
        distances = np.linalg.norm(pred[:, None, :] - target[None, :, :], axis=2)
        cost = np.ones((p, t + p), dtype=np.float64)
        cost[:, :t] = np.where(distances <= radius_px,
                               distances / radius_px / (min(p, t) + 1), 3.0)
        rows, cols = linear_sum_assignment(cost)
        matches = [{"predicted_index": int(row), "truth_index": int(col),
                    "distance_px": float(distances[row, col])}
                   for row, col in zip(rows, cols) if col < t and distances[row, col] <= radius_px]
    return {"tp": len(matches), "fp": p - len(matches), "fn": t - len(matches), "matches": matches}


def summarize_frames(frame_results: list[dict], processing_ms: list[float]) -> dict:
    """Aggregate counts first; undefined ratios/localization stay null with reasons."""
    tp = sum(r["tp"] for r in frame_results)
    fp = sum(r["fp"] for r in frame_results)
    fn = sum(r["fn"] for r in frame_results)
    distances = [m["distance_px"] for r in frame_results for m in r["matches"]]
    count = len(frame_results)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    reasons = {}
    for name, value in (("precision", precision), ("recall", recall), ("f1", f1)):
        if value is None:
            reasons[name] = "zero denominator"
    if not distances:
        reasons["localization"] = "no matched predictions"
    return {"frame_count": count, "tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1,
            "localization_mean_px": float(np.mean(distances)) if distances else None,
            "localization_rmse_px": float(np.sqrt(np.mean(np.square(distances)))) if distances else None,
            "false_positives_per_frame": fp / count if count else None,
            "processing_ms_total": float(sum(processing_ms)),
            "processing_ms_mean_per_frame": float(np.mean(processing_ms)) if processing_ms else None,
            "processing_ms_p95_per_frame": float(np.percentile(processing_ms, 95)) if processing_ms else None,
            "null_reasons": reasons}


def evaluate_sequences(predictions: list[SequenceDetections], labels, radius_px: float) -> dict:
    """Explicitly join inference output and labels after detection has finished."""
    results, times = [], []
    seen = set()
    for sequence in predictions:
        key = (sequence.split, sequence.sequence_id)
        if key in seen or len(sequence.frames) != 5:
            raise ValueError("Evaluation requires unique complete five-frame sequences")
        seen.add(key)
        annotations = labels.for_sequence(sequence.sequence_id)
        for frame, truth in zip(sequence.frames, annotations):
            if frame.frame_index != truth.frame_index:
                raise ValueError("Annotation frame does not match prediction frame")
            matched = match_points([(d.x_raw_px, d.y_raw_px) for d in frame.detections], truth.object_coords, radius_px)
            results.append({"sequence_id": sequence.sequence_id, "split": sequence.split,
                            "frame_index": frame.frame_index, **matched})
            times.append(frame.processing_ms)
    negative_indexes = [i for i, value in enumerate(results) if value["tp"] + value["fn"] == 0]
    return {"matching_radius_px": radius_px, "metrics": summarize_frames(results, times), "per_frame": results,
            "empty_annotation_frames": summarize_frames([results[i] for i in negative_indexes],
                                                         [times[i] for i in negative_indexes])}


def freeze_membership(train_ids, test_ids, *, seed: int = 26, development_count: int = 24,
                      heldout_count: int = 128) -> dict:
    """Select whole sequences uniformly without consulting annotations or image content.

    Train/test IDs are namespaced by split. Membership becomes a written manifest
    before threshold experiments; all tuning is development-only. This samples the
    official test partition and does not claim the full competition score.
    """
    train_ids, test_ids = tuple(train_ids), tuple(test_ids)
    if len(set(train_ids)) != len(train_ids) or len(set(test_ids)) != len(test_ids):
        raise ValueError("Duplicate split IDs")
    if not 0 < development_count <= len(train_ids) or not 0 < heldout_count <= len(test_ids):
        raise ValueError("Requested split sample exceeds available sequences")
    rng = np.random.default_rng(seed)
    dev = sorted(map(str, rng.choice(train_ids, development_count, replace=False)), key=int)
    held = sorted(map(str, rng.choice(test_ids, heldout_count, replace=False)), key=int)
    return {"seed": seed, "development": {"split": "train", "sequence_ids": dev},
            "held_out": {"split": "test", "sequence_ids": held},
            "selection": "uniform sequence sampling before tuning; no annotation stratification"}
