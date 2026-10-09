"""Tests for T07 CLI pipeline orchestration."""
import numpy as np
import pytest

from app.core.config import PipelineConfig
from app.schemas.sequence import SequenceInput
from orbittrace.pipeline import analyze


def sample_sequence_metadata(profile="synthetic_static_stars", frames=5, width=64, height=48, has_time=False):
    return SequenceInput.model_validate({
        "schema_version": "0.1.0",
        "sequence_id": "test_seq",
        "source_type": "synthetic",
        "profile": profile,
        "frames": [
            {
                "frame_index": i,
                "image_ref": f"img_{i}",
                "width_px": width,
                "height_px": height,
                "timestamp_s": float(i) if has_time else None
            }
            for i in range(frames)
        ]
    })


def generate_empty_frames(frames=5, width=64, height=48):
    return [np.zeros((height, width), dtype=np.uint8) for _ in range(frames)]


def generate_target_frames(frames=5, width=64, height=48):
    yy, xx = np.mgrid[:height, :width]
    images = []
    for i in range(frames):
        image = np.full(xx.shape, 20.0, dtype=np.float64)
        # moving target
        image += 80 * np.exp(-((xx - (10 + i * 5)) ** 2 + (yy - 20) ** 2) / (2 * 1.5 ** 2))
        pixels = np.rint(np.clip(image, 0, 255)).astype(np.uint8)
        images.append(pixels)
    return images


def test_rejects_without_pixels():
    seq = sample_sequence_metadata()
    config = PipelineConfig()
    with pytest.raises(NotImplementedError, match="No analysis was performed"):
        analyze(seq, config)


def test_rejects_unregistered_moving_profile():
    seq = sample_sequence_metadata(profile="spotgeo")
    config = PipelineConfig()
    pixels = generate_empty_frames()
    with pytest.raises(RuntimeError, match="Registration \\(T13\\) not implemented"):
        analyze(seq, config, frame_pixels=pixels)


def test_validates_dimensions_and_counts():
    seq = sample_sequence_metadata()
    config = PipelineConfig()
    # Bad count
    with pytest.raises(ValueError, match="Number of frame_pixels must match"):
        analyze(seq, config, frame_pixels=generate_empty_frames(frames=4))

    # Bad dimensions
    bad_pixels = generate_empty_frames(frames=5, width=100, height=100)
    with pytest.raises(ValueError, match="dimensions .* do not match metadata"):
        analyze(seq, config, frame_pixels=bad_pixels)


def test_e2e_synthetic_static_success():
    seq = sample_sequence_metadata(has_time=True)
    config = PipelineConfig(threshold_sigma=3.0, confirmation_observations=3)
    pixels = generate_target_frames()

    result = analyze(seq, config, frame_pixels=pixels)
    assert result.status == "succeeded"
    assert result.schema_version == "0.1.0"
    assert result.coordinate_frame == "raw_pixels"
    assert result.registration.status == "not_required"

    confirmed = [t for t in result.tracks if t.status == "confirmed"]
    assert len(confirmed) == 1
    track = confirmed[0]
    assert track.observed_count == 5
    assert track.trajectory is not None
    assert track.trajectory.speed_unit == "px/s"


def test_e2e_empty_sequence():
    seq = sample_sequence_metadata()
    config = PipelineConfig()
    pixels = generate_empty_frames()

    result = analyze(seq, config, frame_pixels=pixels)
    assert result.status == "succeeded"
    assert len(result.detections) == 0
    assert len(result.tracks) == 0


import subprocess
import json
import cv2
import tempfile
from pathlib import Path
import sys

def test_cli_subprocess_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        seq = sample_sequence_metadata(has_time=True)
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(seq.model_dump_json(), encoding="utf-8")

        frames = generate_target_frames()
        for i, f in enumerate(frames):
            img_path = tmp_path / f"img_{i}.png"
            cv2.imwrite(str(img_path), f)

        script_path = Path(__file__).resolve().parents[2] / "scripts" / "run_t07.py"

        result = subprocess.run(
            [sys.executable, str(script_path), str(manifest_path), str(tmp_path)],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert result.stderr == ""

        out_data = json.loads(result.stdout)
        assert out_data["status"] == "succeeded"
        assert out_data["job_id"] == "local-cli"


def test_cli_subprocess_failure_missing_image():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        seq = sample_sequence_metadata(has_time=True)
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(seq.model_dump_json(), encoding="utf-8")

        # We don't save any images, so it should fail
        script_path = Path(__file__).resolve().parents[2] / "scripts" / "run_t07.py"

        result = subprocess.run(
            [sys.executable, str(script_path), str(manifest_path), str(tmp_path)],
            capture_output=True,
            text=True
        )

        assert result.returncode != 0
        assert "FileNotFoundError" in result.stderr
