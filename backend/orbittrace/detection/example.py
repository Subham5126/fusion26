"""Local CV-T06 evidence runner; image-only inference, optional untouched tracker.

Run from the repository root. --tracking-ref reads two source files
from a locally fetched Git ref into the new ignored report directory, without
checking out/merging that branch or changing any tracking implementation.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter
import warnings

import cv2

from app.schemas.result import AnalysisResult, Provenance, RegistrationResult
from astrotrace.datasets import SpotGeoDataset
from astrotrace.detection.baseline import CandidateLimitWarning
from astrotrace.detection.runner import FrameDetections, SequenceDetections
from astrotrace.detection.visualization import save_detection_panels
from .adapter import _settings, detect_sequence


def _load_snapshot(root: Path, ref: str, output: Path):
    commit = subprocess.check_output(
        ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], cwd=root, text=True,
    ).strip()
    snapshot = output / "tracking_snapshot"
    snapshot.mkdir()
    modules, hashes = [], {}
    for name, path in (
        ("_cv_t06_tracker", "backend/orbittrace/tracking/tracker.py"),
        ("_cv_t06_trajectory", "backend/orbittrace/trajectory/fit.py"),
    ):
        source = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=root)
        target = snapshot / Path(path).name
        target.write_bytes(source)
        hashes[path] = hashlib.sha256(source).hexdigest()
        spec = importlib.util.spec_from_file_location(name, target)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        modules.append(module)
    return commit, hashes, modules[0].Tracker, modules[1].attach_trajectories


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/raw/SpotGEOv2"))
    parser.add_argument("--split", choices=("train", "test"), default="train")
    parser.add_argument("--sequence", default="84")
    parser.add_argument("--method", choices=("baseline", "optimized"), default="optimized")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tracking-ref", help="Locally fetched Git ref; no network access by this runner")
    args = parser.parse_args(argv)
    # Installed wheels live outside the checkout; Git belongs to the caller's cwd.
    root = Path.cwd()
    cv2.setNumThreads(1)
    sequence = SpotGeoDataset(args.source, split=args.split).load_sequence(args.sequence)
    pixels = [frame.pixels for frame in sequence.frames]
    sequence_id = f"{args.split}-{sequence.sequence_id}"
    args.output.mkdir(parents=True, exist_ok=False)
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", CandidateLimitWarning)
        started = perf_counter()
        detections = detect_sequence(pixels, sequence_id=sequence_id, method=args.method)
        elapsed = (perf_counter() - started) * 1000
    messages = [str(w.message) for w in captured]
    by_frame = [[d for d in detections if d.frame_index == index] for index in range(len(pixels))]
    # Existing visualization envelope; per-frame timings were not measured here.
    panel_result = SequenceDetections(sequence.sequence_id, args.split, tuple(
        FrameDetections(i, tuple(dets), 0.0, ()) for i, dets in enumerate(by_frame)
    ))
    save_detection_panels(sequence, panel_result, args.output / "candidates.png")
    _, declared = _settings(args.method, None)
    payload = {
        "schema_version": "0.1.0", "sequence_id": sequence_id,
        "source_type": "real", "profile": "spotgeo", "annotations_read": False,
        "coordinate_system": "raw_top_left_xy_px_integer_centers",
        "score_type": "uncalibrated_heuristic", "config": declared.to_dict(),
        "config_sha256": hashlib.sha256(json.dumps(declared.to_dict(), sort_keys=True).encode()).hexdigest(),
        "detection_runtime_ms": elapsed, "warnings": messages,
        "candidates_per_frame": [len(dets) for dets in by_frame],
        "input_sha256": {f"{args.split}/{sequence.sequence_id}/{i+1}.png": hashlib.sha256(
            (args.source / args.split / sequence.sequence_id / f"{i+1}.png").read_bytes()
        ).hexdigest() for i in range(len(pixels))},
        "detections": [d.model_dump(mode="json") for d in detections],
        "tracking_test": "not_run",
    }
    if args.tracking_ref:
        commit, hashes, Tracker, attach_trajectories = _load_snapshot(root, args.tracking_ref, args.output)
        tracks = Tracker().process_sequence(detections, frame_indices=range(len(pixels)))
        tracks = attach_trajectories(tracks, coordinate_frame="raw", time_basis="frame",
                                    frame_dimensions=(pixels[0].shape[1], pixels[0].shape[0]))
        geometry_warning = "Registration unavailable (not attempted); diagnostic raw-frame fallback. ESA associations/trajectories are unvalidated."
        result = AnalysisResult(
            schema_version="0.1.0", job_id="cv-t06-local", sequence_id=sequence_id,
            source_type="real", profile="spotgeo", status="succeeded", time_basis="frame",
            coordinate_frame="raw", registration=RegistrationResult(status="failed", warnings=[geometry_warning]),
            detections=detections, tracks=tracks, metrics=None, runtime_ms=None,
            warnings=[*messages, geometry_warning],
            provenance=Provenance(input_sha256=None, config_sha256=payload["config_sha256"],
                                  code_commit=None, dataset_version="spotGEOv2"),
        )
        observed = [p for t in tracks for p in t.points if p.point_type == "observed"]
        assert len(observed) == len(detections)
        assert {p.detection_id for p in observed} == {d.detection_id for d in detections}
        assert all(p.detection_id is None for t in tracks if t.trajectory for p in t.trajectory.predictions)
        payload.update(tracking_test="passed", tracking_commit=commit, tracking_source_sha256=hashes,
                       track_count=len(tracks), confirmed_tracks=sum(t.status == "confirmed" for t in tracks),
                       trajectory_count=sum(t.trajectory is not None for t in tracks))
        (args.output / "tracking_result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    (args.output / "detections.json").write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k not in ("detections", "input_sha256")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
