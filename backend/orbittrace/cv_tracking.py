"""CV-TRACK-01: image-only algorithm integration, independent of jobs and HTTP.

Success is the unchanged AnalysisResult 0.1.0. Expected scientific/input failures
raise TelescopeAnalysisError carrying the existing ApiError/JobState contracts.
Supplemental diagnostics reuse the CV suitability/registration dictionaries.
"""
from collections.abc import Mapping, Sequence
from dataclasses import asdict
import hashlib
import json
from time import perf_counter
from typing import Literal
import warnings

import numpy as np
from app.core.config import PipelineConfig
from app.schemas.job import ApiError, JobState
from app.schemas.result import AnalysisResult, Provenance, RegistrationResult, Track
from app.schemas.sequence import SequenceInput
from astrotrace.detection.baseline import BaselineConfig
from astrotrace.detection.precision import precision_config
from astrotrace.preprocessing.candidates import normalize_grayscale
from astrotrace.preprocessing.registration import (
    RegistrationConfig, add_reference_coordinates, register_sequence,
)
from astrotrace.preprocessing.suitability import validate_sequence_suitability
from orbittrace.detection.adapter import detect_sequence
from orbittrace.tracking.tracker import Tracker
from orbittrace.trajectory.fit import attach_trajectories


class TelescopeAnalysisError(ValueError):
    """Expected failure; never return rejected input as a successful empty result."""
    def __init__(self, error: ApiError):
        super().__init__(error.message)
        self.error = error
        self.code, self.details = error.code, error.details

    def as_job_state(self, job_id: str = "local-cv-track") -> JobState:
        return JobState(job_id=job_id, status="failed", progress_stage=self.code,
                        warnings=[], error=self.error, progress_fraction=None)


