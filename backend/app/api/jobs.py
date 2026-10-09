import cv2
from fastapi import APIRouter, HTTPException, status, Response
from fastapi.responses import JSONResponse

from app.schemas.job import JobState, JobManifest
from app.services.job_manager import job_manager

router = APIRouter()

@router.get("/api/jobs/{job_id}", response_model=JobState)
def get_job_state(job_id: str):
    if job_id not in job_manager.jobs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job_manager.jobs[job_id]


@router.get("/api/jobs/{job_id}/result")
def get_job_result(job_id: str):
    if job_id not in job_manager.jobs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job = job_manager.jobs[job_id]
    if job.status != "succeeded":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is currently {job.status}. Results are only available for succeeded jobs."
        )

    if job_id not in job_manager.results:
        # Should not happen if status is succeeded
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result missing")

    # Model dump for exact response
    result_data = job_manager.results[job_id].model_dump(exclude_none=False)
    # Re-insert the exact null semantics for Javascript compatibility
    return JSONResponse(content=result_data)


@router.get("/api/jobs/{job_id}/frames/{frame_index}")
def get_job_frame(job_id: str, frame_index: int):
    if job_id not in job_manager.frames:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "not_found", "message": "Job not found or frames evicted", "details": None}}
        )

    frames = job_manager.frames[job_id]
    if frame_index < 0 or frame_index >= len(frames):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "not_found", "message": "Frame index out of bounds", "details": None}}
        )

    frame_pixels = frames[frame_index]
    success, encoded = cv2.imencode('.png', frame_pixels)
    if not success:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": "server_error", "message": "Failed to encode frame", "details": None}}
        )

    return Response(content=encoded.tobytes(), media_type="image/png")


@router.get("/api/jobs/{job_id}/manifest", response_model=JobManifest)
def get_job_manifest(job_id: str):
    if job_id not in job_manager.manifests:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found or evicted")
    return job_manager.manifests[job_id]
