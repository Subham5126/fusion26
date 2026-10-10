import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from app.services.candidate_assessment import assess_result, load_model
from astrotrace.detection.assessment import FEATURES, feature_vector, score_candidates, validate_model
from astrotrace.detection.precision import precision_config

MODEL = Path(__file__).resolve().parents[2] / 'configs/candidate_assessment_v1.json'


def candidate(**changes):
    return SimpleNamespace(detection_id='one',frame_index=0,detector_name='opencv_context_filtered_v2',
        evidence_statistics={name:float(i+1) for i,name in enumerate(FEATURES)},**changes)


def test_real_serialized_model_is_finite_bounded_and_does_not_mutate_candidates():
    model=json.loads(MODEL.read_text()); d=candidate(); before=d.evidence_statistics.copy()
    assessed=score_candidates([d],model)
    assert assessed['automatic_filtering'] is False and assessed['status']=='experimental'
    assert 0 <= assessed['candidates'][0]['score'] <= 1
    assert d.evidence_statistics==before
    assert np.isfinite(feature_vector(d)).all()


@pytest.mark.parametrize('payload',[[],None,{}, {'version':'wrong'}])
def test_invalid_model_fails_validation(payload):
    with pytest.raises(ValueError): validate_model(payload)


@pytest.mark.parametrize('case',['missing','invalid','oversize','incompatible','absent','temporal','features','null_features'])
def test_optional_model_failures_preserve_the_analysis(monkeypatch,tmp_path,case):
    model=json.loads(MODEL.read_text()); path=tmp_path/'model.json'; d=candidate()
    if case=='invalid': path.write_text('[]')
    elif case=='oversize': path.write_text(' '*100001)
    elif case!='missing': path.write_text(json.dumps(model))
    if case=='temporal': d.detector_name='opencv_temporal_residual_v1'
    if case=='features': d.evidence_statistics={}
    if case=='null_features': d.evidence_statistics=None
    monkeypatch.setenv('ORBITTRACE_CANDIDATE_MODEL',str(path))
    if case=='absent': monkeypatch.delenv('ORBITTRACE_CANDIDATE_MODEL')
    diagnostic={'config':{'detector':{} if case=='incompatible' else precision_config().to_dict()}}
    result=SimpleNamespace(detections=[d]); load_model.cache_clear()
    assert assess_result(result,diagnostic)['status']=='unavailable'
    assert result.detections==[d]


def test_model_is_cached_and_requires_exact_training_configuration(monkeypatch):
    monkeypatch.setenv('ORBITTRACE_CANDIDATE_MODEL',str(MODEL));load_model.cache_clear()
    result=SimpleNamespace(detections=[candidate()]);diag={'config':{'detector':precision_config().to_dict()}}
    assert assess_result(result,diag)['status']=='experimental'
    assert assess_result(result,diag)['status']=='experimental'
    assert load_model.cache_info().hits==1


def test_empty_motion_mode_does_not_claim_raw_detector_model_compatibility(monkeypatch):
    monkeypatch.setenv('ORBITTRACE_CANDIDATE_MODEL',str(MODEL))
    assert assess_result(SimpleNamespace(detections=[]),{'config':{'detector':precision_config().to_dict(),
        'shared':{'analysis_mode':'temporal'}}})['status']=='unavailable'
