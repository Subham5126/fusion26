"""OrbitTrace CV-T05: reproducible real-data handoff and read-only readiness checks.

Reuses existing detection, schema, loader, scoring and rendering interfaces.
No detector/tracker implementation or public/backend selection is changed.
"""

import argparse
import builtins
import hashlib
import importlib.metadata
import inspect
import json
from pathlib import Path
import platform
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for folder in ("src", "backend", "scripts"):
    sys.path.insert(0, str(ROOT / folder))

import cv2
import numpy as np
from PIL import Image, ImageDraw

from app.schemas.result import Detection
from astrotrace.datasets import SpotGeoDataset
from astrotrace.datasets.validation import discover_annotations, write_json
from astrotrace.detection.evaluation import evaluate_sequences
from astrotrace.detection.interface import FrameContext
from astrotrace.detection.optimized import OptimizedConfig, OptimizedDetector, detect_optimized_sequence
from astrotrace.detection.visualization import save_detection_panels
from astrotrace.preprocessing.images import display_uint8
from spotgeo_optimize import algorithm_hashes, comparison_panel, image_manifest, verify_snapshot

SAMPLES = (("train", "84"), ("train", "438"), ("test", "10"), ("test", "57"), ("test", "1107"))
COORDINATES = "raw_top_left_xy_px_integer_centers"
CONFIG_PATH = ROOT / "artifacts/reports/cv_t04_development_v2/selected_config.json"
ANALYSIS_PATH = ROOT / "artifacts/reports/cv_t04_analysis"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen_config():
    """Require original T03 and CV-T04 sources/config; never tune parameters."""
    verify_snapshot(ANALYSIS_PATH)
    value = json.loads(CONFIG_PATH.read_text())
    if sha(CONFIG_PATH) != "66f47213bb37ddd825565cd405a43e694d0e8274b4ab834883d82986c78e976b":
        raise ValueError("CV-T04 selected configuration changed")
    if value["algorithm_sha256"] != algorithm_hashes():
        raise ValueError("CV-T04 detector/preprocessing/script changed since freeze")
    historical = json.loads((ROOT / "artifacts/reports/t03_spotgeo_benchmark/final_code_hashes.json").read_text())
    for name, checksum in historical["files"].items():
        if sha(ROOT / name) != checksum:
            raise ValueError(f"Historical T03 code changed: {name}")
    config = value["optimized"]
    OptimizedConfig.from_mapping(config)
    return config


def environment():
    return {"python": platform.python_version(), "platform": platform.platform(),
            "processor": platform.processor(), "opencv_threads": cv2.getNumThreads(),
            "packages": {name: importlib.metadata.version(name) for name in
                         ("numpy", "opencv-python-headless", "scipy", "Pillow", "pydantic", "pytest")}}


def validate_payload(payload, width, height):
    """Check existing evidence envelope and deserialize actual shared Detection.

    This is a local handoff integrity check, not a newly invented tracker API.
    Empty lists remain empty. Native bounds are checked in addition to schema.
    """
    if (payload.get("schema_version") != "0.1.0" or payload.get("coordinate_system") != COORDINATES
            or payload.get("score_type") != "uncalibrated_heuristic" or payload.get("tracking_performed") is not False):
        raise ValueError("Wrong schema/coordinate/score/tracking metadata")
    frames = payload.get("frames", [])
    if len(frames) != 5 or any(type(f.get("frame_index")) is not int or f["frame_index"] != i
                             for i, f in enumerate(frames)):
        raise ValueError("Expected all five ordered frame indexes 0..4")
    by_frame, identifiers = [], []
    for frame in frames:
        if not isinstance(frame.get("detections"), list):
            raise ValueError("Detections must be a list, including [] for empty frames")
        detections = [Detection.model_validate(d) for d in frame["detections"]]
        for d in detections:
            left, top, right, bottom = d.bbox_raw_px
            if (d.frame_index != frame["frame_index"] or not
                    (0 <= left <= d.x_raw_px < right <= width and 0 <= top <= d.y_raw_px < bottom <= height)):
                raise ValueError("Wrong frame or out-of-bounds native coordinates")
            if d.x_reference_px is not None or d.y_reference_px is not None:
                raise ValueError("Unregistered reference coordinates unexpectedly populated")
            identifiers.append(d.detection_id)
        by_frame.append(detections)
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Duplicate per-sequence proposal IDs")
    json.dumps(payload, allow_nan=False)
    return by_frame


