"""Optional operator-configured model. Never accepts a path from public requests."""
from functools import lru_cache
import json
import os
from pathlib import Path

from astrotrace.detection.assessment import score_candidates, validate_model


@lru_cache(maxsize=1)
def load_model(path):
    source = Path(path)
    if source.stat().st_size > 100_000:
        raise ValueError('Model exceeds bounded size')
    return validate_model(json.loads(source.read_text(encoding='utf-8')))


def assess_result(result, diagnostics):
    path = os.getenv('ORBITTRACE_CANDIDATE_MODEL')
    fallback = {'status': 'unavailable', 'model_name': None, 'candidates': [],
                'automatic_filtering': False, 'interpretation': 'No compatible supervised candidate model is enabled.'}
    if not path:
        return fallback
    try:
        if diagnostics.get('config', {}).get('shared', {}).get('analysis_mode') == 'temporal':
            return fallback  # even empty residual runs are outside this model's training domain
        model = load_model(path)
        if diagnostics.get('config', {}).get('detector') != model.get('detector_config'):
            return fallback
        return score_candidates(result.detections, model)
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        # Optional assessment must not fail the completed scientific pipeline.
        return fallback
