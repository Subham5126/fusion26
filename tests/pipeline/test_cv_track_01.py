"""Integration acceptance: real algorithms, native geometry and no inference IO."""
import builtins
import json
import os
from pathlib import Path
import cv2
import numpy as np
import pytest
from app.core.config import PipelineConfig
from app.schemas.result import AnalysisResult
from app.schemas.sequence import SequenceInput
from astrotrace.datasets import SpotGeoDataset
from astrotrace.datasets.stress import create_stress_scene
from astrotrace.detection.stress_evaluation import evaluate_stress
from astrotrace.preprocessing.registration_fixtures import create_registration_fixture
from orbittrace.cv_tracking import analyze_telescope_sequence, TelescopeAnalysisError
from orbittrace.detection.adapter import detect_sequence
from orbittrace.evaluation.cv_track_diagnostics import trace_associations


def manifest(frames, timestamps=None, source="synthetic"):
    return SequenceInput(schema_version="0.1.0",sequence_id="cv-track-test",source_type=source,profile="spotgeo",
        frames=[{"frame_index":i,"image_ref":f"image_{i}","width_px":p.shape[1],"height_px":p.shape[0],
                 "timestamp_s":None if timestamps is None else timestamps[i]} for i,p in enumerate(frames)])


def assert_contract(result):
    payload=result.model_dump_json(exclude_none=False)
    assert AnalysisResult.model_validate_json(payload)==result
    assert json.loads(payload)["metrics"] is None
    detections={d.detection_id:d for d in result.detections}
    observed=[p for t in result.tracks for p in t.points]
    assert len(observed)==len(result.detections)
    assert {p.detection_id for p in observed}==set(detections)
    for point in observed:
        detection=detections[point.detection_id]
        assert (point.x_raw_px,point.y_raw_px)==(detection.x_raw_px,detection.y_raw_px)
        assert (point.x_reference_px,point.y_reference_px)==(detection.x_reference_px,detection.y_reference_px)
    for track in result.tracks:
        assert track.observed_count==len(track.points)
        if track.trajectory:
            assert track.trajectory.observations_used>=3
            assert all(p.detection_id is None and p.point_type=="extrapolated" and p.x_raw_px is None for p in track.trajectory.predictions)


@pytest.mark.parametrize("case",["counts_change","crossing","empty_targets","artifacts","camera_motion","entry_exit","nearby"])
def test_actual_synthetic_scenarios(case):
    scene=create_stress_scene(case); before=[p.copy() for p in scene.frames]; diagnostics={}
    result=analyze_telescope_sequence(scene.frames,sequence=manifest(scene.frames),frame_indices=range(5),diagnostics=diagnostics)
    assert_contract(result)
    assert all(np.array_equal(a,b) for a,b in zip(before,scene.frames))
    score=evaluate_stress(result.detections,result.tracks,scene.truth)
    if case=="counts_change":
        assert [sum(d.frame_index==i for d in result.detections) for i in range(5)]==[5,3,4,5,5]
        assert len(result.tracks)==5 and all(t.status=="confirmed" and t.trajectory for t in result.tracks)
        assert sorted(t.observed_count for t in result.tracks)==[3,4,5,5,5]
        assert score["association"]["scripted_gaps_recovered"]==2
    if case=="empty_targets":
        assert result.detections==[] and result.tracks==[]
    if case=="artifacts":
        assert score["association"]["false_confirmed_tracks"]>=1  # honest known nuisance, not debris certification
    raw=detect_sequence(scene.frames,sequence_id="cv-track-test",method="optimized")
    assert len(raw)==len(result.detections)
    for original,mapped in zip(raw,result.detections):
        assert {k:v for k,v in mapped.model_dump().items() if k not in ("x_reference_px","y_reference_px")}=={k:v for k,v in original.model_dump().items() if k not in ("x_reference_px","y_reference_px")}
        reg=diagnostics["registration"]["frames"][mapped.frame_index]
        expected=np.asarray(reg["raw_to_reference"])@np.array([mapped.x_raw_px,mapped.y_raw_px,1])
        inverse=np.asarray(reg["reference_to_raw"])@expected
        assert np.allclose(expected[:2],[mapped.x_reference_px,mapped.y_reference_px])
        assert np.allclose(inverse[:2],[mapped.x_raw_px,mapped.y_raw_px])
    trace=trace_associations(result.detections)
    assert all(not p["selected"] or p["within_gate"] for f in trace["frames"] for p in f["pairs"])
    assert [(t["track_id"],t["observed_count"]) for t in trace["tracks"]]==[(t.track_id,t.observed_count) for t in result.tracks]


