"""Read-only image/label and cross-split similarity audit; no automatic training."""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.metadata as metadata
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

from .common import sha256, write_json

SPLITS = ("train", "validation", "test")


def parse_labels(text):
    boxes = []
    for index, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 5:
            raise ValueError(f"Label row {index} must have class + normalized xywh")
        values = list(map(float, fields))
        cls, x, y, w, h = values
        if not all(math.isfinite(v) for v in values) or cls != 0:
            raise ValueError(f"Label row {index}: finite values and class 0 required")
        if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
            raise ValueError(f"Label row {index}: invalid normalized geometry")
        # Tiny serialization tolerance only; any actual clipping is recorded later.
        if x-w/2 < -1e-7 or y-h/2 < -1e-7 or x+w/2 > 1+1e-7 or y+h/2 > 1+1e-7:
            raise ValueError(f"Label row {index}: box exceeds original image")
        boxes.append([0, x, y, w, h])
    return boxes


def phash(gray):
    resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    low = cv2.dct(resized)[:8, :8].reshape(-1)[1:]
    bits = low > np.median(low)
    return sum(int(value) << i for i, value in enumerate(bits))


def audit_dataset(source, near_distance=6):
    source = Path(source).resolve()
    records, errors, orphan_labels = [], [], []
    for split in SPLITS:
        images_dir, labels_dir = source / split / "images", source / split / "labels"
        if not images_dir.is_dir() or not labels_dir.is_dir():
            raise ValueError(f"Missing images/labels directory: {split}")
        images = sorted(images_dir.iterdir(), key=lambda p: p.name)
        supported = [p for p in images if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
        stems = [p.stem for p in supported]
        if len(stems) != len(set(stems)):
            raise ValueError(f"Duplicate image stems in {split}")
        orphan_labels.extend(str(p.relative_to(source)) for p in labels_dir.glob("*.txt") if p.stem not in stems)
        for path in supported:
            label = labels_dir / f"{path.stem}.txt"
            item = {"split": split, "image": path.relative_to(source).as_posix(),
                    "label": label.relative_to(source).as_posix() if label.exists() else None,
                    "file_sha256": sha256(path), "bytes": path.stat().st_size,
                    "label_sha256": sha256(label) if label.exists() else None}
            try:
                with Image.open(path) as probe:
                    probe.verify()
                with Image.open(path) as im:
                    im.load()
                    rgb = np.asarray(im.convert("RGB"))
                    item.update(width=im.width, height=im.height, mode=im.mode)
                gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
                item["pixel_sha256"] = hashlib.sha256(rgb.tobytes()).hexdigest()
                item["phash"] = f"{phash(gray):016x}"
                boxes = parse_labels(label.read_text(encoding="utf-8")) if label.exists() else []
                item.update(boxes=boxes, label_status="positive" if boxes else "empty_file" if label.exists() else "missing_assumed_negative")
                # Store a small descriptor for cross-split appearance review.
                item["thumbnail"] = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
            except (ValueError, OSError, SyntaxError) as exc:
                errors.append({"image": item["image"], "error": str(exc)})
                item["label_status"] = "invalid"
            records.append(item)
        print(f"Audited {split}: {len(supported)} images", flush=True)
    duplicates = []
    for field in ("file_sha256", "pixel_sha256"):
        groups = defaultdict(list)
        for item in records:
            if field in item:
                groups[item[field]].append(item["image"])
        duplicates.extend({"type": field, "images": images} for images in groups.values() if len(images) > 1)
    # Exhaustive cross-split pHash screen; a screen cannot prove no capture-session leakage.
    near = []
    valid = [r for r in records if "thumbnail" in r]
    for i, left in enumerate(valid):
        for right in valid[i+1:]:
            if left["split"] == right["split"]:
                continue
            distance = (int(left["phash"], 16) ^ int(right["phash"], 16)).bit_count()
            if distance <= near_distance:
                a, b = left["thumbnail"].astype(float), right["thumbnail"].astype(float)
                denom = np.linalg.norm(a-a.mean()) * np.linalg.norm(b-b.mean())
                correlation = float(np.sum((a-a.mean())*(b-b.mean()))/denom) if denom else 0.
                near.append({"left": left["image"], "right": right["image"],
                             "phash_distance": distance, "thumbnail_correlation": correlation})
    for item in records:
        item.pop("thumbnail", None)
    counts = {}
    for split in SPLITS:
        rows = [r for r in records if r["split"] == split]
        counts[split] = {"images": len(rows), "label_files": sum(r["label"] is not None for r in rows),
                         "label_status": dict(Counter(r["label_status"] for r in rows)),
                         "boxes": sum(len(r.get("boxes", [])) for r in rows),
                         "resolutions": dict(Counter(f"{r['width']}x{r['height']}" for r in rows if "width" in r))}
    return {"source": str(source), "class_names": {"0": "streak"}, "counts": counts,
            "records": records, "errors": errors, "orphan_labels": orphan_labels,
            "duplicates": duplicates, "cross_split_near_pairs": near, "near_distance": near_distance,
            "negative_policy": "Missing label files are assumed negatives under published YOLO format; not individually certified.",
            "sequence_leakage": "Capture/session IDs are unavailable; filename IDs cannot establish independent captures.",
            "supplied_yaml_sha256": sha256(source / "data.yaml") if (source / "data.yaml").exists() else None}


def hardware():
    packages = {}
    for name in ("torch", "torchvision", "ultralytics", "numpy", "Pillow"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    result = {"python": sys.version, "executable": sys.executable, "platform": platform.platform(),
              "packages": packages, "disk": {str(p): shutil.disk_usage(p)._asdict() for p in (Path.cwd().anchor, Path.home().anchor)}}
    try:
        result["nvidia_smi"] = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        result["nvidia_smi"] = None
    if platform.system() == "Windows":
        for name, command in (
            ("cpu", "Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json"),
            ("ram", "Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory | ConvertTo-Json"),
        ):
            result[name] = json.loads(subprocess.check_output(["powershell", "-NoProfile", "-Command", command], text=True))
    if packages["torch"]:
        import torch
        result.update(cuda_available=torch.cuda.is_available(), torch_cuda=torch.version.cuda)
        if torch.cuda.is_available():
            x = torch.ones((64, 64), device="cuda")
            result["cuda_tensor_sum"] = float((x @ x).sum().item())
            result["gpu"] = torch.cuda.get_device_name(0)
    else:
        result["cuda_available"] = None
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/raw/StreaksYoloDataset"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hardware-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "hardware.json", hardware())
    if not args.hardware_only:
        report = audit_dataset(args.source)
        write_json(args.output / "dataset_audit.json", report)
        print(json.dumps({k: report[k] for k in ("counts", "errors", "orphan_labels")}, indent=2))
        print("Duplicate groups:", len(report["duplicates"]), "cross-split near pairs:", len(report["cross_split_near_pairs"]))
        return 2 if report["errors"] or report["orphan_labels"] else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
