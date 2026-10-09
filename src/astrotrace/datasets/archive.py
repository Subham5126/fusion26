"""Bounded, local ZIP inventory. Never extracts or opens member payloads to inspect."""

from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import zlib
from zipfile import BadZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile


class DatasetError(ValueError):
    """Invalid, unsupported or unsafe dataset input."""


@dataclass(frozen=True)
class ArchiveLimits:
    """Local exploration limits, unrelated to the future HTTP upload service."""

    max_entries: int = 100_000
    max_central_directory_bytes: int = 32 * 1024 * 1024
    max_member_bytes: int = 64 * 1024 * 1024
    max_total_uncompressed_bytes: int = 16 * 1024**3
    max_compression_ratio: float = 1000.0


@dataclass(frozen=True)
class ArchiveEntry:
    name: str
    size_bytes: int
    compressed_bytes: int
    kind: str


@dataclass(frozen=True)
class ArchiveInventory:
    entries: tuple[ArchiveEntry, ...]
    total_uncompressed_bytes: int

    def to_dict(self) -> dict:
        """JSON-safe inventory including images, annotations and other members."""
        return asdict(self)


def safe_member_name(name: str) -> str:
    """Require portable relative ZIP names; reject traversal and Windows aliases."""
    if not name or "\\" in name or name.startswith("/") or "\x00" in name:
        raise DatasetError(f"Unsafe archive member: {name!r}")
    parts = name.rstrip("/").split("/")
    reserved = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)", re.I)
    if any(not p or p in (".", "..") or p.endswith((".", " "))
           or any(c in p for c in ':<>"|?*') or any(ord(c) < 32 for c in p)
           or reserved.match(p) for p in parts):
        raise DatasetError(f"Unsafe archive member: {name!r}")
    return "/".join(parts)


def _preflight(path: Path, limits: ArchiveLimits) -> None:
    """Bound directory allocation before ZipFile parses it; support single-disk ZIP64."""
    with path.open("rb") as stream:
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(max(0, size - 65_557))
        tail = stream.read(65_557)
        offset = tail.rfind(b"PK\x05\x06")
        if offset < 0 or len(tail) - offset < 22:
            raise DatasetError("Missing ZIP end-of-central-directory record")
        fields = struct.unpack_from("<4s4H2LH", tail, offset)
        _, disk, cd_disk, disk_count, count, cd_size, cd_offset, comment_len = fields
        if offset + 22 + comment_len != len(tail):
            raise DatasetError("Invalid ZIP end record or trailing data")
        if disk or cd_disk or disk_count != count:
            raise DatasetError("Multi-disk ZIPs are unsupported")
        eocd_offset = size - len(tail) + offset
        if count == 0xFFFF or cd_size == 0xFFFFFFFF or cd_offset == 0xFFFFFFFF:
            if eocd_offset < 20:
                raise DatasetError("Missing ZIP64 locator")
            stream.seek(eocd_offset - 20)
            locator = stream.read(20)
            signature, locator_disk, zip64_offset, disks = struct.unpack("<4sLQL", locator)
            if signature != b"PK\x06\x07" or locator_disk or disks != 1:
                raise DatasetError("Invalid or multi-disk ZIP64 locator")
            stream.seek(zip64_offset)
            record = stream.read(56)
            if len(record) != 56:
                raise DatasetError("Truncated ZIP64 record")
            fields64 = struct.unpack("<4sQ2H2L4Q", record)
            sig, record_len, _, _, disk, cd_disk, disk_count, count, cd_size, cd_offset = fields64
            if sig != b"PK\x06\x06" or record_len != 44 or disk or cd_disk or disk_count != count:
                raise DatasetError("Unsupported ZIP64 end record")
        if count > limits.max_entries or cd_size > limits.max_central_directory_bytes:
            raise DatasetError("ZIP central directory exceeds inspection limits")
        if cd_offset + cd_size > eocd_offset:
            raise DatasetError("ZIP central directory lies outside archive")


def inventory_open_zip(archive: ZipFile, limits: ArchiveLimits) -> ArchiveInventory:
    """Validate central metadata only. Payload CRC is checked later on bounded reads."""
    entries = []
    seen = set()
    total = 0
    for member in archive.infolist():
        # ZipInfo normalizes Windows backslashes and truncates NUL on reading.
        # Validate the original central-directory spelling before normalization.
        name = safe_member_name(member.orig_filename)
        canonical = name.casefold()
        if canonical in seen:
            raise DatasetError(f"Duplicate or case-aliased member: {name}")
        seen.add(canonical)
        mode = member.external_attr >> 16
        if stat.S_ISLNK(mode) or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise DatasetError(f"Unsupported special member: {name}")
        if member.flag_bits & 1:
            raise DatasetError(f"Encrypted member: {name}")
        if member.compress_type not in (ZIP_STORED, ZIP_DEFLATED):
            raise DatasetError(f"Unsupported compression: {name}")
        if member.file_size > limits.max_member_bytes:
            raise DatasetError(f"Member exceeds byte limit: {name}")
        if member.file_size / max(1, member.compress_size) > limits.max_compression_ratio:
            raise DatasetError(f"Member exceeds compression ratio limit: {name}")
        total += member.file_size
        if total > limits.max_total_uncompressed_bytes:
            raise DatasetError("Archive exceeds total uncompressed limit")
        suffix = PurePosixPath(name).suffix.lower()
        kind = "directory" if member.is_dir() else (
            "image" if suffix in (".png", ".jpg", ".jpeg", ".tif", ".tiff")
            else "annotation" if suffix == ".json" else "other")
        entries.append(ArchiveEntry(member.filename, member.file_size, member.compress_size, kind))
    if len(entries) > limits.max_entries:
        raise DatasetError("Archive exceeds entry limit")
    return ArchiveInventory(tuple(entries), total)


def open_safe_zip(path: Path, limits: ArchiveLimits) -> ZipFile:
    """Return a validated archive; caller closes it. Local path only."""
    archive = None
    try:
        _preflight(path, limits)
        archive = ZipFile(path)
        inventory_open_zip(archive, limits)
        return archive
    except (OSError, BadZipFile, struct.error) as exc:
        if archive is not None:
            archive.close()
        raise DatasetError(f"Cannot inspect ZIP: {exc}") from exc
    except Exception:
        if archive is not None:
            archive.close()
        raise


def inspect_zip(path: str | Path, limits: ArchiveLimits = ArchiveLimits()) -> ArchiveInventory:
    """List a local ZIP without extraction or decompressing any member."""
    with open_safe_zip(Path(path), limits) as archive:
        return inventory_open_zip(archive, limits)


def read_member(archive: ZipFile, name: str, max_bytes: int) -> bytes:
    """Bound both advertised size and actual decompressed read, including CRC validation."""
    try:
        member = archive.getinfo(name)
        if member.is_dir() or member.file_size > max_bytes:
            raise DatasetError(f"Member exceeds read limit or is a directory: {name}")
        with archive.open(member) as stream:
            payload = stream.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise DatasetError(f"Decoded member exceeds byte limit: {name}")
        return payload
    except (KeyError, OSError, BadZipFile, RuntimeError, EOFError, zlib.error) as exc:
        raise DatasetError(f"Cannot read member {name}: {exc}") from exc
