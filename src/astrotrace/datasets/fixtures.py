"""Tiny deterministic authored fixtures; no ESA pixels, labels or benchmark claims."""

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
from PIL import Image

from .archive import DatasetError


def create_fixture(output: str | Path, *, seed: int = 26) -> Path:
    """Create 2 sequences x 5 64x48 PNGs: one moving point, one empty scene.

    Refuse an existing directory. Labels use ESA record structure, live in a
    separate train_anno.json, and contain no inferred IDs. Seed controls noise.
    This is an adapter test fixture, not a realistic telescope-data generator.
    """
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(seed)
    records = []
    yy, xx = np.mgrid[:48, :64]
    for sequence_id in (1, 2):
        folder = root / "train" / str(sequence_id)
        folder.mkdir(parents=True)
        for frame in range(1, 6):
            pixels = rng.integers(0, 8, size=(48, 64)).astype(np.float64)
            coords = []
            if sequence_id == 1:
                x, y = 8.25 + frame, 12.75 + frame / 2
                pixels += 220 * np.exp(-((xx - x)**2 + (yy - y)**2) / 2)
                coords = [[x, y]]
            Image.fromarray(np.rint(np.clip(pixels, 0, 255)).astype(np.uint8)).save(folder / f"{frame}.png")
            records.append({"sequence_id": sequence_id, "frame": frame,
                            "num_objects": len(coords), "object_coords": coords})
    (root / "train_anno.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    (root / "fixture_provenance.json").write_text(json.dumps({
        "source_type": "synthetic", "seed": seed, "width_px": 64, "height_px": 48,
        "description": "Authored adapter fixture; no ESA data or measured detection metrics",
    }, indent=2) + "\n", encoding="utf-8")
    return root


def zip_fixture(root: str | Path, output: str | Path, *, prefix: str = "") -> Path:
    """Write only our tiny fixture files to a new ZIP; never overwrite artifacts."""
    from .archive import safe_member_name

    root, output = Path(root), Path(output)
    prefix = safe_member_name(prefix) if prefix else ""
    files = sorted(root.rglob("*"))
    if any(p.is_symlink() for p in files):
        raise DatasetError("Fixture symlinks unsupported")
    if sum(p.stat().st_size for p in files if p.is_file()) > 1024 * 1024:
        raise DatasetError("Fixture zipper is limited to 1 MiB of authored samples")
    with ZipFile(output, "x", compression=ZIP_DEFLATED) as archive:
        for path in files:
            if path.is_file():
                relative = path.relative_to(root).as_posix()
                archive.write(path, f"{prefix}/{relative}" if prefix else relative)
    return output
