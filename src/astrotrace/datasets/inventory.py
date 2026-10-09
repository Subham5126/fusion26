"""Read-only local dataset audit; labels are inspected only here, never inference.

All image headers and all local labels are inventoried. Exact encoded-image
hashing covers non-ESA sources; ESA large hash audit remains historical evidence.
No dataset is copied, downloaded or repaired. Unverified semantics stay unknown.
"""

import ast
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'}


def inspect_yolo_labels(label_paths, image_stems):
    """Validate existing class0 normalized cx,cy,w,h rows, without rewriting boxes."""
    count = Counter()
    errors = []
    stems = set()
    for path in label_paths:
        stems.add(path.stem)
        if path.stat().st_size > 1024*1024:
            errors.append({'file': str(path), 'reason': 'label_too_large'})
            continue
        lines = path.read_text().splitlines()
        count['files'] += 1
        if not any(line.strip() for line in lines):
            count['empty_files'] += 1
        for index, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                row = list(map(float, line.split()))
                if len(row) != 5 or not np.isfinite(row).all() or row[0] != 0:
                    raise ValueError('expected class0 plus four finite coordinates')
                _, x, y, width, height = row
                if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < width <= 1 and 0 < height <= 1):
                    raise ValueError('normalized coordinates outside bounds')
                if min(x-width/2, y-height/2) < -1e-6 or max(x+width/2, y+height/2) > 1+1e-6:
                    count['boxes_extend_outside_image'] += 1
                count['boxes'] += 1
            except ValueError as exc:
                errors.append({'file': str(path), 'line': index, 'reason': str(exc)})
    return {**count, 'missing_labels': sorted(set(image_stems)-stems),
            'orphan_labels': sorted(stems-set(image_stems)), 'errors': errors}


def inspect_csv(path, image_stems):
    """Audit CSV IDs/box arity; coordinate semantics and identity remain unverified."""
    count = Counter()
    seen, errors = set(), []
    with path.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames
        if columns != ['ImageID', 'bboxes']:
            return {'columns': columns, 'errors': ['Unexpected CSV schema']}
        for index, row in enumerate(reader, 2):
            key = row['ImageID']
            if key in seen:
                errors.append({'line': index, 'reason': 'duplicate ID'})
            seen.add(key)
            count['rows'] += 1
            try:
                if len(row['bboxes']) > 1024*1024:
                    raise ValueError('oversized literal')
                boxes = ast.literal_eval(row['bboxes'])
                if not isinstance(boxes, list):
                    raise ValueError('expected box list')
                if not boxes:
                    count['empty_rows'] += 1
                for box in boxes:
                    if not isinstance(box, (list, tuple)) or not box or not np.isfinite(np.asarray(box, dtype=float)).all():
                        raise ValueError('invalid box values')
                    count[f'boxes_with_{len(box)}_values'] += 1
            except (ValueError, SyntaxError, TypeError) as exc:
                errors.append({'line': index, 'reason': str(exc)})
    return {'columns': columns, **count, 'missing_annotation_ids': sorted(set(image_stems)-seen),
        'annotation_ids_without_image': sorted(seen-set(image_stems)), 'errors': errors,
        'coordinate_semantics': 'unverified; four-value rows resemble xmin,xmax,ymin,ymax, not adopted as a contract'}