def analyze_telescope_sequence(
    frames: Sequence[np.ndarray],
    *,
    sequence: SequenceInput,
    frame_indices: Sequence[int] | None = None,
    timestamps: Sequence[float | None] | None = None,
    config: PipelineConfig | None = None,
    method: Literal["optimized", "baseline"] = "optimized",
    detector_config: Mapping[str, object] | None = None,
    registration_config: RegistrationConfig | Mapping[str, object] | None = None,
    diagnostics: dict | None = None,
) -> AnalysisResult:
    """Analyze exactly five ordered native grayscale arrays without file/label IO.

    Explicit indexes must match schema 0.1.0's contiguous zero-based manifest.
    Explicit timestamps must equal manifest timestamps; unknown remains None.
    Telescope suitability and registration are required even for synthetic
    examples. There is no low-feature or failed-registration bypass here.
    Numeric CV options are validated by the existing detector/config classes.
    If supplied, diagnostics is cleared and filled for this call, including on
    failure. It is supplemental data, not extra AnalysisResult schema fields.
    """
    started = perf_counter()
    diagnostic = diagnostics if diagnostics is not None else {}
    diagnostic.clear()
    stage_started = perf_counter()
    timings = {}
    diagnostic["timings_ms"] = timings

    def reject(code, message, details=None):
        error = ApiError(code=code, message=message, details=details)
        diagnostic.update(status="failed", error=error.model_dump(mode="json"),
                          runtime_ms=(perf_counter()-started)*1000)
        raise TelescopeAnalysisError(error)

    if not isinstance(sequence, SequenceInput):
        reject("invalid_input", "sequence must be a validated SequenceInput 0.1.0")
    # Revalidate caller-held mutable models; no model_copy validation bypass.
    try:
        sequence = SequenceInput.model_validate(sequence.model_dump())
        if not isinstance(frames, Sequence) or isinstance(frames, (str, bytes)) or len(frames) != 5 or len(sequence.frames) != 5:
            raise ValueError("Exactly five ordered arrays and five manifest frames are required")
        indexes = list(range(5)) if frame_indices is None else list(frame_indices)
        if any(type(i) is not int for i in indexes) or indexes != [f.frame_index for f in sequence.frames]:
            raise ValueError("Explicit frame indexes must equal the ordered zero-based manifest indexes 0..4")
        expected_times = [f.timestamp_s for f in sequence.frames]
        if timestamps is not None:
            times = list(timestamps)
            if len(times) != 5 or any(t is not None and type(t) not in (int, float) for t in times) or times != expected_times:
                raise ValueError("Explicit timestamps must equal the manifest; do not guess measurement times")
        for pixels, meta in zip(frames, sequence.frames):
            normalize_grayscale(pixels)
            if pixels.shape != (meta.height_px, meta.width_px):
                raise ValueError("Native image dimensions disagree with the manifest")
    except (ValueError, TypeError) as exc:
        reject("invalid_input", str(exc))
    timings["input_validation"] = (perf_counter()-stage_started)*1000
    diagnostic["sequence"] = sequence.model_dump(mode="json")
    try:
        cfg = PipelineConfig(profile=sequence.profile) if config is None else PipelineConfig.model_validate({**config.model_dump(), "profile": sequence.profile})
        if config is not None and "profile" in config.model_fields_set and config.profile != sequence.profile:
            raise ValueError("Config profile disagrees with sequence profile")
        if method not in ("optimized", "baseline"):
            raise ValueError("Only the verified optimized and baseline OpenCV methods are available")
        defaults = precision_config() if method == "optimized" else BaselineConfig()
        if detector_config is not None and not isinstance(detector_config, Mapping):
            raise ValueError("detector_config must be a declared numeric mapping")
        overrides = dict(detector_config or {})
        for field, key in (("threshold_sigma", "threshold_sigma"), ("candidate_cap", "max_candidates")):
            if config is not None and field in config.model_fields_set:
                if key in overrides and overrides[key] != getattr(config, field):
                    raise ValueError("Conflicting shared and detector numeric overrides")
                overrides[key] = getattr(config, field)
        declared = type(defaults).from_mapping({**defaults.to_dict(), **overrides})
        reg_cfg = RegistrationConfig.from_mapping(registration_config)
    except (ValueError, TypeError, AttributeError) as exc:
        reject("invalid_configuration", str(exc))
    effective = {"shared": cfg.model_dump(mode="json"), "method": method,
                 "detector": declared.to_dict(), "registration": asdict(reg_cfg)}
    diagnostic["config"] = effective
    stage_started = perf_counter()
    diagnostic["suitability"] = validate_sequence_suitability(frames)
    timings["suitability"] = (perf_counter()-stage_started)*1000
    assessment = diagnostic["suitability"]
    if not assessment["inference_allowed"]:
        reject("unsupported_observation" if assessment["status"] == "unsupported" else "uncertain_observation",
               "Observation requires review: " + "; ".join(assessment["explanations"]),
               {"reason_codes": ", ".join(assessment["reason_codes"])})
    stage_started = perf_counter()
    with warnings.catch_warnings(record=True) as emitted:
        warnings.simplefilter("always")
        raw = detect_sequence(frames, sequence_id=sequence.sequence_id, profile=sequence.profile,
                              timestamps_s=expected_times, config=declared.to_dict(), method=method)
    timings["detection"] = (perf_counter()-stage_started)*1000
    diagnostic["detections"] = [d.model_dump(mode="json") for d in raw]
    stage_started = perf_counter()
    registration = register_sequence(frames, config=reg_cfg)
    timings["registration"] = (perf_counter()-stage_started)*1000
    diagnostic["registration"] = registration.to_dict()
    if registration.status == "failed":
        reject("registration_failed", "Registration failed; tracking blocked for the whole sequence.",
               {"failed_frames": ", ".join(str(f.frame_index) for f in registration.frames if f.status == "failed")})
    stage_started = perf_counter()
    detections = add_reference_coordinates(raw, registration)
    frame_times = {f.frame_index: f.timestamp_s for f in sequence.frames if f.timestamp_s is not None}
    tracks = Tracker(config=cfg).process_sequence(detections, frame_indices=indexes, frame_timestamps=frame_times or None)
    width, height = sequence.frames[0].width_px, sequence.frames[0].height_px
    tracks = [Track.model_validate({**t.model_dump(), "points": [{**p.model_dump(),
        "out_of_field": not (0 <= p.x_reference_px < width and 0 <= p.y_reference_px < height)} for p in t.points]}) for t in tracks]
    timings["coordinate_bridge_and_tracking"] = (perf_counter()-stage_started)*1000
    stage_started = perf_counter()
    basis = "second" if frame_times else "frame"
    tracks = attach_trajectories(tracks, coordinate_frame=registration.coordinate_frame, time_basis=basis,
        prediction_horizon=cfg.prediction_horizon_frames, frame_dimensions=(width, height), frame_timestamps=frame_times or None)
    timings["trajectory"] = (perf_counter()-stage_started)*1000
    notices = [str(w.message) for w in emitted]
    if frame_times:
        notices.append("Future prediction timestamps use the fitter cadence estimate when unavailable; they are not measured timestamps.")
        times = list(frame_times.values())
        if len(set(round(b-a, 9) for a, b in zip(times, times[1:]))) > 1:
            notices.append("Association predictor uses frame intervals; irregular timestamp cadence is not calibrated.")
    notices.append("Orbital-object candidates; identity unverified. Motion is image-plane only. Quality is heuristic.")
    # Hash native pixels and declared geometry/timing; preserve an API's supplied
    # encoded-byte provenance when present. No disk/git lookup during inference.
    input_hash = sequence.input_sha256
    if input_hash is None:
        digest = hashlib.sha256(sequence.model_dump_json().encode())
        for pixels in frames:
            digest.update(str(pixels.dtype).encode())
            digest.update(pixels.tobytes(order="C"))
        input_hash = digest.hexdigest()
    result = AnalysisResult(schema_version="0.1.0", job_id="local-cv-track", sequence_id=sequence.sequence_id,
        source_type=sequence.source_type, profile=sequence.profile, status="succeeded", time_basis=basis,
        coordinate_frame=registration.coordinate_frame,
        registration=RegistrationResult(status="estimated", warnings=list(dict.fromkeys(w for f in registration.frames for w in f.warnings))),
        detections=detections, tracks=tracks, metrics=None, runtime_ms=(perf_counter()-started)*1000,
        warnings=notices, provenance=Provenance(input_sha256=input_hash,
            config_sha256=hashlib.sha256(json.dumps(effective, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            code_commit=None, dataset_version=sequence.dataset_version))
    diagnostic.update(status="succeeded", error=None, runtime_ms=result.runtime_ms)
    return result
