import asyncio
import uuid
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from app.core.config import PipelineConfig
from app.core.deployment import public_mode, frame_retention_bytes
from app.schemas.job import JobState, ApiError, JobManifest, ManifestFrame
from app.schemas.result import AnalysisResult
from app.schemas.sequence import SequenceInput
from orbittrace.pipeline import analyze
from orbittrace.cv_tracking import TelescopeAnalysisError


class JobManager:
    def __init__(self, max_concurrent=1):
        self.max_concurrent = max_concurrent
        self.max_frame_bytes = frame_retention_bytes()
        self.jobs: Dict[str, JobState] = {}
        self.results: Dict[str, AnalysisResult] = {}
        self.frames: Dict[str, list] = {}
        self.manifests: Dict[str, JobManifest] = {}
        self.diagnostics: Dict[str, dict] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self.active_count = 0
        self.lock = threading.RLock()

    def generate_id(self, prefix="job") -> str:
        return f"{prefix}-{uuid.uuid4().hex}"

    def can_accept_job(self) -> bool:
        with self.lock:
            queued_or_running = sum(1 for j in self.jobs.values() if j.status in ("queued", "running"))
            return queued_or_running < self.max_concurrent

    def submit_job(self, sequence: SequenceInput, frame_pixels: list, config: PipelineConfig, background_tasks=None) -> JobState:
        incoming_bytes = sum(f.nbytes for f in frame_pixels)
        with self.lock:
            if not self.can_accept_job():
                raise RuntimeError("Capacity exceeded")

            # Evict completed jobs to enforce the deployment's decoded-frame memory budget.
            MAX_JOBS = 100
            MAX_BYTES = self.max_frame_bytes

            while len(self.jobs) >= MAX_JOBS or incoming_bytes + sum(f.nbytes for frames in self.frames.values() for f in frames) > MAX_BYTES:
                completed = [k for k, v in self.jobs.items() if v.status in ("succeeded", "failed")]
                if not completed:
                    raise RuntimeError("Memory capacity exceeded")
                oldest = completed[0]
                self.jobs.pop(oldest, None)
                self.results.pop(oldest, None)
                self.frames.pop(oldest, None)
                self.manifests.pop(oldest, None)
                self.diagnostics.pop(oldest, None)

            return self._reserve_job(sequence, frame_pixels, config, background_tasks)

    def _reserve_job(self, sequence, frame_pixels, config, background_tasks):
        job_id = self.generate_id()
        self.frames[job_id] = frame_pixels
        self.diagnostics[job_id] = {}
        self.manifests[job_id] = JobManifest(
            job_id=job_id,
            frame_count=len(sequence.frames),
            frames=[
                ManifestFrame(
                    frame_index=f.frame_index,
                    timestamp_s=f.timestamp_s,
                    width_px=f.width_px,
                    height_px=f.height_px
                ) for f in sequence.frames
            ]
        )
        job_state = JobState(
            job_id=job_id,
            status="queued",
            progress_stage="queued",
            warnings=[],
            error=None,
            progress_fraction=0.0
        )
        self.jobs[job_id] = job_state

        if background_tasks is not None:
            background_tasks.add_task(self._run_job, job_id, sequence, frame_pixels, config)
        else:
            asyncio.create_task(self._run_job(job_id, sequence, frame_pixels, config))
        return job_state

    async def _run_job(self, job_id: str, sequence: SequenceInput, frame_pixels: list, config: PipelineConfig):
        job = self.jobs[job_id]
        job.status = "running"
        job.progress_stage = "processing"

        import functools
        loop = asyncio.get_running_loop()
        try:
            # Run the heavy numpy pipeline in a thread pool
            result = await loop.run_in_executor(
                self.executor,
                functools.partial(analyze, sequence, config, frame_pixels=frame_pixels,
                                  diagnostics=self.diagnostics[job_id])
            )
            # Override job_id in result to match the API assigned one
            result.job_id = job_id
            self.results[job_id] = result
            job.status = "succeeded"
            job.progress_stage = "completed"
            job.progress_fraction = 1.0
        except TelescopeAnalysisError as e:
            job.status = "failed"
            job.progress_stage = e.code
            job.error = e.error
            job.progress_fraction = None
        except Exception as e:
            job.status = "failed"
            job.progress_stage = "failed"
            # Extract only the class and message, no traceback in UI per contract
            job.error = ApiError(
                code="pipeline_error",
                message="Analysis could not be completed. Retry with supported telescope images." if public_mode() else f"{type(e).__name__}: {str(e)}",
                details=None
            )

job_manager = JobManager()
