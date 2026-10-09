from typing import Annotated, Literal

from pydantic import Field

from .base import ContractModel, OpaqueId


class ApiError(ContractModel):
    code: str
    message: str
    details: dict[str, str] | None = None


class JobState(ContractModel):
    job_id: OpaqueId
    status: Literal["queued", "running", "succeeded", "failed"]
    progress_stage: str
    warnings: list[str]
    error: ApiError | None = None
    progress_fraction: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None = None


class ManifestFrame(ContractModel):
    frame_index: Annotated[int, Field(ge=0)]
    timestamp_s: float | None = None
    width_px: int
    height_px: int


class JobManifest(ContractModel):
    job_id: OpaqueId
    frame_count: int
    frames: list[ManifestFrame]