@pytest.mark.parametrize("case,code",[("daylight_like","unsupported_observation"),("noise_only","uncertain_observation"),("blurred","uncertain_observation")])
def test_scientific_rejections_are_existing_error_contracts(case,code):
    frames=create_stress_scene(case).frames; diagnostic={"stale":"discard"}
    with pytest.raises(TelescopeAnalysisError) as caught:
        analyze_telescope_sequence(frames,sequence=manifest(frames),diagnostics=diagnostic)
    assert caught.value.code==code
    assert caught.value.as_job_state().status=="failed"
    assert diagnostic["status"]=="failed" and "stale" not in diagnostic
    assert "registration" not in diagnostic
    json.dumps(diagnostic,allow_nan=False)


def test_accepted_suitability_failed_registration_has_no_identity_fallback():
    frames=list(create_registration_fixture().frames)
    frames[1]=cv2.warpAffine(frames[0],cv2.getRotationMatrix2D((128,96),5,1),(256,192))
    diagnostic={}
    with pytest.raises(TelescopeAnalysisError,match="tracking blocked"):
        analyze_telescope_sequence(frames,sequence=manifest(frames),diagnostics=diagnostic)
    assert diagnostic["suitability"]["status"]=="supported"
    assert diagnostic["registration"]["frames"][1]["raw_to_reference"] is None
    assert diagnostic["registration"]["frames"][1]["reference_to_raw"] is None


@pytest.mark.parametrize("indexes",[[1,2,3,4,5],[0,1,3,2,4],[0,1,2,3,3],[False,1,2,3,4]])
def test_explicit_indexes_never_sort_or_relabel(indexes):
    frames=create_stress_scene("counts_change").frames
    with pytest.raises(TelescopeAnalysisError,match="indexes"):
        analyze_telescope_sequence(frames,sequence=manifest(frames),frame_indices=indexes)


def test_no_label_or_disk_access_and_no_native_mutation(monkeypatch):
    frames=create_stress_scene("counts_change").frames; sequence=manifest(frames)
    def forbidden(*args,**kwargs): raise AssertionError("Inference attempted file IO")
    monkeypatch.setattr(builtins,"open",forbidden); monkeypatch.setattr(Path,"open",forbidden)
    result=analyze_telescope_sequence(frames,sequence=sequence)
    assert result.provenance.input_sha256 and result.provenance.config_sha256
    assert_contract(result)


@pytest.mark.parametrize("times",[[10.,11.,12.,13.,14.],[10.,11.,13.,16.,20.]])
def test_actual_seconds_and_irregular_cadence_warning(times):
    frames=create_stress_scene("counts_change").frames
    result=analyze_telescope_sequence(frames,sequence=manifest(frames,times),timestamps=times)
    assert result.time_basis=="second"
    assert all(t.trajectory.speed_unit=="px/s" for t in result.tracks)
    assert all(p.timestamp_s==times[p.frame_index] for t in result.tracks for p in t.points)
    assert any("irregular" in w for w in result.warnings)==(times[-1]!=14.)
    assert_contract(result)


def test_timestamps_must_match_manifest_and_not_be_guessed():
    frames=create_stress_scene("counts_change").frames
    with pytest.raises(TelescopeAnalysisError,match="timestamps"):
        analyze_telescope_sequence(frames,sequence=manifest(frames),timestamps=[0.,1.,2.,3.,4.])


@pytest.mark.parametrize("method",["optimized","baseline"])
def test_selectable_existing_detectors(method):
    frames=create_stress_scene("counts_change").frames
    result=analyze_telescope_sequence(frames,sequence=manifest(frames),method=method)
    assert_contract(result)
    assert result.detections
    expected_name = "opencv_context_filtered_v2" if method == "optimized" else "opencv_compact_dog_v1"
    assert {d.detector_name for d in result.detections} == {expected_name}


@pytest.mark.parametrize("options",[{"method":"yolo"},{"detector_config":{"weights":"secret.pt"}},
    {"config":PipelineConfig(threshold_sigma=5.),"detector_config":{"threshold_sigma":4.5}}])
def test_unverified_models_unknown_config_and_conflicts_rejected(options):
    frames=create_stress_scene("counts_change").frames
    with pytest.raises(TelescopeAnalysisError) as caught:
        analyze_telescope_sequence(frames,sequence=manifest(frames),**options)
    assert caught.value.code=="invalid_configuration"


