"""Freeze split membership and build an isolated training view, originals unchanged."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import random
import shutil

import yaml

from .common import fresh_output, sha256, write_json


def select_membership(audit, seed=26, exclude_invalid=False):
    if (audit["errors"] and not exclude_invalid) or audit["orphan_labels"]:
        raise ValueError("Audit errors must be resolved before preparing training")
    rows = {r["image"]: r for r in audit["records"]}
    priority = {"train": 0, "validation": 1, "test": 2}
    excluded = {entry["image"]: ["invalid_image_or_label: " + entry["error"]]
                for entry in audit["errors"]}
    # Keep official test membership. Remove lower-priority near-duplicate images
    # rather than move an image across a split. Conservative pHash screen only.
    for pair in audit["cross_split_near_pairs"]:
        a, b = pair["left"], pair["right"]
        drop = min((a, b), key=lambda p: priority[rows[p]["split"]])
        excluded.setdefault(drop, []).append("cross_split_phash")
    for group in audit["duplicates"]:
        ordered = sorted(group["images"], key=lambda p: (-priority[rows[p]["split"]], p))
        for image in ordered[1:]:
            excluded.setdefault(image, []).append(group["type"])
    selected = {s: sorted(p for p, r in rows.items() if r["split"] == s and p not in excluded)
                for s in priority}
    # Smoke sample is train only, selected before learning; val/test stay separate.
    rng = random.Random(seed)
    positive = [p for p in selected["train"] if rows[p]["boxes"]]
    negative = [p for p in selected["train"] if not rows[p]["boxes"]]
    rng.shuffle(positive)
    rng.shuffle(negative)
    smoke = sorted(positive[:48] + negative[:16])
    return selected, smoke, excluded


def prepare(audit_path, output, seed=26, exclude_invalid=False):
    audit = json.loads(Path(audit_path).read_text(encoding="utf-8"))
    source = Path(audit["source"])
    selected, smoke, excluded = select_membership(audit, seed, exclude_invalid)
    if any(not paths for paths in selected.values()):
        raise ValueError("Filtering left an empty split; inspect similarity audit")
    output = fresh_output(output)
    records = {r["image"]: r for r in audit["records"]}
    for split, paths in selected.items():
        for relative in paths:
            row, original = records[relative], source / relative
            if sha256(original) != row["file_sha256"]:
                raise ValueError(f"Image changed since audit: {relative}")
            label = source / row["label"] if row["label"] else None
            if label is not None and sha256(label) != row["label_sha256"]:
                raise ValueError(f"Label changed since audit: {relative}")
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            # Images never moved/modified. Hard links avoid another 1.5GB copy;
            # Ultralytics reads them only. Labels are copies to isolate caches.
            try:
                os.link(original, target)
            except OSError:
                shutil.copy2(original, target)
            label_target = target.parent.parent / "labels" / f"{target.stem}.txt"
            label_target.parent.mkdir(parents=True, exist_ok=True)
            label_target.write_text(label.read_text(encoding="utf-8") if label else "", encoding="utf-8")
    for split, paths in {**selected, "smoke": smoke}.items():
        (output / f"{split}.txt").write_text("".join(f"{(output / p).as_posix()}\n" for p in paths), encoding="utf-8")
    for name, train_list in (("dataset", "train.txt"), ("smoke", "smoke.txt")):
        config = {"path": output.as_posix(), "train": train_list, "val": "validation.txt", "test": "test.txt",
                  "nc": 1, "names": {0: "streak"}}
        (output / f"{name}.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    counts = {split: {"images": len(paths), "positives": sum(bool(records[p]["boxes"]) for p in paths),
                      "negative_assumptions": sum(not records[p]["boxes"] for p in paths),
                      "boxes": sum(len(records[p]["boxes"]) for p in paths)} for split, paths in selected.items()}
    report = {"audit_sha256": sha256(audit_path), "source": str(source), "seed": seed,
              "selected": selected, "smoke": smoke, "excluded": excluded, "counts": counts,
              "policy": "Official splits retained; exact duplicates and cross-split pHash<=6 candidates excluded conservatively. No capture-session metadata: residual leakage possible.",
              "original_sha256": {p: {"image": records[p]["file_sha256"], "label": records[p]["label_sha256"]} for paths in selected.values() for p in paths}}
    write_json(output / "membership.json", report)
    print(json.dumps({"counts": counts, "smoke_images": len(smoke), "excluded": len(excluded)}, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=26)
    parser.add_argument("--exclude-invalid", action="store_true", help="Exclude audited malformed samples, never repair original labels")
    args = parser.parse_args()
    prepare(args.audit, args.output, args.seed, args.exclude_invalid)


if __name__ == "__main__":
    main()