def verified_inference(sequence, config, *, repeat=False):
    """Block disk IO during existing detector invocation, check raw input stability.

    Caller loads PNGs beforehand. This guard does not block legitimate decoding;
    labels can only be opened later by separate evaluation/rendering code.
    """
    before = [hashlib.sha256(frame.pixels.tobytes()).hexdigest() for frame in sequence.frames]

    def forbidden(*args, **kwargs):
        raise RuntimeError("Inference attempted filesystem/annotation access")

    with patch.object(Path, "open", forbidden), patch.object(builtins, "open", forbidden):
        result = detect_optimized_sequence(sequence, config)
        validate_payload(result.to_dict(), sequence.frames[0].width_px, sequence.frames[0].height_px)
        if repeat:
            repeated = detect_optimized_sequence(sequence, config)
            for frame, first, second in zip(sequence.frames, result.frames, repeated.frames):
                direct = OptimizedDetector().detect(frame.pixels, FrameContext(
                    frame.frame_index, frame.width_px, frame.height_px, "spotgeo", frame.timestamp_s), config)
                strip_id = lambda detections: [{k: v for k, v in d.model_dump().items() if k != "detection_id"}
                                              for d in detections]
                if [d.model_dump() for d in first.detections] != [d.model_dump() for d in second.detections]:
                    raise ValueError("Repeat inference changed detections")
                if strip_id(first.detections) != strip_id(direct):
                    raise ValueError("Sequence wrapper changed native coordinates/scores/schema")
    if before != [hashlib.sha256(frame.pixels.tobytes()).hexdigest() for frame in sequence.frames]:
        raise ValueError("Inference mutated raw pixels")
    return result


def integration_report():
    """Inspect real modules and invoke existing backend fail-closed/health paths.

    Does not simulate a tracker or claim an unavailable call succeeded.
    """
    from app.core.config import PipelineConfig
    from app.main import app
    from app.schemas.sequence import SequenceInput
    from fastapi.testclient import TestClient
    from orbittrace import pipeline, tracking, detection

    symbols = {name: str(inspect.signature(value)) for name, value in vars(tracking).items()
               if not name.startswith("_") and callable(value)}
    fixture = SequenceInput.model_validate_json((ROOT / "tests/contracts/fixtures/sequence.json").read_text())
    try:
        pipeline.analyze(fixture, PipelineConfig())
    except NotImplementedError as exc:
        pipeline_result = {"status": "not_implemented", "actual_exception": str(exc)}
    else:
        pipeline_result = {"status": "unexpected_success_requires_review"}
    with TestClient(app) as client:
        health = client.get("/api/health")
        unavailable = client.post("/api/analyze/demo", json={"demo_id": "not-executed"})
    adapter = getattr(detection, "detect_sequence", None)
    adapter_info = {"available": callable(adapter)}
    if callable(adapter):
        method = inspect.signature(adapter).parameters.get("method")
        adapter_info.update(signature=str(inspect.signature(adapter)),
                            default_method=method.default if method else None,
                            selected_detector="CV-T04" if method and method.default == "optimized" else "requires_review",
                            file_sha256=sha(ROOT / "backend/orbittrace/detection/adapter.py"))
    return {"tracker_module": "orbittrace.tracking", "tracker_file": "backend/orbittrace/tracking/__init__.py",
            "tracker_callables": symbols, "tracker_available": bool(symbols),
            "planned_signature": "associate(detections_by_frame, frame_metadata, config) -> list[Track] (architecture only)",
            "end_to_end_tracker_test": "not_run: no implemented callable tracker is present" if not symbols
                else "not_run: inspect new tracker signature before claiming compatibility",
            "shared_detection_schema": "app.schemas.result.Detection v0.1.0",
            "detection_schema_compatibility": "validated separately on real generated detections",
            "coordinate_readiness": "raw only; x/y_reference_px remain null; image-derived registration required for a common frame",
            "backend_detector_selection": "neither" if pipeline_result["status"] == "not_implemented" else "requires_review",
            "backend_detection_adapter": adapter_info,
            "pipeline": pipeline_result, "health_status_code": health.status_code, "health": health.json(),
            "analysis_route_status_code": unavailable.status_code,
            "analysis_route_response": unavailable.json(),
            "runtime_evidence_scope": "read-only in-process backend calls on authored metadata fixture; no real image-to-tracker/API analysis available",
            "files_sha256": {name: sha(ROOT / name) for name in (
                "backend/orbittrace/tracking/__init__.py", "backend/orbittrace/pipeline.py",
                "backend/app/core/config.py", "backend/app/schemas/result.py", "backend/app/main.py")}}


