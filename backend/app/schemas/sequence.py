"""Image metadata only: opaque server references, never paths or labels."""
from typing import Annotated

from pydantic import Field, model_validator

from .base import ContractModel, Finite, OpaqueId, Profile, SourceType, Version


class FrameInput(ContractModel):
    frame_index: Annotated[int, Field(ge=0)]
    image_ref: OpaqueId
    width_px: Annotated[int, Field(gt=0, le=4_000_000)]
    height_px: Annotated[int, Field(gt=0, le=4_000_000)]
    timestamp_s: Finite | None = None

    @model_validator(mode="after")
    def bounded_pixels(self):
        if self.width_px * self.height_px > 4_000_000:
            raise ValueError("Decoded frame exceeds 4 megapixels")
        return self


class SequenceInput(ContractModel):
    schema_version: Version
    sequence_id: OpaqueId
    source_type: SourceType
    profile: Profile
    frames: Annotated[list[FrameInput], Field(min_length=3, max_length=30)]
    dataset_id: OpaqueId | None = None
    dataset_version: str | None = None
    input_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")] | None = None

    @model_validator(mode="after")
    def ordered_frames(self):
        if [f.frame_index for f in self.frames] != list(range(len(self.frames))):
            raise ValueError("Frames must be ordered with contiguous zero-based indexes")
        if len({(f.width_px, f.height_px) for f in self.frames}) != 1:
            raise ValueError("P0 requires equal frame dimensions")
        if len({f.image_ref for f in self.frames}) != len(self.frames):
            raise ValueError("Image references must be unique")
        timestamps = [f.timestamp_s for f in self.frames]
        if any(t is not None for t in timestamps):
            if any(t is None for t in timestamps):
                raise ValueError("Provide all timestamps or leave all unknown")
            if any(b <= a for a, b in zip(timestamps, timestamps[1:])):
                raise ValueError("Timestamps must increase strictly")
        return self
