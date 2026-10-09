"""CV-T14 reproducible evidence; never overwrite an existing output directory.

Read-only local tracker snapshot, frozen CV-T04 adapter, T13 registration,
pixel-only suitability checks, then separate synthetic truth evaluation.
"""

import argparse
from dataclasses import asdict
import hashlib
import html
import json
from pathlib import Path
import platform
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
for directory in ('src', 'backend'):
    sys.path.insert(0, str(ROOT/directory))

import cv2
import numpy as np
from PIL import Image, ImageDraw

from app.schemas.result import AnalysisResult, Provenance, RegistrationResult
from astrotrace.datasets import SpotGeoDataset
from astrotrace.datasets.stress import CASES, create_stress_scene
from astrotrace.detection.stress_evaluation import evaluate_stress
from astrotrace.preprocessing.registration import register_sequence, add_reference_coordinates
from astrotrace.preprocessing.registration_visualization import save_registration_panels
from astrotrace.preprocessing.suitability import validate_sequence_suitability
from orbittrace.detection import detect_sequence
from orbittrace.detection.adapter import _settings
from orbittrace.detection.example import _load_snapshot


def write_json(path, payload):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(payload, stream, indent=2, allow_nan=False)


def save_panel(frames, detections, output, truth=None, *, inference_executed=True):
    """Original grayscale and actual candidates; truth added only for evaluation."""
    width, height = frames[0].shape[1], frames[0].shape[0]
    canvas = Image.new('RGB', (width*5, height+55), 'black')
    draw = ImageDraw.Draw(canvas)
    for index, pixels in enumerate(frames):
        low, high = np.percentile(pixels, [1, 99.8])
        view = np.rint(np.clip((pixels.astype(float)-low)/max(high-low, 1)*255, 0, 255)).astype(np.uint8)
        canvas.paste(Image.fromarray(view).convert('RGB'), (index*width, 55))
        candidates = [d for d in detections if d.frame_index == index]
        matched = set()
        if truth is not None:
            from astrotrace.detection.evaluation import match_points
            targets = [o for o in truth['frames'][index]['objects'] if o['visible']]
            scored = match_points([(d.x_raw_px, d.y_raw_px) for d in candidates], [o['raw_xy_px'] for o in targets], 5.)
            matched = {m['predicted_index'] for m in scored['matches']}
            for obj in targets:
                x, y = obj['raw_xy_px']; x += width*index; y += 55
                draw.ellipse((x-6, y-6, x+6, y+6), outline='red', width=1)
                draw.text((x+6, y+4), obj['object_id'], fill='red')
        for rank, det in enumerate(candidates):
            x, y = det.x_raw_px+index*width, det.y_raw_px+55
            color = 'lime' if truth is None or rank in matched else 'yellow'
            draw.line((x-4, y, x+4, y), fill=color, width=1)
            draw.line((x, y-4, x, y+4), fill=color, width=1)
        title = f'frame {index}: {len(candidates)} candidates' if inference_executed else f'frame {index}: INFERENCE NOT RUN'
        draw.text((index*width+3, 3), title, fill='white')
        draw.text((index*width+3, 21), 'green=matched yellow=unmatched red=truth' if truth else 'green=candidate, identity unverified', fill='white')
    canvas.save(output)


def track_result(detections, registration, tracker, *, name, source_type, mode):
    Tracker, attach = tracker
    tracks = Tracker().process_sequence(detections, frame_indices=range(5))
    frame = 'reference_frame_0' if mode == 'registered' else 'raw'
    tracks = attach(tracks, coordinate_frame=frame, time_basis='frame',
                    frame_dimensions=(registration.width_px, registration.height_px))
    result = AnalysisResult(schema_version='0.1.0', job_id='cv-t14-local', sequence_id=name,
        source_type=source_type, profile='spotgeo', status='succeeded', time_basis='frame', coordinate_frame=frame,
        registration=RegistrationResult(status='estimated' if mode == 'registered' else 'not_required',
            warnings=[] if mode == 'registered' else ['Raw diagnostic comparator; no compensation']),
        detections=detections, tracks=tracks, metrics=None, runtime_ms=None,
        warnings=['Candidate association is not debris identity; diagnostics only'],
        provenance=Provenance(input_sha256=None, config_sha256=None, code_commit=None, dataset_version=None))
    return tracks, result


