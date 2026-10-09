"""OrbitTrace CV-T04 development analysis; frozen T03 comparison without tracking."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "backend"))

import cv2
import numpy as np
from PIL import Image, ImageDraw

from astrotrace.datasets import SpotGeoDataset
from astrotrace.datasets.validation import discover_annotations, write_json
from astrotrace.preprocessing.images import display_uint8
from astrotrace.preprocessing.candidates import normalize_grayscale
from astrotrace.detection.baseline import OpenCVBaselineDetector
from astrotrace.detection.diagnostics import measure_candidate
from astrotrace.detection.evaluation import evaluate_sequences, match_points
from astrotrace.detection.runner import detect_sequence
from astrotrace.detection.optimized import OptimizedConfig, detect_optimized_sequence
from astrotrace.detection.visualization import save_detection_panels

PRESERVED = ["src/astrotrace/detection/baseline.py", "src/astrotrace/detection/interface.py",
             "src/astrotrace/detection/runner.py", "src/astrotrace/detection/evaluation.py",
             "src/astrotrace/preprocessing/candidates.py", "scripts/spotgeo_baseline.py",
             "artifacts/reports/t03_spotgeo_benchmark/benchmark.json",
             "artifacts/reports/t03_spotgeo_benchmark/membership.json",
             "artifacts/reports/t03_spotgeo_benchmark/selected_config.json"]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def comparison_panel(sequence, predictions, labels, path):
    """Evaluation-only TP green, FP orange, missed label magenta; native-grid panels."""
    width, height = sequence.frames[0].width_px, sequence.frames[0].height_px
    canvas = Image.new("RGB", (5 * width + 32, height + 56), "#151b24")
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 8), f"OrbitTrace {sequence.split}/{sequence.sequence_id}: green=TP orange=FP magenta=missed label; gate=5px", fill="white")
    for index, (frame, predicted, truth) in enumerate(zip(sequence.frames, predictions.frames, labels.for_sequence(sequence.sequence_id))):
        result = match_points([(d.x_raw_px, d.y_raw_px) for d in predicted.detections], truth.object_coords, 5)
        matched_pred = {m["predicted_index"] for m in result["matches"]}
        matched_truth = {m["truth_index"] for m in result["matches"]}
        panel = Image.fromarray(display_uint8(frame.pixels)).convert("RGB")
        marks = ImageDraw.Draw(panel)
        for i, detection in enumerate(predicted.detections):
            x, y = detection.x_raw_px, detection.y_raw_px
            color = "#35ff70" if i in matched_pred else "#ffa040"
            marks.ellipse((x - 5, y - 5, x + 5, y + 5), outline=color, width=2)
        for i, (x, y) in enumerate(truth.object_coords):
            if i not in matched_truth:
                marks.line((x - 6, y, x + 6, y), fill="#ff50ff", width=2)
                marks.line((x, y - 6, x, y + 6), fill="#ff50ff", width=2)
        offset = index * (width + 8)
        canvas.paste(panel, (offset, 56))
        draw.text((offset + 4, 36), f"Frame {index+1}: TP={result['tp']} FP={result['fp']} FN={result['fn']}", fill="white")
    with Path(path).open("xb") as stream:
        canvas.save(stream, format="PNG")


def analyze(source, output):
    output.mkdir(parents=True, exist_ok=False)
    membership = json.loads((ROOT / "artifacts/reports/t03_spotgeo_benchmark/membership.json").read_text())
    baseline = json.loads((ROOT / "artifacts/reports/t03_spotgeo_benchmark/selected_config.json").read_text())["opencv"]
    snapshot = {name: digest(ROOT / name) for name in PRESERVED}
    write_json(output / "baseline_snapshot.json", {"files_sha256": snapshot, "config": baseline,
               "milestone": "CV-T04; detector ownership continues T03; no tracking T04 work"})
    dataset = SpotGeoDataset(source, split="train")
    annotation_file, labels, annotation_hash = discover_annotations(dataset)
    predictions, rows, image_hashes = [], [], []
    for key in membership["development"]["sequence_ids"]:
        sequence = dataset.load_sequence(key)
        predicted = detect_sequence(sequence, OpenCVBaselineDetector(), baseline)
        predictions.append(predicted)
        for frame, result, truth in zip(sequence.frames, predicted.frames, labels.for_sequence(key)):
            normalized, quantum = normalize_grayscale(frame.pixels)
            matched = match_points([(d.x_raw_px, d.y_raw_px) for d in result.detections], truth.object_coords, 5)
            tp = {m["predicted_index"] for m in matched["matches"]}
            for i, detection in enumerate(result.detections):
                features = measure_candidate(normalized, detection.x_raw_px, detection.y_raw_px, detection.bbox_raw_px, quantum)
                rows.append({"sequence_id": key, "frame_index": frame.frame_index, "category": "tp" if i in tp else "fp",
                             "x_raw_px": detection.x_raw_px, "y_raw_px": detection.y_raw_px,
                             "score": detection.quality_score, **detection.evidence_statistics, **features})
            for point_index, (x, y) in enumerate(truth.object_coords):
                if point_index not in {m["truth_index"] for m in matched["matches"]}:
                    # Label-only diagnostic, never passed to detection.
                    bbox = (max(0, x - 1), max(0, y - 1), min(frame.width_px, x + 2), min(frame.height_px, y + 2))
                    rows.append({"sequence_id": key, "frame_index": frame.frame_index, "category": "fn",
                                 "x_raw_px": x, "y_raw_px": y,
                                 **measure_candidate(normalized, x, y, bbox, quantum)})
            name = f"train/{key}/{frame.official_frame}.png"
            image_hashes.append({"name": name, "sha256": hashlib.sha256(dataset.read_file(name, max_bytes=dataset.max_image_bytes)).hexdigest()})
        comparison_panel(sequence, predicted, labels, output / f"train_{key}_baseline.png")
        print(f"Development diagnostics: train/{key}", flush=True)
    quantiles = {}
    for category in ("tp", "fp", "fn"):
        subset = [r for r in rows if r["category"] == category]
        features = sorted((set.intersection(*(set(r) for r in subset)) if subset else set()) - {"sequence_id", "frame_index", "category", "x_raw_px", "y_raw_px"})
        quantiles[category] = {"count": len(subset), "features": {
            name: np.percentile([r[name] for r in subset], [10, 25, 50, 75, 90]).tolist() for name in features}}
    report = {"source_type": "real", "development": membership["development"], "annotation_file": annotation_file,
              "annotation_sha256": annotation_hash, "baseline_config": baseline,
              "baseline_evaluation": evaluate_sequences(predictions, labels, 5), "feature_quantiles": quantiles,
              "quantile_percentages": [10, 25, 50, 75, 90], "heldout_used_for_tuning": False}
    write_json(output / "analysis.json", report)
    write_json(output / "candidate_features.json", rows)
    write_json(output / "development_image_hashes.json", image_hashes)
    write_json(output / "baseline_predictions.json", [r.to_dict() for r in predictions])
    return report


def verify_snapshot(analysis):
    snapshot = json.loads((analysis / "baseline_snapshot.json").read_text())
    changed = [name for name, sha in snapshot["files_sha256"].items() if digest(ROOT / name) != sha]
    if changed:
        raise ValueError(f"Preserved T03 snapshot changed: {changed}")
    return snapshot


def algorithm_hashes():
    names = ["src/astrotrace/detection/optimized.py", "src/astrotrace/detection/diagnostics.py",
             "src/astrotrace/preprocessing/optimized_candidates.py", "scripts/spotgeo_optimize.py"]
    return {name: digest(ROOT / name) for name in names}


def image_manifest(dataset, sequences):
    return [{"name": f"{dataset.split}/{sequence.sequence_id}/{frame.official_frame}.png",
             "sha256": hashlib.sha256(dataset.read_file(
                 f"{dataset.split}/{sequence.sequence_id}/{frame.official_frame}.png",
                 max_bytes=dataset.max_image_bytes)).hexdigest()}
            for sequence in sequences for frame in sequence.frames]


def development_grid(baseline):
    neutral = {**baseline, "background_step": 1, "min_aperture_snr": 0., "max_peak_fraction": 1.,
               "max_context_elongation": 20., "max_component_aspect": 20., "min_score": 0.}
    variants = [("t03_unchanged", "baseline", baseline)]
    for name, change in [("coarse_maps_only", {"background_step": 4}),
                         ("area_only", {"min_area_px": 4, "max_area_px": 50}),
                         ("aspect_only", {"max_component_aspect": 1.5}),
                         ("spike_only", {"max_peak_fraction": .55}),
                         ("context_shape_only", {"max_context_elongation": 2.5}),
                         ("aperture_snr_only", {"min_aperture_snr": 8.}),
                         ("score_only", {"min_score": .45})]:
        variants.append((name, "optimized", {**neutral, **change}))
    for step in (1, 4):
        for threshold in (3.5, 4.5, 5.5, 6.5):
            for elongation in (2., 2.5, 3.):
                variants.append((f"combined_step{step}_threshold{threshold}_context{elongation}", "optimized",
                                 {**neutral, "background_step": step, "threshold_sigma": threshold,
                                  "max_context_elongation": elongation, "max_peak_fraction": .55}))
    for threshold in (3.5, 4.5, 5.5):
        variants.append((f"combined_snr8_threshold{threshold}", "optimized",
                         {**neutral, "background_step": 4, "threshold_sigma": threshold,
                          "max_context_elongation": 2.5, "max_peak_fraction": .55, "min_aperture_snr": 8.}))
    return [{"name": name, "implementation": implementation, "config": config}
            for name, implementation, config in variants]


def precision_recall_svg(trials, selected, path):
    """Static measured dev tradeoffs; no additional plotting dependencies."""
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="560" viewBox="0 0 800 560">',
             '<rect width="800" height="560" fill="white"/>',
             '<text x="60" y="30" font-size="19">OrbitTrace: real ESA development sweep (120 frames)</text>',
             '<path d="M70 65 V480 H750" fill="none" stroke="#333"/>',
             '<text x="380" y="530" font-size="16">Recall</text>',
             '<text x="12" y="55" font-size="16">Precision</text>']
    for tick in np.linspace(0, 1, 6):
        x, y = 70 + 680 * tick, 480 - 400 * tick
        lines.extend([f'<text x="{x-10}" y="500" font-size="12">{tick:.1f}</text>',
                      f'<text x="30" y="{y+4}" font-size="12">{tick:.1f}</text>'])
    for trial in trials:
        metrics = trial["evaluation"]["metrics"]
        if metrics["precision"] is None or metrics["recall"] is None:
            continue
        x, y = 70 + 680 * metrics["recall"], 480 - 400 * metrics["precision"]
        color = "#e85d04" if trial["name"] == "t03_unchanged" else "#268a63" if trial["name"] == selected else "#4177bb"
        lines.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{color}"><title>{trial["name"]}: P={metrics["precision"]:.4f}, R={metrics["recall"]:.4f}</title></circle>')
    lines.append('<text x="90" y="65" font-size="13">orange: T03; green: selected; blue: experiments (hover for settings)</text></svg>')
    path.write_text("\n".join(lines), encoding="utf-8")


def develop(source, analysis, output):
    snapshot = verify_snapshot(analysis)
    membership = json.loads((ROOT / "artifacts/reports/t03_spotgeo_benchmark/membership.json").read_text())
    analysis_report = json.loads((analysis / "analysis.json").read_text())
    baseline = snapshot["config"]
    grid = development_grid(baseline)
    # Declare search and recall constraint before executing any trial. Do not
    # expand this grid after looking at held-out metrics.
    minimum_recall = .9 * analysis_report["baseline_evaluation"]["metrics"]["recall"]
    output.mkdir(parents=True, exist_ok=False)
    plan = {"source_type": "real", "development": membership["development"], "grid": grid,
            "selection": "Maximum development F1 among optimized trials with recall >= 90% of T03 dev recall; tie: precision, then fixed grid order",
            "minimum_recall": minimum_recall, "matching_radius_px": 5,
            "heldout_used_for_tuning": False, "algorithm_sha256": algorithm_hashes()}
    write_json(output / "experiment_plan.json", plan)
    dataset = SpotGeoDataset(source, split="train")
    _, labels, annotation_hash = discover_annotations(dataset)
    if annotation_hash != analysis_report["annotation_sha256"]:
        raise ValueError("Development annotations changed since analysis")
    sequences = [dataset.load_sequence(key) for key in membership["development"]["sequence_ids"]]
    hashes = image_manifest(dataset, sequences)
    if hashes != json.loads((analysis / "development_image_hashes.json").read_text()):
        raise ValueError("Development image bytes changed since analysis")
    write_json(output / "development_image_hashes.json", hashes)
    trials, all_predictions = [], []
    for index, trial in enumerate(grid):
        predicted = [detect_sequence(sequence, OpenCVBaselineDetector(), baseline)
                     if trial["implementation"] == "baseline" else detect_optimized_sequence(sequence, trial["config"])
                     for sequence in sequences]
        evaluation = evaluate_sequences(predicted, labels, 5)
        trials.append({**trial, "evaluation": evaluation})
        all_predictions.append(predicted)
        write_json(output / f"trial_{index:02d}.json", trials[-1])
        m = evaluation["metrics"]
        print(f"{index+1}/{len(grid)} {trial['name']}: P={m['precision']:.4f} R={m['recall']:.4f} F1={m['f1']:.4f} FP/frame={m['false_positives_per_frame']:.3f} ms={m['processing_ms_mean_per_frame']:.2f}", flush=True)
    eligible = [i for i, trial in enumerate(trials) if trial["implementation"] == "optimized"
                and trial["evaluation"]["metrics"]["recall"] >= minimum_recall]
    if not eligible:
        raise ValueError("No configuration met the declared recall floor")
    chosen = max(eligible, key=lambda i: (trials[i]["evaluation"]["metrics"]["f1"],
                                         trials[i]["evaluation"]["metrics"]["precision"], -i))
    selected = {"name": trials[chosen]["name"], "optimized": trials[chosen]["config"], "t03": baseline,
                "development_metrics": trials[chosen]["evaluation"]["metrics"], "plan": plan,
                "annotation_sha256": annotation_hash, "algorithm_sha256": algorithm_hashes()}
    write_json(output / "selected_config.json", selected)
    write_json(output / "development.json", {"plan": plan, "trials": trials, "complete": True, "selected": selected["name"]})
    write_json(output / "selected_predictions.json", [p.to_dict() for p in all_predictions[chosen]])
    for sequence, predicted in zip(sequences, all_predictions[chosen]):
        comparison_panel(sequence, predicted, labels, output / f"train_{sequence.sequence_id}_selected.png")
    precision_recall_svg(trials, selected["name"], output / "precision_recall.svg")
    verify_snapshot(analysis)
    return selected


def evaluate(source, analysis, development, output):
    snapshot = verify_snapshot(analysis)
    selected_file = development / "selected_config.json"
    selected = json.loads(selected_file.read_text())
    if selected["algorithm_sha256"] != algorithm_hashes():
        raise ValueError("Algorithm changed after development freeze; do not evaluate held-out")
    membership = json.loads((ROOT / "artifacts/reports/t03_spotgeo_benchmark/membership.json").read_text())
    expected = {row["name"]: row["sha256"] for row in json.loads(
        (ROOT / "artifacts/reports/t03_spotgeo_benchmark/heldout_image_hashes.json").read_text())}
    historical = json.loads((ROOT / "artifacts/reports/t03_spotgeo_benchmark/benchmark.json").read_text())
    dataset = SpotGeoDataset(source, split="test")
    _, labels, annotation_hash = discover_annotations(dataset)
    if annotation_hash != "8c3e141fba0b5d3ed220563b458a17b17d73ec8cc762aa46abe40d1016f557f4":
        raise ValueError("Held-out annotations changed since T03")
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "evaluation_plan.json", {"selected_config_sha256": digest(selected_file),
               "membership": membership["held_out"], "matching_radius_px": 5,
               "tuning_complete": True, "algorithm_sha256": algorithm_hashes(),
               "limitation": "Previously measured regression set, not a fresh blind test. No held-out cases used for CV-T04 tuning."})
    baseline_predictions, optimized_predictions, hashes = [], [], []
    for index, key in enumerate(membership["held_out"]["sequence_ids"]):
        sequence = dataset.load_sequence(key)
        current = image_manifest(dataset, [sequence])
        if any(expected.get(row["name"]) != row["sha256"] for row in current):
            raise ValueError(f"Held-out image bytes changed in test/{key}")
        hashes.extend(current)
        # Alternate execution order to reduce systematic warm-cache timing bias.
        if index % 2:
            optimized = detect_optimized_sequence(sequence, selected["optimized"])
            baseline = detect_sequence(sequence, OpenCVBaselineDetector(), snapshot["config"])
        else:
            baseline = detect_sequence(sequence, OpenCVBaselineDetector(), snapshot["config"])
            optimized = detect_optimized_sequence(sequence, selected["optimized"])
        baseline_predictions.append(baseline)
        optimized_predictions.append(optimized)
        if index < 6:
            comparison_panel(sequence, optimized, labels, output / f"test_{key}_selected.png")
        if (index + 1) % 16 == 0:
            print(f"Frozen held-out evaluation: {index+1}/128 sequences", flush=True)
    if len(hashes) != len(expected):
        raise ValueError("Incomplete historical held-out membership")
    baseline_result = evaluate_sequences(baseline_predictions, labels, 5)
    optimized_result = evaluate_sequences(optimized_predictions, labels, 5)
    verify_snapshot(analysis)
    # Preserve full measured output and provenance for review, never substitute
    # previously reported numbers for measurements from this invocation.
    report = {"source_type": "real", "membership": membership["held_out"], "matching_radius_px": 5,
              "selected_config_sha256": digest(selected_file), "selected_name": selected["name"],
              "optimized_config": selected["optimized"], "annotation_sha256": annotation_hash,
              "unchanged_image_count": len(hashes), "baseline_preserved": True,
              "t03_rerun": baseline_result, "optimized": optimized_result,
              "historical_report_sha256": digest(ROOT / "artifacts/reports/t03_spotgeo_benchmark/benchmark.json"),
              "historical_report_keys": sorted(historical), "algorithm_sha256": algorithm_hashes(),
              "timing": "One OpenCV CPU thread, detect calls including preprocessing/features/schema; excludes IO/namespacing/evaluation, alternating detector order. Single wall-time run.",
              "heldout_used_for_tuning": False, "blind_test": False}
    write_json(output / "benchmark.json", report)
    write_json(output / "heldout_image_hashes.json", hashes)
    write_json(output / "baseline_predictions.json", [p.to_dict() for p in baseline_predictions])
    write_json(output / "optimized_predictions.json", [p.to_dict() for p in optimized_predictions])
    return report


def infer(source, split, sequence_id, config_file, output):
    config = json.loads(config_file.read_text())
    if not isinstance(config, dict):
        raise ValueError("Config must be a JSON object")
    config = config.get("optimized", config)
    OptimizedConfig.from_mapping(config)
    dataset = SpotGeoDataset(source, split=split)
    sequence = dataset.load_sequence(sequence_id)
    prediction = detect_optimized_sequence(sequence, config)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "detections.json", prediction.to_dict())
    save_detection_panels(sequence, prediction, output / "candidates.png")
    return {"annotations_read": False, "candidates_per_frame": [len(f.detections) for f in prediction.frames]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    analysis = subs.add_parser("analyze")
    analysis.add_argument("--source", type=Path, default=ROOT / "data/raw/SpotGEOv2")
    analysis.add_argument("--output", type=Path, required=True)
    for name in ("develop", "evaluate", "detect"):
        sub = subs.add_parser(name)
        sub.add_argument("--source", type=Path, default=ROOT / "data/raw/SpotGEOv2")
        sub.add_argument("--output", type=Path, required=True)
        if name == "detect":
            sub.add_argument("--split", choices=("train", "test"), default="train")
            sub.add_argument("--sequence", required=True)
            sub.add_argument("--config", type=Path, required=True)
        else:
            sub.add_argument("--analysis", type=Path, required=True)
            if name == "evaluate":
                sub.add_argument("--development", type=Path, required=True)
    args = parser.parse_args(argv)
    cv2.setNumThreads(1)
    try:
        if args.command == "analyze":
            report = analyze(args.source, args.output)
            result = {"metrics": report["baseline_evaluation"]["metrics"], "features": report["feature_quantiles"]}
        elif args.command == "develop":
            report = develop(args.source, args.analysis, args.output)
            result = {"selected": report["name"], "config": report["optimized"], "metrics": report["development_metrics"]}
        elif args.command == "evaluate":
            report = evaluate(args.source, args.analysis, args.development, args.output)
            result = {"t03_rerun": report["t03_rerun"]["metrics"], "optimized": report["optimized"]["metrics"]}
        else:
            result = infer(args.source, args.split, args.sequence, args.config, args.output)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError) as exc:
        print(f"spotgeo_optimize: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
