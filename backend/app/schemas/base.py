"""Shared strict JSON primitives; all coordinates and metrics must be finite."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "0.1.0"
Version = Literal["0.1.0"]
OpaqueId = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$")]
Finite = Annotated[float, Field(allow_inf_nan=False)]
NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Quality = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
SourceType = Literal["synthetic", "real", "user_upload"]
Profile = Literal["synthetic_static_stars", "ground_static_star_streaks", "spotgeo"]
TimeBasis = Literal["frame", "second"]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