def save_track_panel(frames, tracks, registration, mode, output):
    """Actual observed track IDs/trails; predictions never drawn as observations."""
    w, h = frames[0].shape[1], frames[0].shape[0]
    panel = Image.new('RGB', (5*w, h+40), 'black')
    draw = ImageDraw.Draw(panel)
    colors = ('lime', 'cyan', 'orange', 'magenta', 'yellow', '#77aaff', '#ffaacc')
    for index, pixels in enumerate(frames):
        low, high = np.percentile(pixels, [1, 99.8])
        view = np.clip((pixels.astype(float)-low)/max(1., high-low)*255, 0, 255).astype(np.uint8)
        panel.paste(Image.fromarray(view).convert('RGB'), (index*w, 40))
        draw.text((index*w+3, 3), f'{mode} frame {index}: actual observed IDs', fill='white')
        draw.text((index*w+3, 20), 'Trails=observations only; identity unverified', fill='white')
        for rank, track in enumerate(tracks):
            points = [p for p in track.points if p.point_type == 'observed' and p.frame_index <= index]
            if not points:
                continue
            if mode == 'registered':
                positions = registration.frames[index].transform_points(
                    [(p.x_reference_px, p.y_reference_px) for p in points], inverse=True)
            else:
                positions = np.array([(p.x_raw_px, p.y_raw_px) for p in points])
            positions += (index*w, 40)
            color = colors[rank % len(colors)]
            # Clip drawing to the current panel rather than spill trails outside it.
            valid = (positions[:, 0] >= index*w) & (positions[:, 0] < (index+1)*w) & (positions[:, 1] >= 40) & (positions[:, 1] < h+40)
            visible = positions[valid]
            if len(visible) > 1:
                draw.line([tuple(p) for p in visible], fill=color, width=1)
            if points[-1].frame_index == index and valid[-1]:
                x, y = positions[-1]
                draw.ellipse((x-3, y-3, x+3, y+3), outline=color)
                draw.text((x+4, y-10), track.track_id, fill=color)
    panel.save(output)


