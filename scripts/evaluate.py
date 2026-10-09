#!/usr/bin/env python3
"""T12: Held-Out Evaluation and Offline Demonstration Runner."""

import argparse
import json
import sys
import time
from pathlib import Path
import random

import numpy as np

# Setup import path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "src"))

from app.core.config import PipelineConfig
from app.schemas.sequence import SequenceInput
from orbittrace.pipeline import analyze
from orbittrace.evaluation.evaluator import (
    GroundTruthPoint,
    evaluate_detections,
    evaluate_tracks,
    create_sequence_splits,
)


def generate_synthetic_scene(
    seq_id: str,
    seed: int,
    frames: int = 5,
    width: int = 64,
    height: int = 48
) -> tuple[SequenceInput, list[np.ndarray], list[GroundTruthPoint]]:
    """Generates synthetic sequence pixels, metadata, and ground truth."""
    np.random.seed(seed)
    random.seed(seed)

    # 20% empty, 80% targets
    is_empty = (random.random() < 0.2)
    # Some targets can be dim or fast
    amplitude = np.random.uniform(30, 100) if not is_empty else 0
    bg_level = np.random.uniform(15, 25)
    noise_sigma = np.random.uniform(1.0, 3.0)

    start_x = np.random.uniform(10, width - 10)
    start_y = np.random.uniform(10, height - 10)
    vx = np.random.uniform(-4, 4)
    vy = np.random.uniform(-4, 4)

    # 10% chance of missing/occluded observation in the middle
    occlude_idx = random.choice([None, 2]) if random.random() < 0.1 else None

    yy, xx = np.mgrid[:height, :width]

    sequence_data = {
        "schema_version": "0.1.0",
        "sequence_id": seq_id,
        "source_type": "synthetic",
        "profile": "synthetic_static_stars",
        "frames": [
            {
                "frame_index": i,
                "image_ref": f"{seq_id}_frame_{i}",
                "width_px": width,
                "height_px": height,
                "timestamp_s": float(i)
            }
            for i in range(frames)
        ]
    }
    sequence = SequenceInput.model_validate(sequence_data)

    image_list = []
    truth_points = []

    target_id = f"tgt_{seq_id}"

    for i in range(frames):
        image = np.full(xx.shape, bg_level, dtype=np.float64)
        image += np.random.normal(0, noise_sigma, xx.shape)

        visible = not is_empty and (i != occlude_idx)

        if visible:
            cx = start_x + vx * i
            cy = start_y + vy * i
            # Gaussian blob
            image += amplitude * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 1.5 ** 2))

            # Record truth
            truth_points.append(
                GroundTruthPoint(
                    frame_index=i,
                    x=float(cx),
                    y=float(cy),
                    target_id=target_id,
                    visible=True
                )
            )

        pixels = np.rint(np.clip(image, 0, 255)).astype(np.uint8)
        image_list.append(pixels)

    return sequence, image_list, truth_points


def run_evaluation(num_sequences: int = 50, split_seed: int = 26):
    print(f"Generating {num_sequences} synthetic sequences (seed={split_seed})...")
    sequence_ids = [f"syn-{i:03d}" for i in range(num_sequences)]
    splits = create_sequence_splits(sequence_ids, dev_ratio=0.4, val_ratio=0.2, test_ratio=0.4, seed=split_seed)

    test_seqs = splits["test"]
    print(f"Held-out test partition contains {len(test_seqs)} sequences.")

    config = PipelineConfig(threshold_sigma=3.0, confirmation_observations=3)

    all_detections = []
    all_tracks = []
    all_truth = []

    total_frames = 0
    empty_scenes = 0
    t0 = time.perf_counter()

    for seq_id in test_seqs:
        # Deterministic generation seed derived from sequence ID string
        gen_seed = hash(seq_id) % 1000000
        seq_input, pixels, truth = generate_synthetic_scene(seq_id, seed=gen_seed)

        if len(truth) == 0:
            empty_scenes += 1

        result = analyze(seq_input, config, frame_pixels=pixels)

        # Override frame indices for global matching (Wait, match is per frame, but frame indices must be unique per sequence?
        # Actually evaluator matches per frame_index. If we merge sequences, frame_index will collide.
        # We must shift frame indices or evaluate per sequence and aggregate.)
        # The evaluator doesn't know about sequences, so we shift frame indices.

        frame_offset = total_frames

        for d in result.detections:
            d.frame_index += frame_offset
            all_detections.append(d)

        for t in result.tracks:
            for pt in t.points:
                pt.frame_index += frame_offset
            all_tracks.append(t)

        for gt in truth:
            gt.frame_index += frame_offset
            all_truth.append(gt)

        total_frames += len(pixels)

    t1 = time.perf_counter()
    runtime_ms = (t1 - t0) * 1000.0

    print("\n--- Evaluating Detections ---")
    det_metrics = evaluate_detections(
        predictions=all_detections,
        ground_truth=all_truth,
        benchmark_id="t12-test-detections",
        split="test",
        matching_gate_px=5.0
    )

    print("\n--- Evaluating Tracks ---")
    track_metrics, extended = evaluate_tracks(
        tracks=all_tracks,
        ground_truth=all_truth,
        benchmark_id="t12-test-tracks",
        split="test",
        matching_gate_px=5.0
    )

    report = {
        "benchmark": "T12 Held-Out Synthetic",
        "provenance": "Local seeded synthetic generation",
        "random_seed": split_seed,
        "config": {
            "threshold_sigma": config.threshold_sigma,
            "confirmation_observations": config.confirmation_observations
        },
        "sequences": len(test_seqs),
        "total_frames": total_frames,
        "empty_scenes": empty_scenes,
        "detections": {
            "tp": det_metrics.tp,
            "fp": det_metrics.fp,
            "fn": det_metrics.fn,
            "precision": det_metrics.precision,
            "recall": det_metrics.recall,
            "rmse_px": det_metrics.localization_rmse_px,
            "null_reasons": det_metrics.null_reasons
        },
        "tracking": {
            "tp": track_metrics.tp,
            "fp": track_metrics.fp,
            "fn": track_metrics.fn,
            "precision": track_metrics.precision,
            "recall": track_metrics.recall,
            "rmse_px": track_metrics.localization_rmse_px,
            "id_switches": extended.get("id_switches"),
            "target_coverage": extended.get("coverage"),
            "false_confirmed_tracks": extended.get("false_confirmed_tracks"),
            "null_reasons": track_metrics.null_reasons
        },
        "runtime": {
            "total_ms": runtime_ms,
            "ms_per_frame": runtime_ms / total_frames if total_frames else None
        },
        "limitations": [
            "Generated coordinates evaluate image-plane pixel localization, not physical orbit errors.",
            "Targets are simple Gaussians without real atmospheric noise or complex point spread functions.",
            "Registration accuracy cannot be validated here because synthetic_static_stars assumes alignment."
        ]
    }

    print("\n================ T12 EVALUATION REPORT ================\n")
    print(json.dumps(report, indent=2))
    print("\n=======================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="T12 Evaluation Harness")
    parser.add_argument("--sequences", type=int, default=50, help="Total sequences to split")
    parser.add_argument("--seed", type=int, default=26, help="Split and generation seed")
    args = parser.parse_args()

    run_evaluation(num_sequences=args.sequences, split_seed=args.seed)
