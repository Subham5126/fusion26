"""Shared future CLI/API entry point. Never fabricate successful analysis."""
from typing import Sequence

import numpy as np

from app.core.config import PipelineConfig
from app.schemas.result import AnalysisResult, RegistrationResult, Provenance
from app.schemas.sequence import SequenceInput
from orbittrace.detection.adapter import detect_sequence
from orbittrace.tracking.tracker import Tracker
from orbittrace.trajectory.fit import attach_trajectories
from orbittrace.cv_tracking import analyze_telescope_sequence

def analyze(
    sequence: SequenceInput,
    config: PipelineConfig,
    *,
    frame_pixels: Sequence[np.ndarray] | None = None,
    diagnostics: dict | None = None,
) -> AnalysisResult:
    if frame_pixels is None:
        raise NotImplementedError(
            "pipeline_not_implemented: T07 requires image loading/detection T03, "
            "association T04 and trajectory T05. No analysis was performed."
        )

    if not (sequence.source_type == "synthetic" and sequence.profile == "synthetic_static_stars"):
        return analyze_telescope_sequence(frame_pixels, sequence=sequence,
            config=config, diagnostics=diagnostics)
    if diagnostics is not None:
        diagnostics.clear()
        diagnostics.update(sequence=sequence.model_dump(mode="json"),
            suitability={"status": "trusted_synthetic", "inference_allowed": True},
            registration={"status": "not_required", "coordinate_frame": "raw_pixels"})

    if len(frame_pixels) != len(sequence.frames):
        raise ValueError("Number of frame_pixels must match sequence.frames count.")

    for i, (pixels, frame_meta) in enumerate(zip(frame_pixels, sequence.frames)):
        if not isinstance(pixels, np.ndarray) or pixels.ndim != 2:
            raise ValueError(f"Frame {i} is not a 2D numpy array.")
        if pixels.shape != (frame_meta.height_px, frame_meta.width_px):
            raise ValueError(
                f"Frame {i} dimensions {pixels.shape} do not match metadata "
                f"({frame_meta.height_px}, {frame_meta.width_px})."
            )

    detector_config = {
        "threshold_sigma": config.threshold_sigma,
        "max_candidates": config.candidate_cap,
    }

    timestamps_s = [f.timestamp_s for f in sequence.frames]

    detections = detect_sequence(
        frames=frame_pixels,
        sequence_id=sequence.sequence_id,
        profile=sequence.profile,
        timestamps_s=timestamps_s,
        config=detector_config,
        method="optimized"
    )

    tracker = Tracker(config=config)

    frame_timestamps = {
        f.frame_index: f.timestamp_s
        for f in sequence.frames if f.timestamp_s is not None
    }

    tracks = tracker.process_sequence(
        detections=detections,
        frame_indices=[f.frame_index for f in sequence.frames],
        frame_timestamps=frame_timestamps if frame_timestamps else None
    )

    time_basis = "second" if all(f.timestamp_s is not None for f in sequence.frames) else "frame"

    tracks = attach_trajectories(
        tracks=tracks,
        coordinate_frame="raw_pixels",
        time_basis=time_basis,
        prediction_horizon=config.prediction_horizon_frames,
        frame_dimensions=(sequence.frames[0].width_px, sequence.frames[0].height_px),
        frame_timestamps=frame_timestamps if frame_timestamps else None
    )

    return AnalysisResult(
        schema_version="0.1.0",
        job_id="local-cli",
        sequence_id=sequence.sequence_id,
        source_type=sequence.source_type,
        profile=sequence.profile,
        status="succeeded",
        time_basis=time_basis,
        coordinate_frame="raw_pixels",
        registration=RegistrationResult(
            status="not_required",
            warnings=["Camera is static; raw coordinates equal reference coordinates."]
        ),
        detections=detections,
        tracks=tracks,
        metrics=None,
        runtime_ms=None,
        warnings=[],
        provenance=Provenance(
            input_sha256=sequence.input_sha256,
            config_sha256=None,
            code_commit=None,
            dataset_version=sequence.dataset_version
        )
    )
