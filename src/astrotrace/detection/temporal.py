"""Optional registered-background subtraction; image-only native-grid detection.

The unchanged single-frame detector remains the default API mode. Residual
proposals are experimental motion candidates, not a test of debris identity.
"""
import warnings

import cv2
import numpy as np

from astrotrace.preprocessing.candidates import normalize_grayscale
from astrotrace.preprocessing.registration import warp_to_reference
from orbittrace.detection.adapter import detect_sequence


def detect_temporal_sequence(frames, registration, *, sequence_id, profile,
                             timestamps_s, config):
    """Detect positive residuals after a five-frame registered temporal median.

    Detection happens on each original-sized grid, with the median warped BACK
    into that grid. Require >=3 valid contributing images and erode interpolation
    edges. No annotated coordinates, identities, filenames or labels are inputs.
    A stationary/very slow target can be removed: keep original detections in
    diagnostics and provide the unchanged standard mode to review that tradeoff.
    """
    if len(frames) != 5 or len(registration.frames) != 5 or registration.status != 'estimated':
        raise ValueError('Temporal detection requires five registered frames')
    aligned = [warp_to_reference(pixels, transform)
               for pixels, transform in zip(frames, registration.frames)]
    valid = np.array([mask for _, mask in aligned])
    stack = np.array([np.where(mask, pixels, np.nan) for pixels, mask in aligned])
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)  # all-invalid edges masked below
        background = np.nanmedian(stack, axis=0)
    support = (valid.sum(axis=0) >= 3).astype(np.uint8)
    height, width = frames[0].shape
    residuals = []
    for pixels, transform in zip(frames, registration.frames):
        inverse = np.asarray(transform.reference_to_raw)[:2]
        native_background = cv2.warpAffine(np.nan_to_num(background), inverse, (width, height))
        native_support = cv2.warpAffine(support, inverse, (width, height), flags=cv2.INTER_NEAREST)
        native_support = cv2.erode(native_support, np.ones((5, 5), np.uint8),
                                    borderType=cv2.BORDER_CONSTANT, borderValue=0)
        image, _ = normalize_grayscale(pixels)
        residuals.append(np.where(native_support, np.clip(image-native_background+.1, 0, 1), .1).astype(np.float32))
    proposals = detect_sequence(residuals, sequence_id=sequence_id, profile=profile,
                                timestamps_s=timestamps_s, config=config, method='optimized')
    return [d.model_copy(update={'detector_name': 'opencv_temporal_residual_v1'}) for d in proposals]
