"""Internal telescope-profile suitability diagnostics, independent of inference.

Pixel arrays only; no labels, files, HTTP, physical object classification or API
schema changes. Thresholds are declared heuristics, not a trained daylight model.
See ROBUSTNESS.md for inputs, units, limits and the integration proposal.
"""

from collections.abc import Sequence

import cv2
import numpy as np

from .candidates import normalize_grayscale, robust_sigma


EXPLANATIONS = {
    'invalid_pixels': 'Expected bounded finite grayscale uint8/uint16 or normalized floating pixels.',
    'dimensions_too_small': 'Each dimension must be at least 32 pixels for feature assessment.',
    'inconsistent_dimensions': 'Frames must have identical native dimensions.',
    'sequence_length': 'This diagnostic profile requires exactly five frames.',
    'broad_bright_field': 'Broad bright background and brightness quantiles mismatch the dim telescope profile; daylight is one possible cause.',
    'severe_clipping': 'More than 80% of pixels are saturated at the upper limit.',
    'low_feature_evidence': 'Too few high-contrast features to establish suitability; this does not establish absence of objects.',
    'excessive_noise': 'Robust high-frequency noise exceeds the declared normalized-intensity limit.',
    'possible_blur': 'High-contrast features have weak high-frequency structure; blur is possible.',
    'background_inconsistency': 'Background medians change by more than 0.25 normalized intensity across frames.',
}


def _frame(pixels, index):
    reasons, metrics = [], {}
    try:
        image, quantum = normalize_grayscale(pixels)
    except (TypeError, ValueError):
        return {'frame_index': index, 'status': 'unsupported', 'reason_codes': ['invalid_pixels'], 'metrics': metrics}
    if min(image.shape) < 32:
        reasons.append('dimensions_too_small')
    q01, q10, q50, q90, q99 = map(float, np.percentile(image, [1, 10, 50, 90, 99]))
    smooth = cv2.GaussianBlur(image, (0, 0), .8)
    response = smooth - cv2.GaussianBlur(image, (0, 0), 8)
    noise = robust_sigma(image - smooth, max(quantum * .5, 1e-6))
    mask = (response > max(6 * noise, 3 * quantum)).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    features = sum(2 <= int(s[cv2.CC_STAT_AREA]) <= 300 for s in stats[1:count])
    # Ratio is a blur indicator, not an optical PSF or calibrated blur estimate.
    lap = cv2.Laplacian(smooth, cv2.CV_32F)
    gx = cv2.Sobel(smooth, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(smooth, cv2.CV_32F, 0, 1)
    sharpness = float(np.mean(lap**2) / max(float(np.mean(gx**2 + gy**2)), 1e-12))
    saturation = float(np.mean(image >= 1 - quantum * .5))
    metrics.update(width_px=int(image.shape[1]), height_px=int(image.shape[0]), dtype=str(pixels.dtype),
                   q01=q01, q10=q10, median=q50, q90=q90, q99=q99,
                   dynamic_range_q99_q01=q99-q01, upper_saturation_fraction=saturation,
                   lower_clipping_fraction=float(np.mean(image <= quantum * .5)),
                   robust_noise_normalized=float(noise), high_contrast_features=int(features),
                   sharpness_ratio=sharpness)
    if saturation > .8:
        reasons.append('severe_clipping')
    # Three quantiles AND spatial occupancy; never a single mean cutoff.
    if q10 > .4 and q50 > .6 and q90 > .7 and float(np.mean(image > .5)) > .8:
        reasons.append('broad_bright_field')
    if features < 8:
        reasons.append('low_feature_evidence')
    if noise > .08:
        reasons.append('excessive_noise')
    if features >= 8 and sharpness < .008:
        reasons.append('possible_blur')
    unsupported = {'dimensions_too_small', 'severe_clipping', 'broad_bright_field'}
    status = 'unsupported' if unsupported.intersection(reasons) else 'uncertain' if reasons else 'supported'
    return {'frame_index': index, 'status': status, 'reason_codes': reasons, 'metrics': metrics}


def validate_sequence_suitability(frames: Sequence[np.ndarray]) -> dict:
    """Assess five decoded arrays; JSON-finite internal diagnostics, no I/O.

    Supported means appropriate for testing the current grayscale telescope
    candidate pipeline. Unsupported/uncertain means request review/reacquisition,
    NEVER "no debris". Encoded PNG/JPEG validity belongs to existing bounded
    decoders: this function examines the decoded pixel format only.
    """
    if not isinstance(frames, Sequence) or len(frames) != 5:
        return {'status': 'unsupported', 'inference_allowed': False, 'reason_codes': ['sequence_length'],
                'explanations': [EXPLANATIONS['sequence_length']], 'frames': [], 'profile': 'telescope_grayscale_v1'}
    results = [_frame(pixels, i) for i, pixels in enumerate(frames)]
    reasons = list(dict.fromkeys(code for f in results for code in f['reason_codes']))
    shapes = {(f['metrics'].get('width_px'), f['metrics'].get('height_px')) for f in results}
    if len(shapes) != 1:
        reasons.append('inconsistent_dimensions')
    medians = [f['metrics']['median'] for f in results if 'median' in f['metrics']]
    if medians and max(medians)-min(medians) > .25:
        reasons.append('background_inconsistency')
    status = ('unsupported' if any(f['status'] == 'unsupported' for f in results) or 'inconsistent_dimensions' in reasons
              else 'uncertain' if reasons else 'supported')
    return {'status': status, 'inference_allowed': status == 'supported', 'reason_codes': reasons,
            'explanations': [EXPLANATIONS[c] for c in reasons], 'frames': results,
            'profile': 'telescope_grayscale_v1', 'score_semantics': 'uncalibrated_rules',
            'action': 'candidate_inference_permitted' if status == 'supported' else 'review_or_reacquire_input'}
