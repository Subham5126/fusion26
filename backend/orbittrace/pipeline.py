"""Shared future CLI/API entry point. Never fabricate successful analysis."""
from app.core.config import PipelineConfig
from app.schemas.result import AnalysisResult
from app.schemas.sequence import SequenceInput


def analyze(sequence: SequenceInput, config: PipelineConfig) -> AnalysisResult:
    raise NotImplementedError(
        "pipeline_not_implemented: T07 requires image loading/detection T03, "
        "association T04 and trajectory T05. No analysis was performed."
    )
