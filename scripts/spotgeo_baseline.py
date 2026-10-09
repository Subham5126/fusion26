"""Dataset validation, label-free inference, and separate held-out detection benchmark."""

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import platform
import sys
import math

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "backend"))

import cv2

from astrotrace.datasets import DatasetError, SpotGeoDataset, parse_annotations
from astrotrace.datasets.validation import discover_annotations, discover_root, validate_dataset, write_json
from astrotrace.detection.baseline import BaselineConfig, MinimalThresholdDetector, OpenCVBaselineDetector
from astrotrace.detection.evaluation import evaluate_sequences, freeze_membership
from astrotrace.detection.runner import detect_sequence
from astrotrace.detection.visualization import save_detection_panels


def config_hash(config) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def benchmark(source: Path, output: Path, *, development_count: int, heldout_count: int,
              radius_px: float, seed: int, fixture_size: bool = False) -> dict:
    """Freeze membership/grid, tune on dev only, evaluate frozen choices on test once."""
    if not math.isfinite(radius_px) or not 0 < radius_px <= 100:
        raise ValueError("Matching radius must be finite in (0,100] px")
    output.mkdir(parents=True, exist_ok=False)
    size = (64, 48) if fixture_size else (640, 480)
    train = SpotGeoDataset(source, split="train", expected_size=size)
    test = SpotGeoDataset(source, split="test", expected_size=size)
    membership = freeze_membership(train.sequence_ids, test.sequence_ids, seed=seed,
                                   development_count=development_count, heldout_count=heldout_count)
    grid = [BaselineConfig(threshold_sigma=threshold, denoise_sigma=blur, max_elongation=elongation).to_dict()
            for threshold, blur, elongation in itertools.product((3.5, 4.5, 5.5), (0.6, 0.9), (2.5, 4.0))]
    minimal_grid = [BaselineConfig(threshold_sigma=t, max_area_px=1000, max_elongation=20).to_dict()
                    for t in (3.5, 4.5, 5.5)]
    membership.update({"source_type": "synthetic" if fixture_size else "real", "source": str(source.resolve()),
                       "matching_radius_px": radius_px, "opencv_parameter_grid": grid,
                       "minimal_parameter_grid": minimal_grid,
                       "objective": "maximum development F1, then precision, then grid order",
                       "image_grid": "raw native pixels, no resampling", "frame_count_per_sequence": 5})
    write_json(output / "membership.json", membership)
    # Labels are read only here for independent evaluation, never passed into detect_sequence.
    train_annotation, train_labels, train_hash = discover_annotations(train)
    test_annotation, test_labels, test_hash = discover_annotations(test)
    dev_sequences = [train.load_sequence(key) for key in membership["development"]["sequence_ids"]]
    experiments, selected = {}, {}
    for name, detector, configs in (("opencv", OpenCVBaselineDetector(), grid),
                                     ("minimal", MinimalThresholdDetector(), minimal_grid)):
        trials = []
        for index, config in enumerate(configs):
            predictions = [detect_sequence(sequence, detector, config) for sequence in dev_sequences]
            metrics = evaluate_sequences(predictions, train_labels, radius_px)["metrics"]
            trials.append({"config": config, "config_sha256": config_hash(config), "metrics": metrics})
            print(f"Development {name} {index + 1}/{len(configs)}: F1={metrics['f1']} P={metrics['precision']} R={metrics['recall']}", flush=True)
        best = max(range(len(trials)), key=lambda i: (trials[i]["metrics"]["f1"] or 0,
                                                    trials[i]["metrics"]["precision"] or 0, -i))
        experiments[name] = {"trials": trials, "selected_trial": best}
        selected[name] = trials[best]["config"]
    write_json(output / "development.json", experiments)
    write_json(output / "selected_config.json", selected)
    # Held-out pixels enter only after parameter selection has been persisted.
    predictions = {"opencv": [], "minimal": []}
    evidence = []
    for index, key in enumerate(membership["held_out"]["sequence_ids"]):
        sequence = test.load_sequence(key)
        for name, detector in (("opencv", OpenCVBaselineDetector()), ("minimal", MinimalThresholdDetector())):
            predictions[name].append(detect_sequence(sequence, detector, selected[name]))
        # First two uniformly selected sequences are display examples, not a curated score subset.
        if index < 2:
            save_detection_panels(sequence, predictions["opencv"][-1], output / f"test_{key}_comparison.png", test_labels)
        if (index + 1) % 16 == 0:
            print(f"Held-out inference {index + 1}/{heldout_count} sequences", flush=True)
        for frame in sequence.frames:
            relative = f"test/{key}/{frame.official_frame}.png"
            evidence.append({"name": relative, "sha256": hashlib.sha256(test.read_file(relative, max_bytes=test.max_image_bytes)).hexdigest()})
    report = {"source_type": membership["source_type"], "dataset_id": "authored_fixture" if fixture_size else "ESA_spotGEO",
              "dataset_version": None,
              "dataset_version_claim": "authored fixture" if fixture_size else "spotGEO v2; archive identity not verified",
              "development_sequences": development_count, "held_out_sequences": heldout_count,
              "matching_radius_px": radius_px, "official_esa_challenge_score": False,
              "protocol": "per-frame maximum-cardinality one-to-one raw-pixel matching; then minimum distance",
              "timing": "perf_counter, detect call only, includes preprocessing/schema construction; excludes loading/evaluation",
              "environment": {"python": platform.python_version(), "opencv": cv2.__version__,
                              "opencv_threads": cv2.getNumThreads()},
              "annotations": {"train": {"file": train_annotation, "sha256": train_hash},
                              "test": {"file": test_annotation, "sha256": test_hash}},
              "selected_configs": selected,
              "selected_config_sha256": {name: config_hash(config) for name, config in selected.items()},
              "held_out": {name: evaluate_sequences(value, test_labels, radius_px) for name, value in predictions.items()},
              "limitations": ["Single-frame candidates do not establish GEO/debris identity",
                              "Star fragments and hot pixels can be false proposals",
                              "Ground truth can include unobservable positions; this single-frame detector cannot infer them",
                              "No registration, temporal confirmation or tracking", "Uniform subset score, not full test score"]}
    write_json(output / "benchmark.json", report)
    write_json(output / "heldout_image_hashes.json", evidence)
    write_json(output / "predictions.json", {name: [value.to_dict() for value in values] for name, values in predictions.items()})
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "benchmark", "detect"):
        command = subs.add_parser(name)
        command.add_argument("--source", type=Path, help="Extracted root; default discovers within data/raw")
        command.add_argument("--output", required=True, type=Path, help="New results directory")
        if name != "validate":
            command.add_argument("--fixture-size", action="store_true")
        if name == "benchmark":
            command.add_argument("--development-count", type=int, default=24)
            command.add_argument("--heldout-count", type=int, default=128)
            command.add_argument("--radius-px", type=float, default=5.0)
            command.add_argument("--seed", type=int, default=26)
        if name == "detect":
            command.add_argument("--sequence", required=True)
            command.add_argument("--split", choices=("train", "test"), default="train")
            command.add_argument("--config", type=Path, help="selected_config.json from benchmark or standalone numeric config")
    args = parser.parse_args(argv)
    cv2.setNumThreads(1)  # CLI declares a repeatable CPU budget; library does not change global state.
    try:
        source = args.source if args.source else discover_root(ROOT / "data" / "raw")
        if args.command == "validate":
            report = validate_dataset(source, args.output, progress=lambda s: print(s, flush=True))
            print(json.dumps({"validation_status": report["status"], "output": str(args.output)}))
            return 0 if report["status"] == "passed" else 2
        if source is None:
            raise DatasetError("ESA dataset missing; use --source with existing synthetic fixtures; no data downloaded")
        if args.command == "benchmark":
            report = benchmark(source, args.output, development_count=args.development_count,
                               heldout_count=args.heldout_count, radius_px=args.radius_px, seed=args.seed,
                               fixture_size=args.fixture_size)
            print(json.dumps({name: value["metrics"] for name, value in report["held_out"].items()}, indent=2))
        else:
            size = (64, 48) if args.fixture_size else (640, 480)
            dataset = SpotGeoDataset(source, split=args.split, expected_size=size)
            if args.config and args.config.stat().st_size > 64 * 1024:
                raise ValueError("Config file exceeds 64 KiB")
            config = json.loads(args.config.read_text(encoding="utf-8")) if args.config else BaselineConfig().to_dict()
            if not isinstance(config, dict):
                raise ValueError("Config file must contain a JSON object")
            if "opencv" in config:
                config = config["opencv"]
            sequence = dataset.load_sequence(args.sequence)
            predictions = detect_sequence(sequence, OpenCVBaselineDetector(), config)
            args.output.mkdir(parents=True, exist_ok=False)
            write_json(args.output / "detections.json", predictions.to_dict())
            save_detection_panels(sequence, predictions, args.output / "candidates.png")
            print(json.dumps({"sequence_id": sequence.sequence_id, "candidates_per_frame": [len(f.detections) for f in predictions.frames],
                              "annotations_read": False, "output": str(args.output)}))
        return 0
    except (DatasetError, ValueError, OSError) as exc:
        print(f"spotgeo_baseline: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
