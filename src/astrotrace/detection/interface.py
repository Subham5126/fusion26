"""Image-only detector boundary consuming the existing integration-owned Detection."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Mapping, Protocol

import numpy as np

if TYPE_CHECKING:
    from app.schemas.result import Detection


@dataclass(frozen=True)
class FrameContext:
    """Native raw pixel frame metadata; unknown timestamps remain None."""

    frame_index: int
    width_px: int
    height_px: int
    profile: Literal["synthetic_static_stars", "ground_static_star_streaks", "spotgeo"]
    timestamp_s: float | None = None


class Detector(Protocol):
    """Proposed pure CPU interface, no annotations, file paths, HTTP or tracking.

    Input: 2D native grayscale array + image-only context + declared config.
    Output: existing app.schemas.result.Detection objects under contract 0.1.0.
    No targets returns []; invalid input raises ValueError. quality_score is a
    heuristic [0,1]. Raw centroid is inside a positive exclusive-upper bbox.
    Reference coordinates remain None until image-derived registration exists.
    This protocol implements no detection and returns no fabricated proposals.
    """

    def detect(self, pixels: np.ndarray, context: FrameContext,
               config: Mapping[str, object]) -> list["Detection"]:
        ...
