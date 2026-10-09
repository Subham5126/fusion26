"""Bounded defaults; planned algorithm thresholds are not validated constants."""
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import Field, model_validator

from app.schemas.base import ContractModel, NonNegative, Profile

ROOT = Path(__file__).resolve().parents[3]


class UploadLimits(ContractModel):
    min_frames: Annotated[int, Field(ge=3, le=30)] = 3
    max_frames: Annotated[int, Field(ge=3, le=30)] = 30
    max_file_mib: Annotated[int, Field(ge=1, le=10)] = 10
    max_total_mib: Annotated[int, Field(ge=1, le=50)] = 50
    max_pixels_per_frame: Annotated[int, Field(ge=1, le=4_000_000)] = 4_000_000

    @model_validator(mode="after")
    def ordered_limits(self):
        if self.min_frames > self.max_frames:
            raise ValueError("min_frames cannot exceed max_frames")
        return self


class PipelineConfig(ContractModel):
    profile: Profile = "synthetic_static_stars"
    threshold_sigma: Annotated[float, Field(gt=0, le=20, allow_inf_nan=False)] = 5.0
    candidate_cap: Annotated[int, Field(ge=1, le=1000)] = 200
    gate_distance_px: Annotated[float, Field(gt=0, le=200, allow_inf_nan=False)] = 20.0
    confirmation_observations: Annotated[int, Field(ge=3, le=30)] = 3
    max_consecutive_misses: Annotated[int, Field(ge=0, le=5)] = 2
    prediction_horizon_frames: Annotated[int, Field(ge=1, le=2)] = 2
    max_active_jobs: Annotated[int, Field(ge=1, le=1)] = 1
    uploads: UploadLimits = Field(default_factory=UploadLimits)


class DemoConfig(ContractModel):
    seed: int = 26
    width_px: Annotated[int, Field(gt=0, le=2000)] = 640
    height_px: Annotated[int, Field(gt=0, le=2000)] = 480
    frames: Annotated[int, Field(ge=3, le=30)] = 12
    targets: Annotated[int, Field(ge=0, le=3)] = 2
    profile: Profile = "synthetic_static_stars"
    star_count: Annotated[int, Field(ge=0, le=1000)] = 100
    read_noise_sigma: NonNegative = 3.0
    background_level: Annotated[float, Field(ge=0, le=255, allow_inf_nan=False)] = 20.0
    hot_pixels: Annotated[int, Field(ge=0, le=100)] = 4
    isolated_flashes: Annotated[int, Field(ge=0, le=100)] = 1
    camera_jitter_px: Annotated[float, Field(ge=0, le=20, allow_inf_nan=False)] = 0.0


def load_pipeline_config(path: Path | None = None) -> PipelineConfig:
    """Local trusted file helper; not an HTTP override or user-path API."""
    with (path or ROOT / "configs/pipeline.yaml").open(encoding="utf-8") as handle:
        return PipelineConfig.model_validate(yaml.safe_load(handle))
