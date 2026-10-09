import cv2
from fastapi import APIRouter, HTTPException, status, Response
from fastapi.responses import JSONResponse

from app.schemas.job import JobState, JobManifest
from app.services.job_manager import job_manager

router = APIRouter()

@router.get("/api/jobs/{job_id}/diagnostics")
def get_job_diagnostics(job_id: str):
    if job_id not in job_manager.jobs:
        raise HTTPException(404, "Job not found or evicted")
    return job_manager.diagnostics[job_id]

@router.get("/api/jobs/{job_id}/exports/{format}")
def export_job(job_id: str, format: str):
    if job_id not in job_manager.jobs:
        raise HTTPException(404, "Job not found or evicted")
    if job_manager.jobs[job_id].status != "succeeded":
        raise HTTPException(409, "No successful result is available")
    result = job_manager.results[job_id]
    if format == "json":
        return JSONResponse(result.model_dump(mode="json"))
    if format != "csv":
        raise HTTPException(404, "Unknown export format")
    import csv
    from io import StringIO
    stream = StringIO()
    writer = csv.writer(stream)
    writer.writerow(["track_id", "frame_index", "point_type", "detection_id", "timestamp_s", "x_reference_px", "y_reference_px", "coordinate_frame", "time_basis"])
    for track in result.tracks:
        for point in track.points + (track.trajectory.predictions if track.trajectory else []):
            writer.writerow([track.track_id, point.frame_index, point.point_type, point.detection_id,
                point.timestamp_s, point.x_reference_px, point.y_reference_px, result.coordinate_frame, result.time_basis])
    return Response(stream.getvalue(), media_type="text/csv")

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