def raw_panels(sequence, output):
    width, height = sequence.frames[0].width_px, sequence.frames[0].height_px
    canvas = Image.new("RGB", (5*width+32, height+56), "#151b24")
    marks = ImageDraw.Draw(canvas)
    marks.text((8, 8), f"OrbitTrace {sequence.split}/{sequence.sequence_id}: original images; display-only stretch; no detections", fill="white")
    for i, frame in enumerate(sequence.frames):
        canvas.paste(Image.fromarray(display_uint8(frame.pixels)).convert("RGB"), (i*(width+8), 56))
        marks.text((i*(width+8)+4, 36), f"ESA frame {frame.official_frame}; internal {frame.frame_index}", fill="white")
    with output.open("xb") as stream:
        canvas.save(stream, format="PNG")


def package(source, output):
    """Five already-used real examples; no raw file copies or new inference API."""
    config = frozen_config()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "detector_config.json", config)
    write_json(output / "environment.json", environment())
    integration = integration_report()
    write_json(output / "integration.json", integration)
    datasets = {split: SpotGeoDataset(source, split=split) for split in ("train", "test")}
    histories = json.loads((ROOT / "artifacts/reports/cv_t04_development_v2/selected_predictions.json").read_text())
    histories += json.loads((ROOT / "artifacts/reports/cv_t04_evaluation/optimized_predictions.json").read_text())
    previous = {(s["split"], s["sequence_id"]): s for s in histories}
    manifest = {"source_root": "data/raw/SpotGEOv2", "actual_source": str(source.resolve()),
                "source_type": "real", "copies_of_original_images": False, "samples": [],
                "config_sha256": sha(output / "detector_config.json"), "cv_t04_selected_config_sha256": sha(CONFIG_PATH),
                "algorithm_sha256": algorithm_hashes(), "handoff_script_sha256": sha(Path(__file__)),
                "coordinate_system": COORDINATES, "score_type": "uncalibrated_heuristic",
                "attribution": "Chen, Liu, Chin, Rutten, Derksen, Maertens, von Looz, Lecuyer and Izzo; ESA spotGEO v2; DOI 10.5281/zenodo.4432143; published metadata CC BY 4.0. Dataset-relative references; no bulk redistribution.",
                "archive_identity_verified": False}
    loaded = []
    for split, key in SAMPLES:
        dataset = datasets[split]
        with patch.object(dataset, "read_file", wraps=dataset.read_file) as reads:
            sequence = dataset.load_sequence(key)
        names = [call.args[0] for call in reads.call_args_list]
        if names != [f"{split}/{key}/{i}.png" for i in range(1, 6)]:
            raise ValueError("Loader accessed unexpected files")
        predicted = verified_inference(sequence, config, repeat=True)
        payload = predicted.to_dict()
        legacy = previous[(split, key)]
        equal = all(a["detections"] == b["detections"] for a, b in zip(payload["frames"], legacy["frames"]))
        if not equal:
            raise ValueError(f"Output changed since CV-T04 for {split}/{key}")
        directory = output / f"{split}_{key}"
        directory.mkdir()
        write_json(directory / "detections.json", payload)
        raw_panels(sequence, directory / "raw_frames.png")
        save_detection_panels(sequence, predicted, directory / "candidates.png")
        hashes = image_manifest(dataset, [sequence])
        manifest["samples"].append({"split": split, "sequence_id": key, "images": hashes,
                                    "width_px": sequence.frames[0].width_px, "height_px": sequence.frames[0].height_px,
                                    "dtype": str(sequence.frames[0].pixels.dtype), "frame_count": len(sequence.frames),
                                    "candidates_per_frame": [len(f.detections) for f in predicted.frames],
                                    "result": f"{split}_{key}/detections.json", "inference_file_access_blocked": True,
                                    "loader_read_only_expected_pngs": True, "repeatable": True,
                                    "direct_call_coordinates_equal": True, "matches_cv_t04_output": equal})
        loaded.append((sequence, predicted))
        print(f"Member 3 sample {split}/{key}: {manifest['samples'][-1]['candidates_per_frame']}", flush=True)
    # Labels are first opened here, after all sample inference. This layer never
    # modifies saved detections or turns truth positions into observations.
    labels = {split: discover_annotations(dataset) for split, dataset in datasets.items()}
    evaluation = []
    for sequence, predicted in loaded:
        _, annotations, checksum = labels[sequence.split]
        directory = output / f"{sequence.split}_{sequence.sequence_id}"
        comparison_panel(sequence, predicted, annotations, directory / "comparison.png")
        scored = evaluate_sequences([predicted], annotations, 5)
        write_json(directory / "evaluation.json", scored)
        evaluation.append({"split": sequence.split, "sequence_id": sequence.sequence_id,
                           "annotation_sha256": checksum, "metrics": scored["metrics"], "per_frame": scored["per_frame"]})
    if not any(not any(s["candidates_per_frame"]) for s in manifest["samples"]):
        raise ValueError("Package has no genuine all-empty detection sequence")
    if not any(max(s["candidates_per_frame"]) > 1 for s in manifest["samples"]):
        raise ValueError("Package has no multiple-candidate example")
    frozen_config()
    write_json(output / "samples.json", manifest)
    write_json(output / "sample_evaluation.json", {"illustrative_examples_not_a_benchmark": True, "samples": evaluation})
    (output / "README.md").write_text(
        "# OrbitTrace Member 3 real-data package\n\n"
        "Detector import: astrotrace.detection.optimized.OptimizedDetector; five-frame helper: detect_optimized_sequence.\n"
        "Use detector_config.json explicitly, samples.json for dataset-relative references, and each detections.json for actual shared Detection output.\n"
        "raw_frames.png: original pixels, display-only stretch. candidates.png: image-only proposals. comparison.png: separate 5px evaluation (TP green, FP orange, missed label magenta).\n"
        "Schema v0.1.0, raw top-left x/y integer pixel centers, exclusive-upper boxes, fractional centroids. quality_score is heuristic, not a probability.\n"
        "Empty test/1107 JSON contains five genuine empty lists. IDs are proposals, never persistent tracks. Timestamps/reference coordinates remain null.\n"
        "See docs/handoffs/CV-T05.md and src/astrotrace/detection/MEMBER3.md for commands, dependencies, attribution and limitations.\n"
        "Tracker is unavailable and backend selects neither detector; integration.json records actual read-only checks. Sample metrics are illustrative, not generalization accuracy.\n",
        encoding="utf-8")
    return manifest


