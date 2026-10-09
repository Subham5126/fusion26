"""Image-only neighborhood features; no labels, image warps or calibrated PSF claim."""

import cv2
import numpy as np


def measure_candidate(image: np.ndarray, x: float, y: float, bbox, quantum: float) -> dict[str, float]:
    """Raw normalized aperture/ring, spike concentration and low-threshold support.

    image is an already validated native-grid normalized grayscale array. A radius
    3.5..6.5 px ring estimates median background and MAD noise; a radius 2.5 px
    aperture measures signed integrated contrast. Connected support above 2 raw
    noise scales around the local 3x3 peak measures contextual elongation, including
    wings excluded by the proposal threshold. Edge windows are clipped explicitly.
    These are shape heuristics, not fitted physical PSF or scientific SNR calibration.
    """
    height, width = image.shape
    cx, cy = int(np.rint(x)), int(np.rint(y))
    left, top = max(0, cx - 7), max(0, cy - 7)
    right, bottom = min(width, cx + 8), min(height, cy + 8)
    patch = image[top:bottom, left:right].astype(np.float64)
    yy, xx = np.mgrid[top:bottom, left:right]
    radius2 = (xx - x)**2 + (yy - y)**2
    ring = patch[(radius2 >= 3.5**2) & (radius2 <= 6.5**2)]
    if not ring.size:
        ring = patch.ravel()
    background = float(np.median(ring))
    noise = max(1.4826 * float(np.median(np.abs(ring - background))), quantum * 0.5)
    signal = patch - background
    aperture = radius2 <= 2.5**2
    aperture_snr = float(signal[aperture].sum() / (noise * np.sqrt(max(1, aperture.sum()))))
    core = signal[(np.abs(xx - x) <= 1.5) & (np.abs(yy - y) <= 1.5)]
    positive = np.maximum(core, 0)
    concentration = float(positive.max() / positive.sum()) if positive.size and positive.sum() > 0 else 0.0
    support = ((signal > 2 * noise) & (radius2 <= 6.5**2)).astype(np.uint8)
    _, labels = cv2.connectedComponents(support, connectivity=8)
    seed_window = (np.abs(xx - x) <= 1.5) & (np.abs(yy - y) <= 1.5)
    seed_candidates = np.flatnonzero(seed_window)
    seed = seed_candidates[np.argmax(signal.ravel()[seed_candidates])]
    seed_label = labels.ravel()[seed]
    context_elongation, context_area = 1.0, 0
    if seed_label:
        selected = labels == seed_label
        rows, cols = np.nonzero(selected)
        weights = np.maximum(signal[selected] - noise, 0)
        total = weights.sum()
        dx = cols - np.dot(cols, weights) / total
        dy = rows - np.dot(rows, weights) / total
        covariance = np.array([[np.dot(weights, dx * dx), np.dot(weights, dx * dy)],
                               [np.dot(weights, dx * dy), np.dot(weights, dy * dy)]]) / total
        eigenvalues = np.linalg.eigvalsh(covariance) + 1 / 12
        context_elongation = float(np.sqrt(eigenvalues[1] / eigenvalues[0]))
        context_area = int(selected.sum())
    x0, y0, x1, y1 = bbox
    aspect = float(max(x1 - x0, y1 - y0) / min(x1 - x0, y1 - y0))
    return {"aperture_snr_heuristic": aperture_snr, "raw_peak_fraction": concentration,
            "context_elongation": context_elongation, "context_area_px": float(context_area),
            "component_aspect": aspect, "local_noise_normalized": noise,
            "local_contrast_normalized": float(positive.max()) if positive.size else 0.0}
