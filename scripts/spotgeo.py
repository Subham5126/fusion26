"""Local dataset exploration CLI; see src/astrotrace/datasets/README.md."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

# Standalone worker package pending integration-owned packaging coordination.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from astrotrace.datasets import DatasetError, SpotGeoDataset, inspect_zip, parse_annotations
from astrotrace.datasets.fixtures import create_fixture, zip_fixture
from astrotrace.datasets.visualization import save_overlay


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="List ZIP central-directory metadata; no extraction")
    inspect.add_argument("archive", type=Path)
    inspect.add_argument("--limit", type=int, help="Limit printed entries; default lists all")
    inspect.add_argument("--sha256", action="store_true", help="Explicitly stream/hash whole ZIP (can be slow)")
    for name in ("list", "view"):
        command = commands.add_parser(name, help="List sequence IDs" if name == "list" else "Save five frames with GT overlays")
        command.add_argument("source", type=Path)
        command.add_argument("--split", choices=("train", "test"), default="train")
        command.add_argument("--prefix", help="Explicit ZIP wrapper folder (default auto-discovery)")
        command.add_argument("--fixture-size", action="store_true", help="Expect authored 64x48 fixtures instead of ESA 640x480")
        if name == "view":
            command.add_argument("--sequence", required=True)
            command.add_argument("--annotations", required=True, help="Explicit relative JSON member within dataset root")
            command.add_argument("--output", type=Path, required=True, help="New .png output path")
    fixture = commands.add_parser("fixture", help="Create a tiny deterministic synthetic adapter fixture")
    fixture.add_argument("output", type=Path, help="New directory")
    fixture.add_argument("--seed", type=int, default=26)
    fixture.add_argument("--zip", dest="zip_output", type=Path, help="Optional new ZIP path")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            if args.limit is not None and args.limit < 0:
                raise DatasetError("--limit must be nonnegative")
            inventory = inspect_zip(args.archive)
            result = inventory.to_dict()
            result["entry_count"] = len(inventory.entries)
            if args.limit is not None:
                result["entries"] = result["entries"][:args.limit]
            result["omitted_entries"] = result["entry_count"] - len(result["entries"])
            if args.sha256:
                with args.archive.open("rb") as stream:
                    result["archive_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
            print(json.dumps(result, indent=2))
        elif args.command == "fixture":
            root = create_fixture(args.output, seed=args.seed)
            if args.zip_output:
                zip_fixture(root, args.zip_output)
            print(json.dumps({"fixture": str(root), "zip": str(args.zip_output) if args.zip_output else None,
                              "source_type": "synthetic", "size_px": [64, 48], "seed": args.seed}))
        else:
            size = (64, 48) if args.fixture_size else (640, 480)
            dataset = SpotGeoDataset(args.source, split=args.split, prefix=args.prefix, expected_size=size)
            if args.command == "list":
                print(json.dumps({"split": args.split, "sequence_ids": dataset.sequence_ids,
                                  "images_decoded": False, "annotations_read": False}))
            else:
                sequence = dataset.load_sequence(args.sequence)
                annotations = parse_annotations(dataset.read_file(args.annotations, max_bytes=32 * 1024 * 1024),
                                                width_px=size[0], height_px=size[1])
                output = save_overlay(sequence, annotations, args.output)
                print(json.dumps({"output": str(output), "overlay": "ground_truth", "coordinates": annotations.coordinate_convention}))
        return 0
    except (DatasetError, OSError, ValueError) as exc:
        print(f"spotgeo: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
