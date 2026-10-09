"""OrbitTrace image-only filtering experiment; preserves the T03 detector."""

from dataclasses import fields, replace
import math
from typing import Mapping
import warnings

import numpy as np

from app.schemas.result import Detection
from astrotrace.preprocessing.optimized_candidates import enhance_with_coarse_maps
from .baseline import BaselineConfig, CandidateLimitWarning, _components, _validate
from .diagnostics import measure_candidate
from .interface import FrameContext
from .runner import SequenceDetections, detect_sequence


from dataclasses import dataclass


@dataclass(frozen=True)
class OptimizedConfig(BaselineConfig):
    """Bounded, explicit numeric settings; no label/path inputs are accepted."""

    denoise_sigma: float = 0.6
    threshold_sigma: float = 5.5
    max_elongation: float = 2.5
    background_step: int = 1
    min_aperture_snr: float = 0.0
    max_peak_fraction: float = 0.55
    max_context_elongation: float = 2.5
    max_component_aspect: float = 20.0
    min_score: float = 0.0

    def __post_init__(self):
        super().__post_init__()
        if type(self.background_step) is not int or self.background_step not in (1, 2, 4):
            raise ValueError("background_step must be 1, 2 or 4")
        for name, bounds in {"min_aperture_snr": (0, 100), "max_peak_fraction": (0.1, 1),
                             "max_context_elongation": (1, 20), "max_component_aspect": (1, 20),
                             "min_score": (0, 1)}.items():
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or not bounds[0] <= value <= bounds[1]:
                raise ValueError(f"{name} must be finite in {bounds}")

    def baseline_mapping(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(BaselineConfig)}


class OptimizedDetector:
    """Stateless native-coordinate Detector; local shape/noise gates, no tracking.

    Quality retains T03's (1-exp(-peak_snr/8))/max(1,elongation). Added evidence
    fields explain filters; neither quality nor aperture SNR is calibrated.
    """

    name = "opencv_context_filtered_v2"

    def detect(self, pixels: np.ndarray, context: FrameContext,
               config: Mapping[str, object]) -> list[Detection]:
        declared = OptimizedConfig.from_mapping(config)
        image, quantum = _validate(pixels, context)
        prepared = enhance_with_coarse_maps(image, denoise_sigma=declared.denoise_sigma,
                                            background_sigma=declared.background_sigma,
                                            noise_sigma=declared.noise_sigma,
                                            quantization=quantum, background_step=declared.background_step)
        # Apply caller's final cap after filtering, rather than allow rejected
        # high-scoring spikes to crowd out usable proposals. Bound work at 2000.
        proposal_config = BaselineConfig(**declared.baseline_mapping())
        proposals = _components(prepared.response, prepared.noise,
                                replace(proposal_config, max_candidates=2000), context, self.name)
        output = []
        for candidate in proposals:
            features = measure_candidate(image, candidate.x_raw_px, candidate.y_raw_px,
                                         candidate.bbox_raw_px, quantum)
            if (features["aperture_snr_heuristic"] < declared.min_aperture_snr
                    or features["raw_peak_fraction"] > declared.max_peak_fraction
                    or features["context_elongation"] > declared.max_context_elongation
                    or features["component_aspect"] > declared.max_component_aspect
                    or candidate.quality_score < declared.min_score):
                continue
            data = candidate.model_dump()
            data["evidence_statistics"].update(features)
            output.append(Detection.model_validate(data))
        if len(output) > declared.max_candidates:
            warnings.warn(f"{len(output)} filtered candidates exceed cap {declared.max_candidates}; strongest retained",
                          CandidateLimitWarning, stacklevel=2)
            output = output[:declared.max_candidates]
        return [Detection.model_validate({**candidate.model_dump(),
                                         "detection_id": f"f{context.frame_index}-c{index}"})
                for index, candidate in enumerate(output)]


def detect_optimized_sequence(sequence, config: Mapping[str, object]) -> SequenceDetections:
    """Process five loaded frames with existing validation/timing/ID namespacing.

    The preserved T03 runner accepts baseline parameters only. This adapter binds
    validated extended parameters to the detector and passes the baseline subset
    to the runner. Returns its unchanged local SequenceDetections envelope.
    """
    declared = OptimizedConfig.from_mapping(config)

    class BoundDetector:
        def detect(self, pixels, context, _baseline_config):
            return OptimizedDetector().detect(pixels, context, declared.to_dict())

    return detect_sequence(sequence, BoundDetector(), declared.baseline_mapping())
