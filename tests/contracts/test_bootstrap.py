"""T01 evidence: bounds, truth separation, observation semantics and readiness."""
import json
from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError
import yaml

from app.core.config import DemoConfig, PipelineConfig, load_pipeline_config
from app.main import app
from app.schemas.result import AnalysisResult
from app.schemas.sequence import SequenceInput
from orbittrace.pipeline import analyze

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_authored_result_fixtures_roundtrip():
    for name in ("empty-result.json", "track-result.json"):
        model = AnalysisResult.model_validate(fixture(name))
        assert AnalysisResult.model_validate_json(model.model_dump_json()) == model
        assert model.metrics is None and model.runtime_ms is None


@pytest.mark.parametrize("mutation", [
    lambda s: s.update(ground_truth="data/ground_truth/truth.json"),
    lambda s: s["frames"][0].update(image_ref="../ground_truth/truth.json"),
    lambda s: s["frames"][0].update(image_ref="https://example.com/image.png"),
    lambda s: s["frames"][0].update(frame_index=2),
    lambda s: s["frames"][0].update(width_px=4_000_000),
    lambda s: s["frames"][1].update(width_px=65),
    lambda s: s["frames"][0].update(timestamp_s=1.0),
    lambda s: [frame.update(timestamp_s=1.0) for frame in s["frames"]],
    lambda s: s["frames"][0].update(timestamp_s=float("nan")),
    lambda s: s.update(frames=s["frames"][:2]),
])
def test_invalid_or_truth_bearing_inputs_rejected(mutation):
    sequence = fixture("sequence.json")
    mutation(sequence)
    with pytest.raises(ValidationError):
        SequenceInput.model_validate(sequence)


def test_known_seconds_and_unknown_frame_timing():
    sequence = fixture("sequence.json")
    assert all(f.timestamp_s is None for f in SequenceInput.model_validate(sequence).frames)
    for i, frame in enumerate(sequence["frames"]):
        frame["timestamp_s"] = i * 0.5
    assert SequenceInput.model_validate(sequence).frames[-1].timestamp_s == 1.0


@pytest.mark.parametrize("mutation", [
    lambda r: r["tracks"][0].update(observed_count=4),
    lambda r: r["tracks"][0]["trajectory"]["predictions"][0].update(detection_id="d0"),
    lambda r: r["tracks"][0]["trajectory"].update(speed_unit="px/s"),
    lambda r: r["tracks"][0]["points"][0].update(detection_id="nonexistent"),
    lambda r: r["detections"][0].update(x_raw_px=float("inf")),
    lambda r: r["detections"][0].update(bbox_raw_px=[11, 11, 9, 9]),
    lambda r: r["tracks"][0]["trajectory"].update(coordinate_frame="wrong_frame"),
])
def test_invalid_scientific_output_rejected(mutation):
    result = fixture("track-result.json")
    mutation(result)
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(result)


def test_confirmed_track_requires_three_real_observations():
    result = fixture("track-result.json")
    track = result["tracks"][0]
    track["points"] = track["points"][:2]
    track["observed_count"] = 2
    track["trajectory"] = None
    with pytest.raises(ValidationError, match="three observations"):
        AnalysisResult.model_validate(result)


def test_config_bounds_and_yaml():
    config = load_pipeline_config()
    assert config.max_active_jobs == 1
    DemoConfig.model_validate(yaml.safe_load((ROOT / "configs/demo.yaml").read_text()))
    for override in ({"confirmation_observations": 2}, {"max_active_jobs": 2},
                     {"prediction_horizon_frames": 3}, {"threshold_sigma": float("nan")},
                     {"truth_path": "data/ground_truth"},
                     {"uploads": {"min_frames": 20, "max_frames": 10}}):
        with pytest.raises(ValidationError):
            PipelineConfig.model_validate(override)


def test_health_and_reserved_routes_are_honest():
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        body = health.json()
        assert body["readiness"] == "bootstrap_only"
        assert body["schema_version"] == "0.1.0"
        assert body["capabilities"].pop("schemas") is True
        assert body["capabilities"]["analysis_api"] is True
        assert body["capabilities"]["detection"] is True
        for method, path in (("get", "/api/demos"), ("get", "/api/jobs/example-job/result")):
            response = getattr(client, method)(path)
            assert response.status_code == 404
        # We removed the /api/analyze/demo and /api/analyze/upload from the 404 test
        # because they are now implemented!


def test_pipeline_fails_explicitly_without_output():
    with pytest.raises(NotImplementedError, match="T07"):
        analyze(SequenceInput.model_validate(fixture("sequence.json")), PipelineConfig())


@pytest.mark.parametrize("script", ["generate_demo.py", "analyze_sequence.py", "evaluate.py"])
def test_cli_help_and_pending_failure(script):
    path = ROOT / "scripts" / script
    help_run = subprocess.run([sys.executable, str(path), "--help"], capture_output=True, text=True)
    assert help_run.returncode == 0 and "pending implementation" in " ".join(help_run.stdout.split())
    pending_run = subprocess.run([sys.executable, str(path)], capture_output=True, text=True)
    assert pending_run.returncode == 2 and "not_implemented" in pending_run.stderr
