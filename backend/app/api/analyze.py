import json
import uuid
from typing import List

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status, BackgroundTasks

from app.core.config import PipelineConfig
from app.schemas.sequence import SequenceInput
from app.services.job_manager import job_manager

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
async def analyze_demo(background_tasks: BackgroundTasks):
    if not job_manager.can_accept_job():
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Queue capacity exceeded")
    
    frames_count = 5
    width = 64
    height = 48
    
    seq_id = f"demo-{uuid.uuid4().hex}"
    
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
    pixels = generate_target_frames(frames=frames_count, width=width, height=height)
    
    config = PipelineConfig(threshold_sigma=3.0, confirmation_observations=3)
    
    job_state = job_manager.submit_job(sequence, pixels, config, background_tasks)
    return {"job_id": job_state.job_id, "status": job_state.status}


@router.post("/api/analyze/upload", status_code=status.HTTP_202_ACCEPTED)
async def analyze_upload(
    background_tasks: BackgroundTasks,
    manifest: str = Form(...),
    files: List[UploadFile] = File(...)
):
    if not job_manager.can_accept_job():
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Queue capacity exceeded")

    try:
        manifest_data = json.loads(manifest)
        sequence = SequenceInput.model_validate(manifest_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid manifest: {str(e)}")

    if sequence.profile == "synthetic_static_stars":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Untrusted uploads cannot claim the explicitly trusted 'synthetic_static_stars' profile to bypass registration."
        )

    if len(files) != len(sequence.frames):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File count does not match manifest frames")
        
    if len(files) > 30:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Max 30 frames allowed")

    total_size = 0
    frame_pixels = []
    
    # Files must exactly map to sequence.frames in order (contract: "ordered manifest")
    for i, (upload_file, frame_meta) in enumerate(zip(files, sequence.frames)):
        content = await upload_file.read()
        
        file_size = len(content)
        if file_size > 10 * 1024 * 1024:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"File {i} exceeds 10MB limit")
        
        total_size += file_size
        if total_size > 50 * 1024 * 1024:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Total upload exceeds 50MB limit")
            
        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        
        if img is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"File {i} could not be decoded as an image")
            
        h, w = img.shape
        if w != frame_meta.width_px or h != frame_meta.height_px:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
                detail=f"File {i} dimensions {w}x{h} do not match manifest {frame_meta.width_px}x{frame_meta.height_px}"
            )
            
        if w * h > 4_000_000:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"File {i} exceeds 4 megapixels")
            
        frame_pixels.append(img)

    config = PipelineConfig()
    
    try:
        job_state = job_manager.submit_job(sequence, frame_pixels, config, background_tasks)
    except RuntimeError:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Queue capacity exceeded")
        
    return {"job_id": job_state.job_id, "status": job_state.status}
