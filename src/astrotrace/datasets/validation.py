"""Local discovery and full decoding evidence; no acquisition or inference."""

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Callable

from .annotations import parse_annotations
from .archive import DatasetError
from .spotgeo import SpotGeoDataset
from .visualization import save_overlay


def discover_root(search_root: str | Path) -> Path | None:
    """Find a unique extracted root by its actual train/test directories, depth <=2."""
    search = Path(search_root)
    if not search.is_dir():
        return None
    candidates = [search]
    candidates.extend(p for p in search.iterdir() if p.is_dir() and not p.is_symlink())
    candidates.extend(p for parent in list(candidates[1:]) for p in parent.iterdir()
                      if p.is_dir() and not p.is_symlink())
    roots = [p for p in candidates if (p / "train").is_dir() and (p / "test").is_dir()
             and any(d.is_dir() and d.name.isdecimal() for d in (p / "train").iterdir())]
    if len(roots) > 1:
        raise DatasetError("Multiple train/test dataset roots; supply --source explicitly")
    return roots[0].resolve() if roots else None


def discover_annotations(dataset: SpotGeoDataset):
    """Match actual root JSON content against split membership, never guess its filename.

    Intended for extracted data; parser checks full official schema. The same numeric
    IDs can exist in train and test, so use exact split-ID set equality. Ambiguity
    fails. Inference never calls this evaluation/validation helper.
    """
    if dataset.is_zip:
        raise DatasetError("Automatic annotation discovery requires extracted data")
    matches, rejected = [], []
    expected_ids = set(dataset.sequence_ids)
    for path in sorted(dataset.source.glob("*.json")):
        try:
            payload = dataset.read_file(path.name, max_bytes=32 * 1024 * 1024)
            labels = parse_annotations(payload, width_px=dataset.expected_size[0], height_px=dataset.expected_size[1])
            ids = {key for key, _ in labels.frames}
            if ids == expected_ids:
                matches.append((path.name, labels, hashlib.sha256(payload).hexdigest()))
        except DatasetError as exc:
            rejected.append({"name": path.name, "error": str(exc)})
    if len(matches) != 1:
        raise DatasetError(f"Expected one annotation JSON matching {dataset.split}; found {len(matches)}; rejected={rejected}")
    return matches[0]


def write_json(path: Path, value) -> None:
    """Finite JSON, new artifact only; never silently overwrite a previous report."""
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def validate_dataset(source: str | Path | None, output: str | Path,
                     progress: Callable[[str], None] = lambda _: None) -> dict:
    """Decode/hash every local train/test sequence and explicitly validate annotations.

    Write report, per-image SHA-256 manifest, nonempty/empty GT panels. Continue
    recording per-sequence failures, but never mark a partial decode as a success.
    Missing data gets a concrete missing status; no fallback download occurs.
    """
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=False)
    report = {"source": str(Path(source).resolve()) if source else None,
              "status": "missing" if source is None else "in_progress", "splits": {},
              "coordinate_system": "raw_top_left_xy_px_integer_centers",
              "coordinate_conversion": "identity; ESA half-pixel edge bounds preserved",
              "dataset_archive_checksum_verified": False}
    if source is None:
        report["missing_reason"] = "No extracted five-frame train/test root found; no data downloaded"
        write_json(folder / "validation.json", report)
        return report
    image_hashes = []
    for split in ("train", "test"):
        progress(f"Discovering {split}")
        dataset = SpotGeoDataset(source, split=split)
        annotation_name, labels, annotation_hash = discover_annotations(dataset)
        empty_ids = [key for key in dataset.sequence_ids if not labels.for_sequence(key)[0].num_objects]
        dimensions, dtypes = Counter(), Counter()
        failures = []
        decoded = 0
        first_nonempty = next((key for key in dataset.sequence_ids if key not in set(empty_ids)), None)
        overlay_ids = {key for key in (first_nonempty, next(iter(empty_ids), None)) if key is not None}
        for index, key in enumerate(dataset.sequence_ids):
            try:
                sequence = dataset.load_sequence(key)
                if [f.official_frame for f in sequence.frames] != [1, 2, 3, 4, 5]:
                    raise DatasetError("Frame order does not match official 1..5")
                for frame in sequence.frames:
                    dimensions[f"{frame.width_px}x{frame.height_px}"] += 1
                    dtypes[str(frame.pixels.dtype)] += 1
                    name = f"{split}/{key}/{frame.official_frame}.png"
                    digest = hashlib.sha256(dataset.read_file(name, max_bytes=dataset.max_image_bytes)).hexdigest()
                    image_hashes.append({"name": name, "sha256": digest})
                    decoded += 1
                if key in overlay_ids:
                    save_overlay(sequence, labels, folder / f"{split}_{key}_ground_truth.png")
            except (DatasetError, OSError) as exc:
                failures.append({"sequence_id": key, "error": str(exc)})
            if (index + 1) % 250 == 0:
                progress(f"Validated {split}: {index + 1}/{len(dataset.sequence_ids)} sequences")
        report["splits"][split] = {
            "sequence_count": len(dataset.sequence_ids), "decoded_frame_count": decoded,
            "annotation_file": annotation_name, "annotation_sha256": annotation_hash,
            "annotation_record_count": len(labels.frames), "empty_sequence_count": len(empty_ids),
            "empty_sequence_ids": empty_ids, "dimensions": dict(dimensions), "dtypes": dict(dtypes),
            "frame_order": [1, 2, 3, 4, 5], "failures": failures,
            "ground_truth_panels": [f"{split}_{key}_ground_truth.png" for key in sorted(overlay_ids, key=int)],
        }
    manifest_bytes = json.dumps(image_hashes, sort_keys=True, separators=(",", ":")).encode()
    report["image_manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    report["status"] = "failed" if any(s["failures"] for s in report["splits"].values()) else "passed"
    write_json(folder / "image_hashes.json", image_hashes)
    write_json(folder / "validation.json", report)
    return report