def verify_package(source, directory):
    """Reprocess every dataset-relative sample and compare actual saved detections."""
    manifest = json.loads((directory / "samples.json").read_text())
    config = json.loads((directory / "detector_config.json").read_text())
    if config != frozen_config() or sha(directory / "detector_config.json") != manifest["config_sha256"]:
        raise ValueError("Package config differs from frozen CV-T04")
    checked = []
    for sample in manifest["samples"]:
        dataset = SpotGeoDataset(source, split=sample["split"])
        sequence = dataset.load_sequence(sample["sequence_id"])
        if image_manifest(dataset, [sequence]) != sample["images"]:
            raise ValueError("Referenced dataset pixels changed")
        saved = json.loads((directory / sample["result"]).read_text())
        validate_payload(saved, sample["width_px"], sample["height_px"])
        current = verified_inference(sequence, config).to_dict()
        if (saved["sequence_id"], saved["split"]) != (sequence.sequence_id, sequence.split):
            raise ValueError("Saved result belongs to a different dataset sequence")
        if any(a["detections"] != b["detections"] for a, b in zip(saved["frames"], current["frames"])):
            raise ValueError("Saved detections differ from current inference")
        checked.append(f"{sample['split']}/{sample['sequence_id']}")
    return {"verified_samples": checked, "verified_frame_count": len(checked)*5,
            "annotation_access_during_inference": False, "saved_detections_reproduced": True}


