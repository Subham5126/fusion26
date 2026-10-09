"""Detection-to-Tracking Ablation Evaluation Harness (Task T11).

Compares raw detector candidate proposals (Run A baseline) against
tracking-assisted temporally filtered observations (Run B) over identical
sequences and ground truth.
"""
from __future__ import annotations

import math
import time
from typing import Any, Literal, Sequence

from app.core.config import PipelineConfig
from app.schemas.result import Detection, Track
from orbittrace.evaluation.evaluator import (
    GroundTruthPoint,
    evaluate_detections,
    evaluate_tracks,
)
from orbittrace.tracking.tracker import Tracker


def _compute_f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None:
        return None
    if precision + recall <= 0.0:
        return 0.0
    return float(2.0 * (precision * recall) / (precision + recall))


def run_ablation_comparison(
    detections: Sequence[Detection],
    ground_truth: Sequence[GroundTruthPoint],
    frame_count: int,
    tracker_config: PipelineConfig | None = None,
    matching_gate_px: float = 5.0,
    sequence_id: str = "sequence",
    detector_runtime_ms: float | None = None,
    source_type: Literal["synthetic", "real", "user_upload"] = "synthetic",
) -> dict[str, Any]:
    """Execute a deterministic ablation comparing raw detections vs. tracking-filtered observations.

    Parameters:
        detections: All candidate detections proposed for the sequence.
        ground_truth: Ground truth points for evaluation.
        frame_count: Total number of frames in the sequence (must be >= 1).
        tracker_config: Optional PipelineConfig overriding default tracking thresholds.
        matching_gate_px: Hungarian assignment gate threshold for metric scoring.
        sequence_id: Identifier of the evaluated sequence.
        detector_runtime_ms: Execution wall time of the detector, or None if external/synthetic.
        source_type: Data source type ("synthetic", "real", or "user_upload").

    Returns:
        Structured dictionary containing counts, Run A metrics, Run B metrics,
        ablation deltas, tracking lifecycle counts, and warnings.
    """
    if frame_count < 1:
        raise ValueError(f"frame_count must be at least 1, got {frame_count}")

    # Validate detection sequence invariants
    seen_ids: set[str] = set()
    for d in detections:
        if d.detection_id in seen_ids:
            raise ValueError(f"Duplicate detection_id across sequence: {d.detection_id}")
        seen_ids.add(d.detection_id)

        if not (0 <= d.frame_index < frame_count):
            raise ValueError(
                f"Detection {d.detection_id} has frame_index {d.frame_index} "
                f"outside [0, {frame_count - 1}]"
            )

        if not math.isfinite(d.x_raw_px) or not math.isfinite(d.y_raw_px):
            raise ValueError(
                f"Detection {d.detection_id} contains non-finite coordinates: "
                f"({d.x_raw_px}, {d.y_raw_px})"
            )

        # Validate bounding box invariant
        x0, y0, x1, y1 = d.bbox_raw_px
        if not (x0 <= d.x_raw_px < x1 and y0 <= d.y_raw_px < y1):
            raise ValueError(
                f"Detection {d.detection_id} centroid ({d.x_raw_px}, {d.y_raw_px}) "
                f"outside exclusive bounding box {d.bbox_raw_px}"
            )

    warnings: list[str] = []

    # -------------------------------------------------------------
    # Run A: Detector-only baseline (All raw detections evaluated)
    # -------------------------------------------------------------
    metrics_a = evaluate_detections(
        predictions=detections,
        ground_truth=ground_truth,
        benchmark_id=f"{sequence_id}-runA",
        matching_gate_px=matching_gate_px,
    )
    f1_a = _compute_f1(metrics_a.precision, metrics_a.recall)

    # -------------------------------------------------------------
    # Run B: Tracking-assisted evaluation
    # -------------------------------------------------------------
    tracker = Tracker(config=tracker_config)
    min_hits_to_confirm = tracker.confirmation_observations

    t0 = time.perf_counter()
    tracks = tracker.process_sequence(
        detections=detections,
        frame_indices=list(range(frame_count)),
    )
    t1 = time.perf_counter()
    tracker_runtime_ms = (t1 - t0) * 1000.0

    # Determine tracks that achieved confirmation during their lifecycle:
    # A track is confirmed-in-lifecycle if status is 'confirmed', OR if status
    # is 'ended' but it achieved at least min_hits_to_confirm observed detections.
    confirmed_in_lifecycle: list[Track] = []
    for t in tracks:
        if t.status == "confirmed" or (t.status == "ended" and t.observed_count >= min_hits_to_confirm):
            confirmed_in_lifecycle.append(t)

    # Accepted observations: only observed points from tracks confirmed in their lifecycle
    accepted_observations = []
    for t in confirmed_in_lifecycle:
        for pt in t.points:
            if pt.point_type == "observed":
                accepted_observations.append(pt)

    # Evaluate accepted observations at detection level
    metrics_b = evaluate_detections(
        predictions=accepted_observations,
        ground_truth=ground_truth,
        benchmark_id=f"{sequence_id}-runB",
        matching_gate_px=matching_gate_px,
    )
    f1_b = _compute_f1(metrics_b.precision, metrics_b.recall)

    # Evaluate full tracks at track level (using evaluate_tracks)
    _, ext_tracks = evaluate_tracks(
        tracks=tracks,
        ground_truth=ground_truth,
        benchmark_id=f"{sequence_id}-tracks",
        matching_gate_px=matching_gate_px,
    )

    # Track lifecycle counts
    num_confirmed = sum(1 for t in tracks if t.status == "confirmed")
    num_tentative = sum(1 for t in tracks if t.status == "tentative")
    num_ended = sum(1 for t in tracks if t.status == "ended")
    num_lifecycle_confirmed = len(confirmed_in_lifecycle)

    # Compute deltas (preserve None when either metric is undefined)
    precision_delta = None
    if metrics_a.precision is not None and metrics_b.precision is not None:
        precision_delta = float(metrics_b.precision - metrics_a.precision)

    recall_delta = None
    if metrics_a.recall is not None and metrics_b.recall is not None:
        recall_delta = float(metrics_b.recall - metrics_a.recall)

    f1_delta = None
    if f1_a is not None and f1_b is not None:
        f1_delta = float(f1_b - f1_a)

    rmse_delta = None
    if metrics_a.localization_rmse_px is not None and metrics_b.localization_rmse_px is not None:
        rmse_delta = float(metrics_b.localization_rmse_px - metrics_a.localization_rmse_px)

    fp_reduction = metrics_a.fp - metrics_b.fp
    fp_per_frame = float(metrics_b.fp / frame_count)

    if detector_runtime_ms is None:
        warnings.append("Detector runtime not measured by harness; reported as null.")

    total_runtime_ms = None
    if detector_runtime_ms is not None:
        total_runtime_ms = float(detector_runtime_ms + tracker_runtime_ms)

    return {
        "sequence_id": sequence_id,
        "frame_count": frame_count,
        "source_type": source_type,
        "counts": {
            "raw_detections": len(detections),
            "accepted_detections": len(accepted_observations),
            "ground_truth_points": sum(1 for gt in ground_truth if gt.visible),
            "ground_truth_targets": len({gt.target_id for gt in ground_truth if gt.visible and gt.target_id}),
        },
        "tracks": {
            "total": len(tracks),
            "confirmed": num_confirmed,
            "tentative": num_tentative,
            "ended": num_ended,
            "confirmed_in_lifecycle": num_lifecycle_confirmed,
        },
        "detector_only": {
            "tp": metrics_a.tp,
            "fp": metrics_a.fp,
            "fn": metrics_a.fn,
            "precision": metrics_a.precision,
            "recall": metrics_a.recall,
            "f1": f1_a,
            "localization_rmse_px": metrics_a.localization_rmse_px,
            "null_reasons": metrics_a.null_reasons,
            "runtime_ms": detector_runtime_ms,
        },
        "tracking_assisted": {
            "tp": metrics_b.tp,
            "fp": metrics_b.fp,
            "fn": metrics_b.fn,
            "precision": metrics_b.precision,
            "recall": metrics_b.recall,
            "f1": f1_b,
            "localization_rmse_px": metrics_b.localization_rmse_px,
            "false_positives_per_frame": fp_per_frame,
            "false_confirmed_tracks": ext_tracks["false_confirmed_tracks"],
            "id_switches": ext_tracks["id_switches"],
            "target_coverage": ext_tracks["coverage"],
            "null_reasons": metrics_b.null_reasons,
            "runtime_ms": tracker_runtime_ms,
        },
        "deltas": {
            "precision_delta": precision_delta,
            "recall_delta": recall_delta,
            "f1_delta": f1_delta,
            "fp_reduction": fp_reduction,
            "rmse_delta": rmse_delta,
        },
        "config": {
            "matching_gate_px": float(matching_gate_px),
            "gate_distance_px": float(tracker.gate_distance_px),
            "confirmation_observations": int(tracker.confirmation_observations),
            "max_consecutive_misses": int(tracker.max_consecutive_misses),
        },
        "runtime_ms": {
            "detector_ms": detector_runtime_ms,
            "tracker_ms": tracker_runtime_ms,
            "total_ms": total_runtime_ms,
        },
        "warnings": warnings,
    }
