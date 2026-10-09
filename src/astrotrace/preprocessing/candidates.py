"""Native-grid float normalization and conservative compact-source enhancement."""

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class CandidateImage:
    response: np.ndarray
    noise: np.ndarray
    global_noise: float


def normalize_grayscale(pixels: np.ndarray) -> tuple[np.ndarray, float]:
    """Return a new float32 array in [0,1] using dtype range, plus quantization step.

    uint8 and uint16 are supported; float32/64 must already be finite [0,1].
    No min/max stretching, resizing, transposition or geometric conversion.
    """
    if not isinstance(pixels, np.ndarray) or pixels.ndim != 2 or not pixels.size:
        raise ValueError("Expected a nonempty 2D grayscale NumPy array")
    if pixels.size > 4_000_000:
        raise ValueError("Image exceeds 4,000,000 pixel processing limit")
    if pixels.dtype in (np.dtype("uint8"), np.dtype("uint16")):
        scale = float(np.iinfo(pixels.dtype).max)
        return pixels.astype(np.float32) / scale, 1.0 / scale
    if pixels.dtype not in (np.dtype("float32"), np.dtype("float64")):
        raise ValueError("Expected uint8, uint16 or normalized float32/64 grayscale")
    if not np.isfinite(pixels).all() or pixels.min() < 0 or pixels.max() > 1:
        raise ValueError("Float grayscale must be finite and lie in [0,1]")
    return pixels.astype(np.float32, copy=True), 1.0 / 65535


def robust_sigma(values: np.ndarray, floor: float) -> float:
    """Median absolute deviation scale; a declared floor handles constant images."""
    median = float(np.median(values))
    return max(1.4826 * float(np.median(np.abs(values - median))), floor)


def enhance_compact(image: np.ndarray, *, denoise_sigma: float, background_sigma: float,
                    noise_sigma: float, quantization: float) -> CandidateImage:
    """Mild Gaussian denoising minus broad Gaussian background on the same grid.

    This difference-of-Gaussians response enhances compact peaks. A clipped local
    residual RMS and global MAD floor form an adaptive noise map; bright sources
    cannot arbitrarily inflate local thresholds. No temporal differencing or
    median erosion is used, and all pixel coordinates remain unchanged.
    """
    smooth = cv2.GaussianBlur(image, (0, 0), denoise_sigma, borderType=cv2.BORDER_REFLECT_101)
    background = cv2.GaussianBlur(image, (0, 0), background_sigma, borderType=cv2.BORDER_REFLECT_101)
    response = smooth - background
    response -= np.median(response)
    sigma = robust_sigma(response, quantization * 0.5)
    clipped = np.clip(response, -3 * sigma, 3 * sigma)
    variance = cv2.GaussianBlur(clipped * clipped, (0, 0), noise_sigma, borderType=cv2.BORDER_REFLECT_101)
    noise = np.maximum(np.sqrt(np.maximum(variance, 0)), sigma * 0.5)
    return CandidateImage(response, noise, sigma)