def recorded_exclusions():
    """Audit known detector use; full decoding/hash validation is disclosed separately.

    Cannot establish broader human/external blindness. Do not call this an
    independently blind test. Known presentation examples are also excluded.
    """
    membership_path = ROOT / "artifacts/reports/t03_spotgeo_benchmark/membership.json"
    membership = json.loads(membership_path.read_text())
    excluded = {(membership[split]["split"], key) for split in ("development", "held_out")
                for key in membership[split]["sequence_ids"]}
    excluded.update(SAMPLES)
    excluded.update({("train", "1"), ("train", "14"), ("test", "1"), ("test", "4"), ("test", "10")})
    reports = []
    for directory in ("t03_spotgeo_benchmark", "cv_t04_analysis", "cv_t04_development_v2",
                      "cv_t04_evaluation", "cv_t04_inference84", "t03_spotgeo_inference10"):
        for path in sorted((ROOT / "artifacts/reports" / directory).glob("*predictions.json")):
            value = json.loads(path.read_text())
            def visit(node):
                if isinstance(node, dict):
                    if node.get("split") in ("train", "test") and "sequence_id" in node:
                        excluded.add((node["split"], str(node["sequence_id"])))
                    for child in node.values():
                        visit(child)
                elif isinstance(node, list):
                    for child in node:
                        visit(child)
            visit(value)
            reports.append({"name": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(path)})
    return excluded, reports


def select_final_ids(sequence_ids, excluded, count, seed):
    if type(count) is not int or not 1 <= count <= 256:
        raise ValueError("Final evaluation count must be 1..256 whole sequences")
    available = [key for key in sequence_ids if ("test", key) not in excluded]
    if count > len(available):
        raise ValueError("Insufficient unused sequences in recorded provenance")
    return sorted(map(str, np.random.default_rng(seed).choice(available, count, replace=False)), key=int)


