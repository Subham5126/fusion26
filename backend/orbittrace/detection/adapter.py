"""Contract 0.1.0 bridge; algorithms remain in astrotrace, with no IO or truth.

Both src and backend must be importable until Integration packages astrotrace.
The default optimized configuration is the frozen CV-T04 selection; explicit
numeric overrides are validated by the original config classes. IDs identify
proposals, never persistent objects. Raw/reference transforms are not invented.
"""

from collections.abc import Mapping, Sequence
import hashlib
import math
import re
from typing import Literal

import numpy as np

from app.schemas.result import Detection
from astrotrace.detection.baseline import BaselineConfig, OpenCVBaselineDetector
from astrotrace.detection.interface import FrameContext
from astrotrace.detection.optimized import OptimizedConfig, OptimizedDetector

Method = Literal["baseline", "optimized"]
Profile = Literal["synthetic_static_stars", "ground_static_star_streaks", "spotgeo"]


def _settings(method: Method, config: Mapping[str, object] | None):
    if method == "baseline":
        detector, defaults = OpenCVBaselineDetector(), BaselineConfig()
    elif method == "optimized":
        detector = OptimizedDetector()
        defaults = OptimizedConfig(threshold_sigma=4.5, max_context_elongation=2.0)
    else:
        raise ValueError("method must be baseline or optimized")
    if config is not None and not isinstance(config, Mapping):
        raise ValueError("config must be a declared numeric mapping or None")
    declared = type(defaults).from_mapping({**defaults.to_dict(), **(config or {})})
    return detector, declared


def _namespace(sequence_id: str, detector_name: str) -> str:
    if not isinstance(sequence_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", sequence_id):
        raise ValueError("sequence_id must be a contract-compatible opaque ID")
    return hashlib.sha256(f"{sequence_id}/{detector_name}".encode()).hexdigest()[:16]


def detect_frame(
    pixels: np.ndarray,
    context: FrameContext,
    config: Mapping[str, object] | None = None,
    *,
    method: Method = "optimized",
    sequence_id: str = "sequence",
) -> list[Detection]:
    """Detect one native grayscale frame; no candidates returns [].

    context declares the actual frame index/dimensions/profile and optional time.
    Invalid images/metadata/config raise ValueError. Original cap warnings propagate.
    Repeated calls with identical inputs/sequence ID produce identical proposal IDs.
    Use distinct sequence_id values when combining results from different sequences.
    """
    detector, declared = _settings(method, config)
    token = _namespace(sequence_id, detector.name)
    candidates = detector.detect(pixels, context, declared.to_dict())
    if len(candidates) > declared.max_candidates:
        raise ValueError("Detector exceeded declared candidate cap")
    output = []
    for rank, candidate in enumerate(candidates):
        # Revalidate instead of model_copy(update=...), which bypasses validators.
        detection = Detection.model_validate({
            **candidate.model_dump(),
            "detection_id": f"s{token}-f{context.frame_index}-c{rank}",
        })
        left, top, right, bottom = detection.bbox_raw_px
        if (detection.frame_index != context.frame_index
                or detection.detector_name != detector.name
                or not 0 <= left < right <= context.width_px
                or not 0 <= top < bottom <= context.height_px):
            raise ValueError("Detector returned wrong-frame/name or out-of-image geometry")
        output.append(detection)
    return output


def detect_sequence(
    frames: Sequence[np.ndarray],
    *,
    sequence_id: str,
    profile: Profile = "spotgeo",
    timestamps_s: Sequence[float | None] | None = None,
    config: Mapping[str, object] | None = None,
    method: Method = "optimized",
) -> list[Detection]:
    """Return a flat list for Tracker.process_sequence, in frame/proposal order.

    Accepts 0..30 ordered same-size arrays (public SequenceInput still requires
    3..30). Empty frames produce no detections; pass range(len(frames)) to tracking
    so missing/trailing empty frames advance lifecycle. Timestamps must be all
    unknown or finite strictly increasing seconds; no cadence is inferred.
    """
    detector, _ = _settings(method, config)
    _namespace(sequence_id, detector.name)
    if profile not in ("spotgeo", "synthetic_static_stars", "ground_static_star_streaks"):
        raise ValueError("Unsupported acquisition profile")
    if not isinstance(frames, Sequence) or isinstance(frames, (str, bytes)) or len(frames) > 30:
        raise ValueError("frames must be an ordered sequence of at most 30 grayscale arrays")
    if timestamps_s is None:
        timestamps = [None] * len(frames)
    else:
        if (not isinstance(timestamps_s, Sequence) or isinstance(timestamps_s, (str, bytes))
                or len(timestamps_s) != len(frames)):
            raise ValueError("timestamps_s must match the frame count")
        timestamps = list(timestamps_s)
    if any(t is not None for t in timestamps):
        if any(type(t) not in (int, float) or not math.isfinite(t) for t in timestamps):
            raise ValueError("Provide all finite timestamps or leave all unknown")
        if any(b <= a for a, b in zip(timestamps, timestamps[1:])):
            raise ValueError("Timestamps must increase strictly")
    shape = None
    for pixels in frames:
        if not isinstance(pixels, np.ndarray) or pixels.ndim != 2 or not pixels.size:
            raise ValueError("Expected nonempty 2D grayscale arrays")
        if shape is None:
            shape = pixels.shape
        if pixels.shape != shape:
            raise ValueError("P0 requires equal native frame dimensions")
    output = []
    for index, (pixels, timestamp) in enumerate(zip(frames, timestamps)):
        context = FrameContext(index, pixels.shape[1], pixels.shape[0], profile, timestamp)
        output.extend(detect_frame(pixels, context, config, method=method, sequence_id=sequence_id))
    return output
