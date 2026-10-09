"""Strict ESA point-label parser for evaluation/visualization only; no track IDs."""

from dataclasses import dataclass
import json
import math
from types import MappingProxyType
from typing import Mapping

from .archive import DatasetError
from .spotgeo import sequence_key


@dataclass(frozen=True)
class AnnotationFrame:
    sequence_id: str
    original_sequence_id: int | str
    official_frame: int
    object_coords: tuple[tuple[float, float], ...]

    @property
    def frame_index(self) -> int:
        return self.official_frame - 1

    @property
    def num_objects(self) -> int:
        return len(self.object_coords)


@dataclass(frozen=True)
class AnnotationSet:
    """Official raw x/y labels. An array index is not an object identity."""

    frames: Mapping[tuple[str, int], AnnotationFrame]
    width_px: int
    height_px: int
    coordinate_convention: str = "esa_spotgeo_xy_bounds_minus_half_to_size_minus_half"

    def for_sequence(self, sequence_id: int | str) -> tuple[AnnotationFrame, ...]:
        """Require all five explicit entries; missing labels never become empty labels."""
        key = sequence_key(sequence_id)
        try:
            return tuple(self.frames[key, frame] for frame in range(1, 6))
        except KeyError as exc:
            raise DatasetError(f"Missing annotation sequence/frame: {exc.args[0]}") from exc


def _unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise DatasetError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def _bad_constant(value: str) -> None:
    raise DatasetError(f"Non-finite JSON constant: {value}")


def parse_annotations(payload: bytes | str, *, width_px: int = 640, height_px: int = 480,
                      max_bytes: int = 32 * 1024 * 1024,
                      require_complete: bool = True) -> AnnotationSet:
    """Parse UTF-8 train_anno.json/test_anno.json array, preserving official coordinates.

    Numeric, finite (x,y) pairs lie in inclusive [-.5,width-.5] / [-.5,height-.5].
    Strict records have sequence_id, frame (1..5), num_objects (0..30), object_coords.
    All five entries and constant ground-truth counts per sequence are required by
    default. require_complete=False supports inspection of explicitly partial data.
    Empty top-level arrays and explicit zero-object frames are valid. No rounding,
    x/y swap, half-pixel shift, object identity or visibility is inferred.
    """
    if type(width_px) is not int or type(height_px) is not int or min(width_px, height_px) <= 0:
        raise DatasetError("Annotation dimensions must be positive integers")
    if not isinstance(payload, (bytes, str)):
        raise DatasetError("Annotations must be UTF-8 bytes or JSON text")
    if len(payload) > max_bytes:
        raise DatasetError("Annotations exceed byte limit")
    try:
        text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        if len(text.encode("utf-8")) > max_bytes:
            raise DatasetError("Annotations exceed UTF-8 byte limit")
        records = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_bad_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise DatasetError(f"Invalid annotation JSON: {exc}") from exc
    if not isinstance(records, list):
        raise DatasetError("Annotations must be a JSON array")
    frames = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict) or set(record) != {"sequence_id", "frame", "num_objects", "object_coords"}:
            raise DatasetError(f"Record {index}: expected exactly the four ESA fields")
        key = sequence_key(record["sequence_id"])
        frame, count, points = record["frame"], record["num_objects"], record["object_coords"]
        if type(frame) is not int or frame not in range(1, 6):
            raise DatasetError(f"Record {index}: frame must be an integer in 1..5")
        if type(count) is not int or not 0 <= count <= 30 or not isinstance(points, list) or count != len(points):
            raise DatasetError(f"Record {index}: num_objects must match 0..30 coordinate pairs")
        coords = []
        for point in points:
            if not isinstance(point, list) or len(point) != 2:
                raise DatasetError(f"Record {index}: expected [x,y] pair")
            if any(type(value) not in (int, float) for value in point):
                raise DatasetError(f"Record {index}: coordinates must be numbers, not strings/bools")
            try:
                x, y = map(float, point)
            except OverflowError as exc:
                raise DatasetError(f"Record {index}: coordinate exceeds finite float range") from exc
            if not (math.isfinite(x) and math.isfinite(y)):
                raise DatasetError(f"Record {index}: coordinates must be finite")
            if not (-0.5 <= x <= width_px - 0.5 and -0.5 <= y <= height_px - 0.5):
                raise DatasetError(f"Record {index}: coordinates outside official image bounds")
            coords.append((x, y))
        if (key, frame) in frames:
            raise DatasetError(f"Duplicate annotation sequence/frame: {(key, frame)}")
        frames[key, frame] = AnnotationFrame(key, record["sequence_id"], frame, tuple(coords))
    result = AnnotationSet(MappingProxyType(frames), width_px, height_px)
    if require_complete:
        for key in {key for key, _ in frames}:
            sequence = result.for_sequence(key)
            if len({entry.num_objects for entry in sequence}) != 1:
                raise DatasetError(f"Inconsistent ground-truth count in sequence {key}")
    return result
