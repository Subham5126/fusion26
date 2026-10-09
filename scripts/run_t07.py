#!/usr/bin/env python3
"""Thin CLI entry point for T07: Orchestrating the end-to-end pipeline."""

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

# Setup import path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import load_pipeline_config
from app.schemas.sequence import SequenceInput
from orbittrace.pipeline import analyze


def load_grayscale_pixels(image_path: Path) -> np.ndarray:
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    # cv2.imread with IMREAD_GRAYSCALE returns 2D numpy array
    pixels = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if pixels is None:
        raise ValueError(f"Failed to decode image: {image_path}")
    return pixels


def main():
    parser = argparse.ArgumentParser(description="T07 CLI pipeline runner")
    parser.add_argument("manifest", type=Path, help="Path to SequenceInput JSON manifest")
    parser.add_argument("image_dir", type=Path, help="Directory containing image files matching image_ref")
    parser.add_argument("--config", type=Path, help="Optional PipelineConfig YAML path")
    args = parser.parse_args()

    try:
        # Load manifest
        manifest_data = json.loads(args.manifest.read_text(encoding="utf-8"))
        sequence = SequenceInput.model_validate(manifest_data)

        # Load config
        config = load_pipeline_config(args.config)

        # Load actual pixels
        frame_pixels = []
        for frame_meta in sequence.frames:
            # Assumes image files are named exactly like their image_ref + .png or .jpg
            image_path = args.image_dir / f"{frame_meta.image_ref}.png"
            if not image_path.exists():
                image_path = args.image_dir / f"{frame_meta.image_ref}.jpg"

            pixels = load_grayscale_pixels(image_path)
            frame_pixels.append(pixels)

        # Run pipeline
        result = analyze(sequence, config, frame_pixels=frame_pixels)

        # Dump to stdout
        sys.stdout.write(result.model_dump_json(indent=2, exclude_none=True))
        sys.stdout.write("\n")

    except Exception as e:
        sys.stderr.write(f"Pipeline failed: {type(e).__name__}: {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
