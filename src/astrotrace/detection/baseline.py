"""CPU image-only compact candidate detector and minimal global-threshold comparator."""

from dataclasses import asdict, dataclass, fields
import math
from typing import Mapping
import warnings

import cv2
import numpy as np

from app.schemas.result import Detection
from astrotrace.preprocessing.candidates import enhance_compact, normalize_grayscale, robust_sigma
from .interface import FrameContext


class CandidateLimitWarning(UserWarning):
    """Usable proposals exceed the declared cap; truncation must be reported."""


@dataclass(frozen=True)
class BaselineConfig:
    denoise_sigma: float = 0.8
    background_sigma: float = 8.0
    noise_sigma: float = 12.0
    threshold_sigma: float = 4.5
    min_area_px: int = 3
    max_area_px: int = 150
    max_elongation: float = 4.0
    max_candidates: int = 200

    def __post_init__(self):
        numeric_bounds = {"denoise_sigma": (0.3, 2.0), "background_sigma": (2.0, 30.0),
                          "noise_sigma": (2.0, 40.0), "threshold_sigma": (2.0, 15.0),
                          "max_elongation": (1.0, 20.0)}
        for name, (lo, hi) in numeric_bounds.items():
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or not lo <= value <= hi:
                raise ValueError(f"{name} must be finite in [{lo},{hi}]")
        if self.background_sigma <= self.denoise_sigma:
            raise ValueError("background_sigma must exceed denoise_sigma")
        for name in ("min_area_px", "max_area_px", "max_candidates"):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= 10_000:
                raise ValueError(f"{name} must be an integer in 1..10000")
        if self.min_area_px > self.max_area_px or self.max_candidates > 2000:
            raise ValueError("Invalid area range or excessive candidate cap")

    @classmethod
    def from_mapping(cls, config: Mapping[str, object]):
        if not isinstance(config, Mapping) or set(config) - {f.name for f in fields(cls)}:
            raise ValueError("Unknown detector config keys; only declared numeric parameters are accepted")
        return cls(**dict(config))

    def to_dict(self) -> dict:
        return asdict(self)


def _validate(pixels: np.ndarray, context: FrameContext) -> tuple[np.ndarray, float]:
    image, quantization = normalize_grayscale(pixels)
    if not isinstance(context, FrameContext):
        raise ValueError("Expected FrameContext")
    if type(context.frame_index) is not int or not 0 <= context.frame_index <= 1_000_000:
        raise ValueError("frame_index must be a nonnegative bounded integer")
    if type(context.width_px) is not int or type(context.height_px) is not int:
        raise ValueError("Frame dimensions must be integers")
    if image.shape != (context.height_px, context.width_px):
        raise ValueError("FrameContext dimensions do not match image")
    if context.profile not in ("spotgeo", "synthetic_static_stars", "ground_static_star_streaks"):
        raise ValueError("Unsupported acquisition profile")
    if context.timestamp_s is not None and (type(context.timestamp_s) not in (int, float)
                                           or not math.isfinite(context.timestamp_s)):
        raise ValueError("timestamp_s must be finite or None")
    return image, quantization


def _components(response: np.ndarray, noise: np.ndarray, config: BaselineConfig,
                context: FrameContext, detector_name: str) -> list[Detection]:
    mask = (response > config.threshold_sigma * noise).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    candidates = []
    for label in range(1, count):
        left, top, width, height, area = map(int, stats[label])
        if not config.min_area_px <= area <= config.max_area_px:
            continue
        region = labels[top:top + height, left:left + width] == label
        rows, cols = np.nonzero(region)
        weights = response[top:top + height, left:left + width][region].astype(np.float64)
        total = float(weights.sum())
        x = float(np.dot(cols, weights) / total + left)
        y = float(np.dot(rows, weights) / total + top)
        dx, dy = cols + left - x, rows + top - y
        covariance = np.array([[np.dot(weights, dx * dx), np.dot(weights, dx * dy)],
                               [np.dot(weights, dx * dy), np.dot(weights, dy * dy)]]) / total
        # Quantization variance avoids infinite elongation for thin/one-pixel shapes.
        eigenvalues = np.linalg.eigvalsh(covariance) + 1.0 / 12.0
        elongation = float(np.sqrt(eigenvalues[1] / eigenvalues[0]))
        if elongation > config.max_elongation:
            continue
        local_noise = noise[top:top + height, left:left + width][region]
        peak_snr = float(np.max(weights / local_noise))
        score = float((1.0 - math.exp(-peak_snr / 8.0)) / max(1.0, elongation))
        candidates.append({"x": x, "y": y, "bbox": (left, top, left + width, top + height),
                           "score": score, "area": area, "elongation": elongation, "peak_snr": peak_snr})
    candidates.sort(key=lambda item: (-item["score"], item["y"], item["x"]))
    if len(candidates) > config.max_candidates:
        warnings.warn(f"{len(candidates)} proposals exceed cap {config.max_candidates}; strongest retained",
                      CandidateLimitWarning, stacklevel=3)
        candidates = candidates[:config.max_candidates]
    return [Detection(
        detection_id=f"f{context.frame_index}-c{index}", frame_index=context.frame_index,
        x_raw_px=item["x"], y_raw_px=item["y"], bbox_raw_px=item["bbox"],
        kind="compact" if item["elongation"] <= 2.0 else "unknown",
        quality_score=item["score"], detector_name=detector_name,
        evidence_statistics={"area_px": float(item["area"]), "elongation": item["elongation"],
                             "peak_snr_heuristic": item["peak_snr"]},
    ) for index, item in enumerate(candidates)]


class OpenCVBaselineDetector:
    """Stateless Detector implementation; no label/path/sequence-memory input."""

    name = "opencv_compact_dog_v1"

    def detect(self, pixels: np.ndarray, context: FrameContext,
               config: Mapping[str, object]) -> list[Detection]:
        declared = BaselineConfig.from_mapping(config)
        image, quantum = _validate(pixels, context)
        prepared = enhance_compact(image, denoise_sigma=declared.denoise_sigma,
                                   background_sigma=declared.background_sigma,
                                   noise_sigma=declared.noise_sigma, quantization=quantum)
        return _components(prepared.response, prepared.noise, declared, context, self.name)


class MinimalThresholdDetector:
    """Comparator: median/MAD global threshold with no denoising/background model.

    Same component extraction/centroid, but broad area/elongation filters. Declared
    thresholds can be tuned on the same development sequences as the main method.
    """

    name = "global_mad_threshold_v1"

    def detect(self, pixels: np.ndarray, context: FrameContext,
               config: Mapping[str, object]) -> list[Detection]:
        declared = BaselineConfig.from_mapping(config)
        image, quantum = _validate(pixels, context)
        response = image - np.median(image)
        sigma = robust_sigma(response, quantum * 0.5)
        return _components(response, np.full(image.shape, sigma, dtype=np.float32), declared, context, self.name)
