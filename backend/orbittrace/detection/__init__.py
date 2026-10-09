"""CV-owned bridge to the preserved T03/CV-T04 image-only detectors."""

from .adapter import FrameContext, detect_frame, detect_sequence

__all__ = ["FrameContext", "detect_frame", "detect_sequence"]
