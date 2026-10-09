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