@pytest.mark.parametrize("kind",["color","nonfinite","dtype","dimensions","count"])
def test_invalid_native_inputs(kind):
    frames=list(create_stress_scene("counts_change").frames); sequence=manifest(frames)
    if kind=="color": frames[0]=np.repeat(frames[0][...,None],3,axis=2)
    if kind=="nonfinite": frames[0]=np.full(frames[0].shape,np.nan)
    if kind=="dtype": frames[0]=frames[0].astype(np.int32)
    if kind=="dimensions": frames[0]=frames[0][:-1]
    if kind=="count": frames=frames[:-1]
    with pytest.raises(TelescopeAnalysisError) as caught:
        analyze_telescope_sequence(frames,sequence=sequence)
    assert caught.value.code=="invalid_input"


@pytest.mark.parametrize("key,expected",[("84","succeeded"),("438","registration_failed")])
def test_requested_real_esa_without_assuming_identities(key,expected):
    source=Path(os.environ.get("CV_TRACK_SOURCE",str(Path(__file__).resolve().parents[2]/"data/raw/SpotGEOv2")))
    if not source.exists(): pytest.skip("Explicit local ESA source unavailable")
    frames=tuple(f.pixels for f in SpotGeoDataset(source).load_sequence(key).frames)
    diagnostic={}
    if expected=="succeeded":
        result=analyze_telescope_sequence(frames,sequence=manifest(frames,source="real"),diagnostics=diagnostic)
        assert_contract(result)
        # Retain the historical CV-T04 regression while checking the stricter
        # image-only profile removes proposals without moving/boosting survivors.
        frozen=analyze_telescope_sequence(frames,sequence=manifest(frames,source="real"),
            detector_config={"min_score":0.,"min_aperture_snr":0.,"max_peak_fraction":.55})
        assert len(frozen.detections)==34 and len(frozen.tracks)==31
        geometry=lambda d: (d.frame_index,d.x_raw_px,d.y_raw_px,d.bbox_raw_px,d.quality_score)
        assert 0 < len(result.detections) < len(frozen.detections)
        assert set(map(geometry,result.detections)) < set(map(geometry,frozen.detections))
        assert not any(t.status=="confirmed" or t.trajectory for t in result.tracks)
    else:
        with pytest.raises(TelescopeAnalysisError) as caught:
            analyze_telescope_sequence(frames,sequence=manifest(frames,source="real"),diagnostics=diagnostic)
        assert caught.value.code=="registration_failed"
        assert [f["frame_index"] for f in diagnostic["registration"]["frames"] if f["status"]=="failed"]==[3,4]


def test_member3_evaluation_uses_declared_reference_synthetic_truth():
    from orbittrace.evaluation.cv_track_diagnostics import evaluate_synthetic_models
    scene=create_stress_scene("counts_change")
    result=analyze_telescope_sequence(scene.frames,sequence=manifest(scene.frames))
    score=evaluate_synthetic_models(result,scene.truth)
    assert score["metrics"]["tp"]==22 and score["metrics"]["fp"]==0 and score["metrics"]["fn"]==0
    assert score["tracking"]["id_switches"]==0 and score["tracking"]["coverage"]==1.
    assert result.metrics is None


def test_member3_esa_evaluation_does_not_compare_reference_points_to_raw_labels():
    from types import SimpleNamespace
    from orbittrace.evaluation.cv_track_diagnostics import evaluate_raw_detection_models
    from app.schemas.result import Detection
    detection=Detection(detection_id="raw-candidate",frame_index=0,x_raw_px=10.,y_raw_px=12.,
        bbox_raw_px=(9.,11.,13.,15.),kind="compact",quality_score=.8,detector_name="actual-test",
        x_reference_px=110.,y_reference_px=112.)
    original=detection.model_dump()
    metric=evaluate_raw_detection_models([detection],[SimpleNamespace(frame_index=0,object_coords=[(10.,12.)])])
    assert metric.tp==1 and metric.fn==0 and metric.localization_rmse_px==0.
    assert detection.model_dump()==original


def test_stationary_stars_and_noise_are_valid_empty_candidates():
    base=create_stress_scene("empty_targets",seed=101).frames[0]
    rng=np.random.default_rng(101)
    frames=tuple(np.rint(np.clip(base.astype(float)+rng.normal(0,.2,base.shape),0,255)).astype(np.uint8) for _ in range(5))
    result=analyze_telescope_sequence(frames,sequence=manifest(frames))
    assert result.registration.status=="estimated"
    assert result.detections==[] and result.tracks==[]
    assert_contract(result)
