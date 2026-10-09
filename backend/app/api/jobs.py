from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas.job import JobState
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
