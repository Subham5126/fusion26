"""Reproduce the frozen precision profile on already available ESA images.

No downloads. Inference receives native pixels/metadata only. Annotation reading
and matching happen after image-only inference. This is a regression on the
historically used CV-T04 sample, not a new blind test or full ESA evaluation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'backend')]
from astrotrace.datasets import SpotGeoDataset
from astrotrace.datasets.validation import discover_annotations
from astrotrace.detection.evaluation import evaluate_sequences
from astrotrace.detection.optimized import OptimizedConfig, detect_optimized_sequence
from astrotrace.detection.precision import precision_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'data/raw/SpotGEOv2')
    parser.add_argument('--output', type=Path, default=ROOT / '.cache/precision-review/fresh-inference.json')
    args = parser.parse_args()
    membership_path = ROOT / 'docs/handoffs/CV_PRECISION_MEMBERSHIP.json'
    membership = json.loads(membership_path.read_text())
    previous = OptimizedConfig(threshold_sigma=4.5, max_context_elongation=2.0)
    configs = {'cv_t04': previous.to_dict(), 'precision': precision_config().to_dict()}
    report = {'matching_gate_px': 5, 'configs': configs,
              'membership_sha256': hashlib.sha256(membership_path.read_bytes()).hexdigest(),
              'scope': 'Previously used CV-T04 regression; not a fresh blind test', 'splits': {}}
    for key in ('development', 'held_out'):
        partition = membership[key]
        dataset = SpotGeoDataset(args.source, split=partition['split'])
        predictions = {name: [] for name in configs}
        for index, sequence_id in enumerate(partition['sequence_ids']):
            sequence = dataset.load_sequence(sequence_id)
            for name, config in configs.items():
                predictions[name].append(detect_optimized_sequence(sequence, config))
            if index % 16 == 0: print(f"{key}: {index + 1}/{len(partition['sequence_ids'])}", flush=True)
        _, labels, annotation_hash = discover_annotations(dataset)
        report['splits'][key] = {'annotation_sha256': annotation_hash, 'sequence_ids': partition['sequence_ids'],
            **{name: evaluate_sequences(output, labels, 5) for name, output in predictions.items()}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    for key, data in report['splits'].items():
        print(key, json.dumps({name: data[name]['metrics'] for name in configs}), flush=True)
    print(f"Saved {args.output}")


if __name__ == '__main__': main()
