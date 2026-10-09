"""Five-frame inference and local evidence output; no annotations or tracking."""

from dataclasses import dataclass
import hashlib
from time import perf_counter
import warnings

from app.schemas.result import Detection
from astrotrace.datasets.spotgeo import Sequence
from .baseline import BaselineConfig, CandidateLimitWarning
from .interface import Detector, FrameContext


@dataclass(frozen=True)
class FrameDetections:
    frame_index: int
    detections: tuple[Detection, ...]
    processing_ms: float
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class SequenceDetections:
    """Local evidence envelope, not a new shared/public API contract."""

    sequence_id: str
    split: str
    frames: tuple[FrameDetections, ...]

    def to_dict(self) -> dict:
        return {"schema_version": "0.1.0", "sequence_id": self.sequence_id, "split": self.split,
                "coordinate_system": "raw_top_left_xy_px_integer_centers",
                "score_type": "uncalibrated_heuristic", "tracking_performed": False,
                "frames": [{"frame_index": frame.frame_index, "processing_ms": frame.processing_ms,
                            "warnings": frame.warnings,
                            "detections": [d.model_dump(mode="json") for d in frame.detections]}
                           for frame in self.frames]}


def detect_sequence(sequence: Sequence, detector: Detector, config: dict) -> SequenceDetections:
    """Call agreed detect(pixels, FrameContext, mapping)->list[Detection] five times.

    Timing excludes image loading and evaluation. Namespace IDs across dataset split
    and sequence; ID reuse never establishes cross-frame identity. No labels accepted.
    """
    BaselineConfig.from_mapping(config)
    if len(sequence.frames) != 5:
        raise ValueError("Expected exactly five frames")
    token = hashlib.sha256(f"{sequence.split}/{sequence.sequence_id}".encode()).hexdigest()[:16]
    output = []
    for index, frame in enumerate(sequence.frames):
        if frame.frame_index != index or frame.official_frame != index + 1:
            raise ValueError("Sequence frame order must be contiguous official 1..5")
        context = FrameContext(index, frame.width_px, frame.height_px, "spotgeo", frame.timestamp_s)
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always", CandidateLimitWarning)
            started = perf_counter()
            detections = detector.detect(frame.pixels, context, config)
            elapsed = (perf_counter() - started) * 1000
        namespaced = []
        for detection in detections:
            if not isinstance(detection, Detection) or detection.frame_index != index:
                raise ValueError("Detector returned an invalid or wrong-frame Detection")
            data = detection.model_dump()
            data["detection_id"] = f"s{token}-{detection.detection_id}"
            namespaced.append(Detection.model_validate(data))
        if len({d.detection_id for d in namespaced}) != len(namespaced):
            raise ValueError("Detector returned duplicate IDs")
        output.append(FrameDetections(index, tuple(namespaced), elapsed,
                                      tuple(str(w.message) for w in captured)))
    return SequenceDetections(sequence.sequence_id, sequence.split, tuple(output))
