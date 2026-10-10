import hashlib
import json
import uuid
from typing import List, Literal

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status, BackgroundTasks

from app.core.config import PipelineConfig
from app.core.deployment import public_mode
from app.core.upload import read_bounded_file, decode_upload, TOTAL_BYTES
from app.schemas.sequence import SequenceInput
from app.services.job_manager import job_manager
from orbittrace.demo_scenes import generate_demo_preset

router = APIRouter()

def generate_target_frames(frames=5, width=64, height=48):
    yy, xx = np.mgrid[:height, :width]
    images = []
    for i in range(frames):
        image = np.full(xx.shape, 20.0, dtype=np.float64)
        image += 80 * np.exp(-((xx - (10 + i * 5)) ** 2 + (yy - 20) ** 2) / (2 * 1.5 ** 2))
        pixels = np.rint(np.clip(image, 0, 255)).astype(np.uint8)
        images.append(pixels)
    return images

@router.post("/api/analyze/demo", status_code=status.HTTP_202_ACCEPTED)
async def analyze_demo(background_tasks: BackgroundTasks, preset: Literal['1', '2', '3', '4'] | None = None):
    if not job_manager.can_accept_job():
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Queue capacity exceeded")
    
    frames_count = 5
    width = 640 if preset else 64
    height = 480 if preset else 48
    
    seq_id = f"demo-{preset or 'legacy'}-{uuid.uuid4().hex}"
    
    sequence_data = {
        "schema_version": "0.1.0",
        "sequence_id": seq_id,
        "source_type": "synthetic",
        "profile": "synthetic_static_stars",
        "frames": [
            {
                "frame_index": i,
                "image_ref": f"frame_{i}",
                "width_px": width,
                "height_px": height,
                "timestamp_s": float(i)
            }
            for i in range(frames_count)
        ]
    }
    
    sequence = SequenceInput.model_validate(sequence_data)
    pixels = generate_demo_preset(preset) if preset else generate_target_frames(frames=frames_count, width=width, height=height)
    
    config = PipelineConfig(threshold_sigma=3.0, confirmation_observations=3)
    
    try:
        job_state = job_manager.submit_job(sequence, pixels, config, background_tasks)
    except RuntimeError:
        raise HTTPException(429, "Queue capacity exceeded")
    return {"job_id": job_state.job_id, "status": job_state.status}


@router.post("/api/analyze/upload", status_code=status.HTTP_202_ACCEPTED)
async def analyze_upload(
    background_tasks: BackgroundTasks,
    manifest: str = Form(...),
    files: List[UploadFile] = File(...),
    analysis_mode: Literal['standard', 'temporal'] = Form('standard'),
):
    if not job_manager.can_accept_job():
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Queue capacity exceeded")

    try:
        manifest_data = json.loads(manifest)
        sequence = SequenceInput.model_validate(manifest_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid manifest: request does not match the sequence contract" if public_mode() else f"Invalid manifest: {str(e)}")

    if sequence.profile == "synthetic_static_stars":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Untrusted uploads cannot claim the explicitly trusted 'synthetic_static_stars' profile to bypass registration."
        )

    if len(files) != len(sequence.frames):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File count does not match manifest frames")
        
    if len(files) != 5 or sequence.source_type != "user_upload":
        raise HTTPException(422, "Exactly five ordered user_upload telescope frames are required")
    total_size = 0
    frame_pixels = []
    encoded_hash = hashlib.sha256()
    try:
        for upload_file, frame_meta in zip(files, sequence.frames):
            content = await read_bounded_file(upload_file, TOTAL_BYTES - total_size)
            total_size += len(content)
            encoded_hash.update(content)
            frame_pixels.append(decode_upload(content, upload_file, frame_meta))
    finally:
        for upload_file in files:
            await upload_file.close()
    sequence = sequence.model_copy(update={"input_sha256": encoded_hash.hexdigest()})

    # Explicit opt-in: preserve existing clients and the frozen single-frame path.
    config = PipelineConfig(analysis_mode=analysis_mode,
                            gate_distance_px=25.0 if analysis_mode == 'temporal' else 20.0)
    
    try:
        job_state = job_manager.submit_job(sequence, frame_pixels, config, background_tasks)
    except RuntimeError:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Queue capacity exceeded")
        
    return {"job_id": job_state.job_id, "status": job_state.status}