def verify_tracking_ref(directory, ref, output):
    """Use an already locally fetched, byte-identical Member 3 source snapshot.

    Reuses the separately authored CV-T06 snapshot loader. No fetch, checkout,
    merge, tracking edits or reimplemented association. Raw fallback is explicitly
    diagnostic; successful schema consumption does not validate ESA associations.
    """
    from orbittrace.detection.example import _load_snapshot
    output.mkdir(parents=True, exist_ok=False)
    commit, hashes, Tracker, attach = _load_snapshot(ROOT, ref, output)
    manifest = json.loads((directory / "samples.json").read_text())
    cases = []
    for sample in manifest["samples"]:
        payload = json.loads((directory / sample["result"]).read_text())
        frames = validate_payload(payload, sample["width_px"], sample["height_px"])
        detections = [d for frame in frames for d in frame]
        def forbidden(*args, **kwargs):
            raise RuntimeError("Tracking compatibility test attempted filesystem access")
        with patch.object(Path, "open", forbidden), patch.object(builtins, "open", forbidden):
            tracks = Tracker().process_sequence(detections, frame_indices=range(5))
            tracks = attach(tracks, coordinate_frame="raw", time_basis="frame",
                            frame_dimensions=(sample["width_px"], sample["height_px"]))
        lookup = {d.detection_id: d for d in detections}
        observed = [p for t in tracks for p in t.points if p.point_type == "observed"]
        if len(observed) != len(detections) or {p.detection_id for p in observed} != set(lookup):
            raise ValueError("Tracker lost, duplicated or fabricated observed detections")
        if any((p.x_raw_px, p.y_raw_px, p.frame_index) != (
                lookup[p.detection_id].x_raw_px, lookup[p.detection_id].y_raw_px,
                lookup[p.detection_id].frame_index) for p in observed):
            raise ValueError("Tracker changed raw coordinates/frame identity")
        if any(t.observed_count != len(t.points) for t in tracks):
            raise ValueError("Tracker counted nonobserved points as observations")
        if any(p.detection_id is not None or p.point_type != "extrapolated"
               for t in tracks if t.trajectory for p in t.trajectory.predictions):
            raise ValueError("Trajectory fabricated an observed detection")
        if not detections and tracks:
            raise ValueError("Empty detections created tracks")
        name = f"{sample['split']}_{sample['sequence_id']}"
        write_json(output / f"{name}_tracks.json", [t.model_dump(mode="json") for t in tracks])
        cases.append({"split": sample["split"], "sequence_id": sample["sequence_id"],
                      "detection_count": len(detections), "observed_count": len(observed),
                      "track_count": len(tracks), "confirmed_count": sum(t.status == "confirmed" for t in tracks),
                      "trajectory_count": sum(t.trajectory is not None for t in tracks), "schema_consumption": "passed"})
    for source, expected in hashes.items():
        if sha(output / "tracking_snapshot" / Path(source).name) != expected:
            raise ValueError("Read-only snapshot changed during compatibility test")
    report = {"status": "passed", "scope": "read-only shared-schema consumption of actual saved real detections; no association/trajectory accuracy claim",
              "locally_fetched_ref": ref, "commit": commit, "source_sha256": hashes, "cases": cases,
              "tracker_signature": str(inspect.signature(Tracker.process_sequence)),
              "trajectory_signature": str(inspect.signature(attach)), "active_checkout_tracker_available": False,
              "coordinate_limitation": "Snapshot tracker falls back from null reference to raw coordinates. No image registration was estimated; ESA camera motion makes these diagnostic raw tracks scientifically unvalidated.",
              "backend_api_integration_verified": False, "tracking_sources_modified": False,
              "observations_use_real_detections_only": True, "timestamps": "unknown; px/frame"}
    write_json(output / "compatibility.json", report)
    return report