def process(frames, name, output, tracker, *, truth=None, allow_diagnostic=False):
    output.mkdir()
    suitability = validate_sequence_suitability(frames)
    # Unsupported examples are blocked. Noise/blank/blurred diagnostic experiments
    # explicitly bypass uncertain guard, and are never presented as production success.
    permitted = suitability['inference_allowed'] or (allow_diagnostic and suitability['status'] == 'uncertain')
    started = perf_counter()
    detections = detect_sequence(frames, sequence_id=name) if permitted else []
    detector_ms = (perf_counter()-started)*1000 if permitted else None
    registration = register_sequence(frames)
    report = {'name': name, 'source_type': 'synthetic' if truth else 'real', 'suitability': suitability,
        'inference_executed': permitted, 'uncertain_guard_bypassed_for_diagnostic': permitted and not suitability['inference_allowed'],
        'detections_per_frame': [sum(d.frame_index == i for d in detections) for i in range(5)] if permitted else None,
        'detector_ms_per_frame': detector_ms/5 if detector_ms is not None else None,
        'registration_status': registration.status, 'failed_registration_frames': [f.frame_index for f in registration.frames if f.status == 'failed'],
        'registration_ms_per_frame': float(np.mean([f.runtime_ms for f in registration.frames])),
        'registered_tracking': 'blocked: failed registration' if registration.status == 'failed' else 'not_run: unsuitable input',
        'annotations_used_during_inference': False}
    write_json(output/'suitability.json', suitability)
    write_json(output/'registration.json', registration.to_dict())
    write_json(output/'detections.json', {'inference_executed': permitted,
        'uncertain_guard_bypassed_for_diagnostic': permitted and not suitability['inference_allowed'],
        'input_status': suitability['status'], 'detections': [d.model_dump(mode='json') for d in detections] if permitted else None})
    save_panel(frames, detections, output/'candidates.png', truth if permitted else None, inference_executed=permitted)
    save_registration_panels(frames, registration, output)
    if truth:
        write_json(output/'truth.json', truth)
        for index, pixels in enumerate(frames):
            Image.fromarray(pixels).save(output/f'{index+1}.png')
        report['expected_suitability'] = truth['expected_suitability']
        report['suitability_label_agrees'] = suitability['status'] == truth['expected_suitability']
        errors = [float(np.linalg.norm(np.asarray(f.raw_to_reference)[:2, 2]+truth['frames'][i]['camera_shift_xy_px']))
                  for i, f in enumerate(registration.frames) if f.status != 'failed']
        report['synthetic_shift_max_error_px'] = max(errors, default=None)
    if permitted:
        for mode in ('raw', 'registered'):
            if mode == 'registered' and registration.status == 'failed':
                continue  # no per-frame mixture or fabricated identity transforms
            proposals = detections if mode == 'raw' else add_reference_coordinates(detections, registration)
            started = perf_counter()
            tracks, result = track_result(proposals, registration, tracker, name=name,
                source_type=report['source_type'], mode=mode)
            if not suitability['inference_allowed']:
                result = AnalysisResult.model_validate({**result.model_dump(), 'warnings': [*result.warnings,
                    'Uncertain suitability guard bypassed for diagnostic only; not an accepted production result']})
            write_json(output/f'tracking_{mode}.json', result.model_dump(mode='json'))
            report[f'{mode}_tracking_ms'] = (perf_counter()-started)*1000
            save_track_panel(frames, tracks, registration, mode, output/f'tracking_{mode}.png')
            if truth:
                report[mode] = evaluate_stress(proposals, tracks, truth)
            else:
                report[mode] = {'tracks': len(tracks), 'confirmed_tracks': sum(t.status == 'confirmed' for t in tracks),
                    'identity_accuracy': 'unavailable: ESA point annotations do not supply persistent truth IDs here'}
            if mode == 'registered':
                report['registered_tracking'] = 'contract_validation_passed'
    write_json(output/'report.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=Path('data/raw/SpotGEOv2'))
    parser.add_argument('--tracking-ref', required=True, help='Already fetched local ref, no automatic network request')
    parser.add_argument('--synthetic-only', action='store_true')
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=False)
    cv2.setNumThreads(1)
    commit, hashes, Tracker, attach = _load_snapshot(ROOT, args.tracking_ref, args.output)
    reports = []
    for name in CASES:
        scene = create_stress_scene(name)
        report = process(scene.frames, name.replace('_', '-'), args.output/name, (Tracker, attach),
                         truth=scene.truth, allow_diagnostic=True)
        reports.append(report)
        print(json.dumps({k: report[k] for k in ('name', 'detections_per_frame', 'registration_status', 'registered_tracking')}), flush=True)
    missing = []
    if not args.synthetic_only:
        if not args.source.is_dir():
            missing.append(str(args.source))
        else:
            for split, sid in (('train', '84'), ('train', '438'), ('test', '1107')):
                sequence = SpotGeoDataset(args.source, split=split).load_sequence(sid)
                frames = [f.pixels for f in sequence.frames]
                report = process(frames, f'{split}-{sid}', args.output/f'{split}_{sid}', (Tracker, attach))
                report['input_sha256'] = {str(args.source/split/sid/f'{i}.png'): hashlib.sha256(
                    (args.source/split/sid/f'{i}.png').read_bytes()).hexdigest() for i in range(1, 6)}
                reports.append(report)
    _, settings = _settings('optimized', None)
    summary = {'task': 'CV-T14', 'python': platform.python_version(), 'opencv': cv2.__version__,
        'tracker_commit': commit, 'tracker_source_sha256': hashes, 'tracker_gate_distance_px': Tracker().gate_distance_px,
        'detector_config': settings.to_dict(), 'registration_config': asdict(register_sequence(create_stress_scene('counts_change').frames).config),
        'real_negative_suitability_labels': 'unavailable; no blind daylight validation',
        'scope': 'synthetic stress + previously used ESA diagnostics, not blind scientific validation',
        'missing_data': missing, 'reports': reports}
    write_json(args.output/'summary.json', summary)
    rows = []
    for r in reports:
        folder = r['name'].replace('-', '_')
        if r['source_type'] == 'real':
            folder = r['name'].replace('-', '_')
        tracking_links = ' | '.join(f'<a href="{folder}/tracking_{mode}.png">{mode} observed track overlay</a>'
                                  for mode in ('raw', 'registered') if (args.output/folder/f'tracking_{mode}.png').exists())
        rows.append(f'<h2>{html.escape(r["name"])}</h2><p>{html.escape(r["suitability"]["status"])}; candidates {r["detections_per_frame"]}; registration {r["registration_status"]}</p>'
                    f'<p><a href="{folder}/report.json">Measured report</a> | <a href="{folder}/suitability.json">Suitability reasons</a></p><img width="100%" src="{folder}/candidates.png">')
        rows.append(f'<p>{tracking_links} | <a href="{folder}/star_overlay_before.png">Stars before</a> | <a href="{folder}/star_overlay.png">Stars after</a></p>')
    (args.output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>OrbitTrace CV-T14</title><style>body{background:#111;color:#eee;font:16px sans-serif;margin:24px}a{color:#8cf}img{max-width:1600px}</style><h1>OrbitTrace CV-T14 actual evidence</h1><p>Candidate identity unverified. Synthetic daylight/noise cases are controlled renders, not real negative validation. Uncertain bypass is a diagnostic only. Red circles=truth, green crosses=matched, yellow crosses=unmatched.</p>'+''.join(rows), encoding='utf-8')
    print(f'Evidence: {args.output / "index.html"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
