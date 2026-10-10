"""Small supervised candidate scorer. Pure numerical inference, no label/file IO."""
import hashlib
import json
import numpy as np

FEATURES = ('peak_snr_heuristic', 'area_px', 'elongation', 'aperture_snr_heuristic',
            'raw_peak_fraction', 'context_elongation', 'context_area_px',
            'component_aspect', 'local_noise_normalized', 'local_contrast_normalized')
VERSION = 'candidate-logistic-v1'


def feature_vector(detection):
    if not isinstance(detection.evidence_statistics, dict):
        raise ValueError('Candidate features unavailable')
    values = [detection.evidence_statistics.get(name) for name in FEATURES]
    if any(v is None or not np.isfinite(v) for v in values):
        raise ValueError('Missing/nonfinite candidate features')
    # Signed log for dynamic-range compression; exactly reused in training.
    array = np.asarray(values, dtype=float)
    return np.sign(array) * np.log1p(np.abs(array))


def validate_model(model):
    if not isinstance(model, dict):
        raise ValueError('Model must be an object')
    if (model.get('version') != VERSION or model.get('features') != list(FEATURES)
            or model.get('detector_name') != 'opencv_context_filtered_v2'):
        raise ValueError('Incompatible model feature/detector version')
    for key in ('mean', 'scale', 'coef'):
        a = np.asarray(model.get(key), dtype=float)
        if a.shape != (len(FEATURES),) or not np.isfinite(a).all():
            raise ValueError('Invalid model dimensions or coefficients')
    if (min(model['scale']) <= 0 or not isinstance(model.get('intercept'), (int, float))
            or not np.isfinite(model['intercept'])):
        raise ValueError('Invalid model scale/intercept')
    return model


def score_candidates(detections, model):
    model = validate_model(model)
    scores = []
    for d in detections:
        if d.detector_name != model['detector_name']:
            raise ValueError('Detector not compatible with training data')
        x = (feature_vector(d) - model['mean']) / model['scale']
        z = np.clip(x @ model['coef'] + model['intercept'], -35, 35)
        score = float(1 / (1 + np.exp(-z)))
        scores.append({'detection_id': d.detection_id, 'frame_index': d.frame_index,
                       'score': score, 'category': 'high' if score >= .7 else 'medium' if score >= .4 else 'low'})
    return {'status': 'experimental', 'model_name': VERSION,
            'model_sha256': hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest(),
            'interpretation': 'Uncalibrated annotation-match score; not a probability of debris identity. No automatic filtering.',
            'automatic_filtering': False, 'candidates': scores}