def final_evaluate(source, output, count, seed):
    """One fixed-config evaluation on sequences disjoint from recorded prior use.

    Freeze IDs without annotation/image stratification. No tuning and no new
    detector models. Refuse exact-byte duplicates against known used sequences.
    """
    config = frozen_config()
    dataset = SpotGeoDataset(source, split="test")
    excluded, reports = recorded_exclusions()
    ids = select_final_ids(dataset.sequence_ids, excluded, count, seed)
    output.mkdir(parents=True, exist_ok=False)
    plan = {"source_type": "real", "split": "test", "sequence_ids": ids, "seed": seed,
            "sequence_count": count, "config": config, "cv_t04_selected_config_sha256": sha(CONFIG_PATH),
            "algorithm_sha256": algorithm_hashes(), "handoff_script_sha256": sha(Path(__file__)),
            "selection": "uniform whole-sequence sampling before labels or pixel inspection; no tuning",
            "excluded": [{"split": s, "sequence_id": k} for s, k in sorted(excluded)], "audited_reports": reports,
            "matching_radius_px": 5, "independent_blind_validation": False,
            "provenance_limit": "Unused for detector tuning/scoring in available records, but all images/annotations underwent T03 full decode/schema/hash validation. Prior external/human exposure and capture-session independence cannot be certified."}
    write_json(output / "membership.json", plan)
    full_hashes = json.loads((ROOT / "artifacts/reports/t03_spotgeo_validation/image_hashes.json").read_text())
    historical = {row["name"]: row["sha256"] for row in full_hashes}
    known_bytes = {row["sha256"] for row in full_hashes if tuple(row["name"].split("/")[:2]) in excluded}
    predictions, sequences, hashes = [], [], []
    for index, key in enumerate(ids):
        sequence = dataset.load_sequence(key)
        current = image_manifest(dataset, [sequence])
        if any(row["sha256"] != historical.get(row["name"]) for row in current):
            raise ValueError("Final-set pixels changed since full archive audit")
        if any(row["sha256"] in known_bytes for row in current):
            raise ValueError("Final-set image duplicates a previously used frame; no automatic reselection")
        hashes.extend(current)
        predictions.append(verified_inference(sequence, config))
        if index < 3:
            sequences.append(sequence)
        if (index+1) % 16 == 0 or index+1 == count:
            print(f"Fixed-config final evaluation: {index+1}/{count} sequences", flush=True)
    # Only after all label-free inference, join separate annotations for scoring.
    annotation_name, labels, annotation_hash = discover_annotations(dataset)
    if annotation_hash != "8c3e141fba0b5d3ed220563b458a17b17d73ec8cc762aa46abe40d1016f557f4":
        raise ValueError("ESA test annotations changed since T03")
    report = {"source_type": "real", "membership_sha256": sha(output / "membership.json"),
              "evaluation": evaluate_sequences(predictions, labels, 5), "environment": environment(),
              "annotation_file": annotation_name, "annotation_sha256": annotation_hash,
              "config": config, "algorithm_sha256": algorithm_hashes(), "sequence_count": count,
              "independent_blind_validation": False, "recorded_prior_use_disjoint": True,
              "exact_byte_overlap_with_known_used_frames": 0, "no_parameter_tuning": True,
              "timing": "one OpenCV CPU thread; actual detect() calls, excludes IO/wrapper/evaluation and file-guard overhead; single wall-time run",
              "provenance_limit": plan["provenance_limit"]}
    frozen_config()
    write_json(output / "benchmark.json", report)
    write_json(output / "predictions.json", [p.to_dict() for p in predictions])
    write_json(output / "image_hashes.json", hashes)
    for sequence, predicted in zip(sequences, predictions[:3]):
        comparison_panel(sequence, predicted, labels, output / f"test_{sequence.sequence_id}_comparison.png")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("package", "verify", "final-evaluate", "inspect-integration", "verify-tracking-ref"):
        sub = subs.add_parser(name)
        if name not in ("inspect-integration", "verify-tracking-ref"):
            sub.add_argument("--source", type=Path, default=ROOT / "data/raw/SpotGEOv2")
        if name == "verify":
            sub.add_argument("--package", type=Path, required=True)
        else:
            sub.add_argument("--output", type=Path, required=True)
        if name == "final-evaluate":
            sub.add_argument("--count", type=int, default=128)
            sub.add_argument("--seed", type=int, default=20261009)
        if name == "verify-tracking-ref":
            sub.add_argument("--package", type=Path, required=True)
            sub.add_argument("--ref", required=True, help="Already locally fetched Git ref; no network fetch")
    args = parser.parse_args(argv)
    cv2.setNumThreads(1)
    try:
        if args.command == "package":
            report = package(args.source, args.output)
            result = {"samples": [{"split": s["split"], "sequence_id": s["sequence_id"],
                                    "candidates_per_frame": s["candidates_per_frame"]} for s in report["samples"]]}
        elif args.command == "verify":
            result = verify_package(args.source, args.package)
        elif args.command == "final-evaluate":
            report = final_evaluate(args.source, args.output, args.count, args.seed)
            result = {"metrics": report["evaluation"]["metrics"],
                      "independent_blind_validation": report["independent_blind_validation"]}
        elif args.command == "verify-tracking-ref":
            result = verify_tracking_ref(args.package, args.ref, args.output)
        else:
            result = integration_report()
            args.output.mkdir(parents=True, exist_ok=False)
            write_json(args.output / "integration.json", result)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"spotgeo_handoff: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
