"""Five-frame ESA layout adapter; never reads annotations during image loading."""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re

import numpy as np

from astrotrace.preprocessing.images import decode_png
from .archive import ArchiveLimits, DatasetError, open_safe_zip, read_member, safe_member_name


def sequence_key(value: int | str) -> str:
    """Canonical positive decimal folder ID; preserve original label ID separately."""
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise DatasetError("sequence_id must be a positive integer or canonical decimal string")
    key = str(value)
    if not re.fullmatch(r"[1-9][0-9]{0,18}", key):
        raise DatasetError("sequence_id must be a positive canonical decimal ID")
    return key


@dataclass(frozen=True)
class Frame:
    frame_index: int
    official_frame: int
    pixels: np.ndarray
    timestamp_s: None = None

    @property
    def width_px(self) -> int:
        return self.pixels.shape[1]

    @property
    def height_px(self) -> int:
        return self.pixels.shape[0]


@dataclass(frozen=True)
class Sequence:
    """Internal image-only record, not public SequenceInput; no paths or labels."""

    sequence_id: str
    split: str
    frames: tuple[Frame, ...]
    coordinate_frame: str = "raw"
    coordinate_convention: str = "integer_pixel_centers_top_left_xy"


class SpotGeoDataset:
    """Read train|test/<positive sequence ID>/1.png .. 5.png from local directory/ZIP.

    For a directory, source points at the parent of train/test. For a ZIP, one
    optional wrapper folder is discovered by suffix, or supply prefix explicitly.
    No full extraction, remote fetching, resizing, color conversion or timestamps.
    All five frames must have equal dimensions; ESA defaults require 640x480.
    """

    def __init__(self, source: str | Path, *, split: str = "train", prefix: str | None = None,
                 expected_size: tuple[int, int] | None = (640, 480),
                 max_pixels: int = 4_000_000, max_image_bytes: int = 16 * 1024 * 1024,
                 archive_limits: ArchiveLimits = ArchiveLimits()):
        if split not in ("train", "test"):
            raise DatasetError("split must be train or test")
        self.source = Path(source).resolve()
        self.split, self.expected_size = split, expected_size
        self.max_pixels, self.max_image_bytes = max_pixels, max_image_bytes
        self.archive_limits = archive_limits
        self.is_zip = self.source.is_file()
        self.prefix = ""
        self._frames: dict[str, dict[int, str]] = {}
        if self.is_zip:
            with open_safe_zip(self.source, archive_limits) as archive:
                names = [m.filename for m in archive.infolist() if not m.is_dir()]
            candidates = set()
            for name in names:
                parts = PurePosixPath(name).parts
                if len(parts) >= 3 and parts[-3] == split and re.fullmatch(r"[1-9][0-9]*", parts[-2]):
                    candidates.add("/".join(parts[:-3]))
            if prefix is None:
                if len(candidates) != 1:
                    raise DatasetError("Missing or ambiguous dataset ZIP prefix; supply prefix explicitly")
                self.prefix = candidates.pop()
            else:
                self.prefix = safe_member_name(prefix) if prefix else ""
            base = f"{self.prefix}/{split}/" if self.prefix else f"{split}/"
            for name in names:
                if not name.startswith(base):
                    continue
                parts = name[len(base):].split("/")
                if len(parts) == 2 and parts[1].lower().endswith(".png"):
                    self._add_frame(parts[0], parts[1], name)
        elif self.source.is_dir():
            if prefix is not None:
                raise DatasetError("prefix is a ZIP option; directory source must contain train/test")
            folder = self._local_path(split)
            if not folder.is_dir():
                raise DatasetError(f"Missing split directory: {split}")
            for sequence_dir in sorted(folder.iterdir()):
                if sequence_dir.is_dir():
                    sequence_key(sequence_dir.name)
                    self._local_path(f"{split}/{sequence_dir.name}")
                    for image in sequence_dir.iterdir():
                        if image.suffix.lower() == ".png":
                            name = f"{split}/{sequence_dir.name}/{image.name}"
                            self._local_path(name)
                            self._add_frame(sequence_dir.name, image.name, name)
                    if sequence_dir.name not in self._frames:
                        raise DatasetError(f"Empty sequence directory: {sequence_dir.name}")
        else:
            raise DatasetError("Dataset source must be an existing local directory or ZIP")
        if not self._frames:
            raise DatasetError("No five-frame PNG sequences found")
        for key, frames in self._frames.items():
            if set(frames) != {1, 2, 3, 4, 5}:
                raise DatasetError(f"Sequence {key} must contain exactly frames 1..5")

    def _add_frame(self, key: str, filename: str, name: str) -> None:
        key = sequence_key(key)
        if filename not in {f"{i}.png" for i in range(1, 6)}:
            raise DatasetError(f"Unsupported frame filename: {name}")
        official_frame = int(filename[0])
        frames = self._frames.setdefault(key, {})
        if official_frame in frames:
            raise DatasetError(f"Duplicate frame: {name}")
        frames[official_frame] = name

    def _local_path(self, name: str) -> Path:
        safe_member_name(name)
        path = self.source / name
        # Reject symlinks anywhere below the explicitly selected source root.
        current = self.source
        for part in PurePosixPath(name).parts:
            current = current / part
            if current.is_symlink():
                raise DatasetError(f"Dataset symlink is unsupported: {name}")
        if not path.resolve().is_relative_to(self.source):
            raise DatasetError("Dataset path escapes source root")
        return path

    @property
    def sequence_ids(self) -> tuple[str, ...]:
        """Numeric ordering, never lexicographic frame guessing."""
        return tuple(sorted(self._frames, key=int))

    def read_file(self, relative_name: str, *, max_bytes: int) -> bytes:
        """Explicit bounded local read, used separately by annotation exploration."""
        name = safe_member_name(relative_name)
        if self.is_zip:
            name = f"{self.prefix}/{name}" if self.prefix else name
            with open_safe_zip(self.source, self.archive_limits) as archive:
                return read_member(archive, name, max_bytes)
        path = self._local_path(name)
        try:
            if path.stat().st_size > max_bytes:
                raise DatasetError(f"File exceeds byte limit: {name}")
            with path.open("rb") as stream:
                payload = stream.read(max_bytes + 1)
            if len(payload) > max_bytes:
                raise DatasetError(f"File exceeds read limit: {name}")
            return payload
        except OSError as exc:
            raise DatasetError(f"Cannot read {name}: {exc}") from exc

    def load_sequence(self, sequence_id: str | int) -> Sequence:
        """Decode only the selected five images, never any *_anno.json file."""
        key = sequence_key(sequence_id)
        if key not in self._frames:
            raise DatasetError(f"Unknown sequence: {key}")
        frames = []

        def append_frame(official_frame: int, payload: bytes) -> None:
            try:
                pixels = decode_png(payload, max_pixels=self.max_pixels, expected_size=self.expected_size)
            except ValueError as exc:
                raise DatasetError(f"Sequence {key}, frame {official_frame}: {exc}") from exc
            if frames and pixels.shape != frames[0].pixels.shape:
                raise DatasetError("Sequence frame dimensions differ")
            frames.append(Frame(official_frame - 1, official_frame, pixels))

        if self.is_zip:
            with open_safe_zip(self.source, self.archive_limits) as archive:
                for official_frame in range(1, 6):
                    append_frame(official_frame, read_member(
                        archive, self._frames[key][official_frame], self.max_image_bytes))
        else:
            for official_frame in range(1, 6):
                append_frame(official_frame, self.read_file(
                    self._frames[key][official_frame], max_bytes=self.max_image_bytes))
        return Sequence(key, self.split, tuple(frames))
