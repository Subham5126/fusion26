"""OrbitTrace T13 image-only registration, diagnostics and optional tracking probe.

No large downloads, labels, tuning or source modifications. New output directory
required; five named ESA samples plus two authored scenes are diagnostic evidence.
"""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
for folder in ('src', 'backend'):
    sys.path.insert(0, str(ROOT / folder))

import cv2
import numpy as np

from app.schemas.result import AnalysisResult, Provenance, RegistrationResult
from astrotrace.datasets import SpotGeoDataset
from astrotrace.preprocessing.registration import RegistrationConfig, register_sequence, add_reference_coordinates
from astrotrace.preprocessing.registration_fixtures import create_registration_fixture
from astrotrace.preprocessing.registration_visualization import save_registration_panels
from orbittrace.detection import detect_sequence

SAMPLES = (('train', '84'), ('train', '438'), ('test', '10'), ('test', '57'), ('test', '1107'))


def write_json(path, payload):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(payload, stream, indent=2, allow_nan=False)


def process(frames, sequence_id, output, *, truth=None, tracker=None):
    output.mkdir()
    started = perf_counter()
    result = register_sequence(frames)
    total_ms = (perf_counter()-started)*1000
    predictions = detect_sequence(frames, sequence_id=sequence_id)
    registered = add_reference_coordinates(predictions, result) if result.status != 'failed' else None
    report = {**result.to_dict(), 'sequence_id': sequence_id, 'annotations_read': False,
        'source_type': 'synthetic' if truth is not None else 'real',
        'registration_total_ms': total_ms, 'detections_per_frame': [sum(d.frame_index == i for d in predictions) for i in range(len(frames))],
        'tracking_compatibility': 'not_run: registration failed' if registered is None else 'not_run: tracker not supplied'}
    if truth is not None:
        shift_errors, target_errors, recovered, independent_errors = [], [], [], []
        for index, frame in enumerate(result.frames):
            if frame.status == 'failed':
                continue
            estimated = np.asarray(frame.raw_to_reference)[:2, 2]
            shift_errors.append(float(np.linalg.norm(estimated+truth.camera_shifts_xy[index])))
            compensated = frame.transform_points(truth.target_raw_xy[index:index+1])[0]
            recovered.append(compensated)
            target_errors.append(float(np.linalg.norm(compensated-truth.target_reference_xy[index])))
            # Separate known background coordinates were never used by fitting.
            check = frame.transform_points(truth.background_reference_xy+truth.camera_shifts_xy[index])
            independent_errors.extend(np.linalg.norm(check-truth.background_reference_xy, axis=1).tolist())
        target_matches = []
        for index in range(len(frames)):
            candidates = [d for d in (registered or []) if d.frame_index == index]
            distances = [float(np.linalg.norm(np.array([d.x_reference_px, d.y_reference_px])-truth.target_reference_xy[index])) for d in candidates]
            best = min(distances, default=None)
            target_matches.append(best if best is not None and best <= 5 else None)
        report['synthetic_evaluation'] = {
            'seed': 13, 'known_camera_shifts_xy_px': truth.camera_shifts_xy.tolist(),
            'shift_error_px_per_valid_frame': shift_errors,
            'max_shift_error_px': max(shift_errors, default=None),
            'independent_background_rmse_px': float(np.sqrt(np.mean(np.square(independent_errors)))) if independent_errors else None,
            'target_compensation_errors_px': target_errors,
            'known_target_reference_xy_px': truth.target_reference_xy.tolist(),
            'compensated_known_target_xy_px': np.asarray(recovered).tolist(),
            'actual_detection_target_errors_px_inclusive_5px_gate': target_matches,
            'known_target_motion_px_per_frame': [3., 1.5],
            'estimated_compensated_displacements_px': np.diff(np.asarray(recovered), axis=0).tolist(),
            'truth_used_only_after_registration_and_detection': True}
    if registered is not None and tracker is not None:
        Tracker, attach = tracker
        tracks = Tracker().process_sequence(registered, frame_indices=range(len(frames)))
        tracks = attach(tracks, coordinate_frame='reference_frame_0', time_basis='frame',
                        frame_dimensions=(result.width_px, result.height_px))
        analysis = AnalysisResult(schema_version='0.1.0', job_id='cv-t13-local', sequence_id=sequence_id,
            source_type=report['source_type'], profile='spotgeo', status='succeeded', time_basis='frame',
            coordinate_frame='reference_frame_0', registration=RegistrationResult(status='estimated', warnings=[]),
            detections=registered, tracks=tracks, metrics=None, runtime_ms=None,
            warnings=['Image-plane diagnostic; associations and orbital identity unvalidated'],
            provenance=Provenance(input_sha256=None, config_sha256=None, code_commit=None, dataset_version=None))
        observed = [point for track in tracks for point in track.points if point.point_type == 'observed']
        assert {p.detection_id for p in observed} == {d.detection_id for d in registered}
        by_id = {d.detection_id: d for d in registered}
        assert all((p.x_reference_px, p.y_reference_px, p.x_raw_px, p.y_raw_px) ==
                   (by_id[p.detection_id].x_reference_px, by_id[p.detection_id].y_reference_px,
                    by_id[p.detection_id].x_raw_px, by_id[p.detection_id].y_raw_px) for p in observed)
        write_json(output / 'tracking_result.json', analysis.model_dump(mode='json'))
        report.update(tracking_compatibility='passed', tracks=len(tracks), confirmed_tracks=sum(t.status == 'confirmed' for t in tracks))
    write_json(output / 'detections.json', {'raw': [d.model_dump(mode='json') for d in predictions],
               'with_reference': None if registered is None else [d.model_dump(mode='json') for d in registered]})
    save_registration_panels(frames, result, output)
    write_json(output / 'registration.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('data/raw/SpotGEOv2'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--synthetic-only', action='store_true')
    parser.add_argument('--tracking-ref', help='Already fetched local ref; read-only source snapshot')
    args = parser.parse_args(argv)
    cv2.setNumThreads(1)
    args.output.mkdir(parents=True, exist_ok=False)
    tracker, snapshot = None, None
    if args.tracking_ref:
        from orbittrace.detection.example import _load_snapshot
        commit, hashes, Tracker, attach = _load_snapshot(ROOT, args.tracking_ref, args.output)
        tracker = (Tracker, attach)
        snapshot = {'commit': commit, 'source_sha256': hashes}
    reports = []
    for name, streaks, isolated in (('synthetic_stars', False, False),
                                    ('synthetic_streaks', True, False),
                                    ('synthetic_isolated', True, True)):
        fixture = create_registration_fixture(streaks=streaks, isolated_target=isolated)
        report = process(fixture.frames, name.replace('_', '-'), args.output / name, truth=fixture, tracker=tracker)
        report['synthetic_evaluation']['isolated_target_corridor_22px'] = isolated
        reports.append(report)
    missing = []
    if not args.synthetic_only:
        if not args.source.is_dir():
            missing.append(str(args.source))
        else:
            for split, sid in SAMPLES:
                sequence = SpotGeoDataset(args.source, split=split).load_sequence(sid)
                report = process([frame.pixels for frame in sequence.frames], f'{split}-{sid}',
                                  args.output / f'{split}_{sid}', tracker=tracker)
                report['input_sha256'] = {f'{split}/{sid}/{i}.png': hashlib.sha256(
                    (args.source/split/sid/f'{i}.png').read_bytes()).hexdigest() for i in range(1, 6)}
                reports.append(report)
    summary = {'config': asdict(RegistrationConfig()),
        'python': platform.python_version(), 'opencv': cv2.__version__, 'opencv_threads': cv2.getNumThreads(),
        'tracking_snapshot': snapshot, 'missing_data': missing,
        'evaluation_scope': 'five requested previously used ESA examples; diagnostic only, not a blind evaluation',
        'reports': reports}
    write_json(args.output/'summary.json', summary)
    for report in reports:
        print(json.dumps({'sequence_id': report['sequence_id'], 'status': report['status'],
            'frame_statuses': [f['status'] for f in report['frames']],
            'validation_rmse_px': [f['validation_rmse_px'] for f in report['frames']],
            'registration_total_ms': report['registration_total_ms'],
            'tracking_compatibility': report['tracking_compatibility']}, allow_nan=False), flush=True)
    return 2 if missing else 0


if __name__ == '__main__':
    raise SystemExit(main())