def inventory_datasets(project_root):
    """All requested on-disk sources; full headers/labels, explicit hash scope."""
    root = Path(project_root)
    sources = []
    groups = defaultdict(list)
    encoded = defaultdict(list)
    paths = [('spotgeo', root/'data/raw/SpotGEOv2'), ('streaks', root/'data/raw/StreaksYoloDataset'),
             ('csv_train', root/'data/raw/train'), ('csv_val', root/'data/raw/val'),
             ('csv_test', root/'data/raw/test'), ('synthetic', root/'data/synthetic')]
    for name, folder in paths:
        if not folder.is_dir():
            sources.append({'source': name, 'path': str(folder), 'status': 'missing'})
            continue
        images = sorted(p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
        headers, modes, errors = Counter(), Counter(), []
        partitions = defaultdict(list)
        for path in images:
            relative = path.relative_to(folder).as_posix()
            partition = relative.split('/')[0] if name in ('spotgeo', 'streaks') else name
            partitions[partition].append(path)
            try:
                with Image.open(path) as image:
                    headers[f'{image.width}x{image.height}'] += 1
                    modes[image.mode] += 1
                    if image.width*image.height > 4_000_000:
                        errors.append({'path': relative, 'reason': 'exceeds_current_4MP_bound'})
            except (OSError, ValueError) as exc:
                errors.append({'path': relative, 'reason': str(exc)})
            if name != 'spotgeo':
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                encoded[digest].append({'source': name, 'split': partition, 'path': str(path.relative_to(root))})
        record = {'source': name, 'path': str(folder), 'status': 'present', 'images': len(images),
            'dimensions': dict(headers), 'modes': dict(modes), 'header_errors': errors,
            'validation_scope': 'all headers inspected; full image pixel decoding not claimed',
            'hash_scope': 'historical ESA image hashes not recomputed' if name == 'spotgeo' else 'all encoded images SHA256',
            'split_image_counts': {key: len(value) for key, value in partitions.items()},
            'class_semantics': 'unverified', 'license_provenance': 'no new rights verification'}
        if name == 'streaks':
            record['class_semantics'] = 'local data.yaml declares class0 streak; no debris/satellite identity labels'
            record['data_yaml_text'] = (folder/'data.yaml').read_text()
            record['declared_paths_resolve_in_project'] = all((root/'data/yolo-streaks-dataset'/key/'images').is_dir()
                                                            for key in ('train', 'validation', 'test'))
            record['labels'] = {key: inspect_yolo_labels(sorted((folder/key/'labels').glob('*.txt')),
                [p.stem for p in value]) for key, value in partitions.items()}
            record['license_provenance'] = 'No LICENSE/source manifest supplied under this extracted dataset'
        elif name in ('csv_train', 'csv_val'):
            record['annotations'] = inspect_csv(root/'data/raw'/('train.csv' if name == 'csv_train' else 'val.csv'), [p.stem for p in images])
            record['license_provenance'] = 'No source/license/class-description manifest supplied for flat JPEG/CSV dataset'
        elif name == 'csv_test':
            record['annotations'] = {'ground_truth': 'not supplied; sample_submission.csv is not ground truth'}
        elif name == 'spotgeo':
            record['class_semantics'] = 'ESA point positions of GEO-like objects; no certified debris identity or persistent GT track IDs'
            record['annotations'] = 'root train_anno.json and test_anno.json; previous strict parser/validation, no new parsing in this header audit'
        else:
            record['class_semantics'] = 'authored adapter fixture; separate generated truth, no physical realism claim'
        for key, value in partitions.items():
            groups[f'{name}/{key}'] = [p.stem for p in value]
        sources.append(record)
    duplicates = [locations for locations in encoded.values() if len(locations) > 1]
    cross_split = [locations for locations in duplicates if len({(p['source'], p['split']) for p in locations}) > 1]
    return {'sources': sources, 'encoded_duplicates': duplicates, 'cross_source_or_split_encoded_duplicates': cross_split,
        'leakage_limits': ['No full decoded/perceptual near-duplicate audit', 'No capture-session metadata verified',
                          'CSV numeric filenames reused across splits are not alone evidence of leakage',
                          'Empty annotations are potential object negatives, not labelled daylight/suitability negatives'],
        'training_readiness': 'blocked until paths, rights/provenance, boundary boxes and split independence reviewed',
        'training_plan': ['Keep full ESA sequences and capture sessions together; preserve already consumed evaluation sets',
                          'Resolve streak label semantics/rights and YAML layout; validate decoded coordinates and all label errors',
                          'Group exact/near duplicates and source sessions before train/development/untouched test splitting',
                          'Retain original split boundaries for audit; never mix target CSVs of unknown semantics into ESA parser',
                          'Curate explicit daylight/cloud/blank/noise/nighttime hard negatives with independent labels',
                          'Train a licensed streak-candidate baseline only after Member1 approves dependency/config and model budget',
                          'Freeze numeric training config/seed/weights hash; compare CPU OpenCV and learned proposals on untouched data']}
