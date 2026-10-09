from typing import Literal

from .base import ContractModel, Version


class Capabilities(ContractModel):
    schemas: bool = True
    synthetic_generation: bool = False
    detection: bool = False
    tracking: bool = False
    trajectory: bool = False
    evaluation: bool = False
    analysis_api: bool = False
    uploads: bool = False
    exports: bool = False


class HealthResponse(ContractModel):
    status: Literal["ok"] = "ok"
    service: Literal["OrbitTrace"] = "OrbitTrace"
    readiness: Literal["bootstrap_only"] = "bootstrap_only"
    schema_version: Version = "0.1.0"
    capabilities: Capabilities = Capabilities()
