import io
import json
import uuid
import time
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.result import AnalysisResult

client = TestClient(app)

def generate_target_frames(frames=5, width=64, height=48):
    yy, xx = np.mgrid[:height, :width]
    images = []
    for i in range(frames):
        image = np.full(xx.shape, 20.0, dtype=np.float64)
        image += 80 * np.exp(-((xx - (10 + i * 5)) ** 2 + (yy - 20) ** 2) / (2 * 1.5 ** 2))
        pixels = np.rint(np.clip(image, 0, 255)).astype(np.uint8)
        images.append(pixels)
    return images

def test_health_capabilities():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["readiness"] == "bootstrap_only"
    caps = data["capabilities"]
    assert caps["analysis_api"] is True
    assert caps["synthetic_generation"] is True
    assert caps["evaluation"] is False

def test_demo_endpoint_and_job_lifecycle():
    # 1. Start demo
    response = client.post("/api/analyze/demo")
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # 2. Poll job until success
    max_retries = 50
    succeeded = False
    for _ in range(max_retries):
        status_resp = client.get(f"/api/jobs/{job_id}")
        assert status_resp.status_code == 200
        state = status_resp.json()
        if state["status"] == "succeeded":
            succeeded = True
            break
        elif state["status"] == "failed":
            pytest.fail(f"Job failed: {state.get('error')}")
        time.sleep(0.1)

    assert succeeded, "Job did not complete in time"

    # 3. Get result
    result_resp = client.get(f"/api/jobs/{job_id}/result")
    assert result_resp.status_code == 200
    result_data = result_resp.json()

    # Validate via pydantic
    AnalysisResult.model_validate(result_data)
    assert result_data["status"] == "succeeded"
    assert result_data["registration"]["status"] == "not_required"

def test_upload_spoofed_synthetic_profile_rejected():
    frames = generate_target_frames(3)
    files = []
    for i, frame in enumerate(frames):
        success, encoded = cv2.imencode('.png', frame)
        files.append(("files", (f"frame_{i}.png", encoded.tobytes(), "image/png")))

    manifest = {
        "schema_version": "0.1.0",
        "sequence_id": "test_upload",
        "source_type": "user_upload",
        "profile": "synthetic_static_stars",
        "frames": [
            {
                "frame_index": i,
                "image_ref": f"frame_{i}",
                "width_px": 64,
                "height_px": 48
            } for i in range(3)
        ]
    }

    response = client.post(
        "/api/analyze/upload",
        data={"manifest": json.dumps(manifest)},
        files=files
    )
    assert response.status_code == 422

def test_upload_invalid_registration():
    frames = generate_target_frames(3)
    files = []
    for i, frame in enumerate(frames):
        success, encoded = cv2.imencode('.png', frame)
        files.append(("files", (f"frame_{i}.png", encoded.tobytes(), "image/png")))

    manifest = {
        "schema_version": "0.1.0",
        "sequence_id": "test_spotgeo",
        "source_type": "user_upload",
        "profile": "spotgeo",  # Trigger error
        "frames": [
            {
                "frame_index": i,
                "image_ref": f"frame_{i}",
                "width_px": 64,
                "height_px": 48
            } for i in range(3)
        ]
    }

    response = client.post(
        "/api/analyze/upload",
        data={"manifest": json.dumps(manifest)},
        files=files
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Wait for completion
    for _ in range(30):
        resp = client.get(f"/api/jobs/{job_id}")
        if resp.json()["status"] in ["succeeded", "failed"]:
            break
        time.sleep(0.1)

    state = resp.json()
    assert state["status"] == "failed"
    assert state["error"]["code"] == "pipeline_error"
    assert "Registration (T13) not implemented" in state["error"]["message"]

def test_upload_invalid_file_count():
    files = [("files", ("dummy.png", b"bad", "image/png"))]
    manifest = {
        "schema_version": "0.1.0",
        "sequence_id": "bad_count",
        "source_type": "user_upload",
        "profile": "synthetic_static_stars",
        "frames": [{"frame_index": 0, "image_ref": "frame_0", "width_px": 64, "height_px": 48}]
        # But wait, sequence needs min 3 frames, so manifest itself will fail!
    }

    response = client.post(
        "/api/analyze/upload",
        data={"manifest": json.dumps(manifest)},
        files=files
    )
    assert response.status_code == 422

def test_job_not_found():
    response = client.get("/api/jobs/missing_job")
    assert response.status_code == 404

def test_job_frame_retrieval_and_errors():
    # Submit demo to get a job id and generate frames
    response = client.post("/api/analyze/demo")
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Wait for completion
    for _ in range(30):
        resp = client.get(f"/api/jobs/{job_id}")
        if resp.json()["status"] in ["succeeded", "failed"]:
            break
        time.sleep(0.1)

    assert resp.json()["status"] == "succeeded"

    # Test valid frame
    frame_resp = client.get(f"/api/jobs/{job_id}/frames/0")
    assert frame_resp.status_code == 200
    assert frame_resp.headers["content-type"] == "image/png"

    # Test valid frame index 4
    frame_resp_4 = client.get(f"/api/jobs/{job_id}/frames/4")
    assert frame_resp_4.status_code == 200

    # Test invalid frame index bounds (demo creates 5 frames, index 5 is OOB)
    frame_resp_oob = client.get(f"/api/jobs/{job_id}/frames/5")
    assert frame_resp_oob.status_code == 404

    frame_resp_neg = client.get(f"/api/jobs/{job_id}/frames/-1")
    assert frame_resp_neg.status_code == 404

    # Test invalid job id
    frame_resp_missing = client.get("/api/jobs/missing_job/frames/0")
    assert frame_resp_missing.status_code == 404

def test_manifest_endpoint():
    # Submit demo to get a job id
    response = client.post("/api/analyze/demo")
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Test valid manifest
    manifest_resp = client.get(f"/api/jobs/{job_id}/manifest")
    assert manifest_resp.status_code == 200
    manifest = manifest_resp.json()

    assert manifest["job_id"] == job_id
    assert manifest["frame_count"] == 5
    assert len(manifest["frames"]) == 5

    for i, frame in enumerate(manifest["frames"]):
        assert frame["frame_index"] == i
        assert frame["width_px"] == 64
        assert frame["height_px"] == 48
        assert frame["timestamp_s"] == float(i)

    # Test missing job manifest
    missing_manifest_resp = client.get("/api/jobs/missing_job/manifest")
    assert missing_manifest_resp.status_code == 404
