"""Evaluate existing supplied QA images and a frozen ESA sample; never feed labels to inference."""
import argparse
import json
from pathlib import Path
import cv2
from app.core.config import PipelineConfig
from app.schemas.sequence import SequenceInput
from astrotrace.datasets import SpotGeoDataset
from astrotrace.datasets.validation import discover_annotations
from astrotrace.detection.evaluation import match_points, summarize_frames
from orbittrace.cv_tracking import analyze_telescope_sequence, TelescopeAnalysisError


def run(frames, name, output, truth_loader):
    sequence = SequenceInput(schema_version='0.1.0', sequence_id=name, source_type='user_upload', profile='spotgeo',
        frames=[dict(frame_index=i, image_ref=f'frame_{i}', width_px=p.shape[1], height_px=p.shape[0], timestamp_s=None) for i,p in enumerate(frames)])
    modes = {}
    for mode in ('standard', 'temporal'):
        diagnostic = {}
        try:
            result = analyze_telescope_sequence(frames, sequence=sequence, diagnostics=diagnostic,
                config=PipelineConfig(analysis_mode=mode, gate_distance_px=25 if mode == 'temporal' else 20))
            # Ground truth is read only after the complete image-only pipeline.
            truth = truth_loader()
            scores = [match_points([(d.x_raw_px,d.y_raw_px) for d in result.detections if d.frame_index==i], coords, 5) for i,coords in enumerate(truth)]
            owners = {p.detection_id:t.track_id for t in result.tracks for p in t.points}
            identities = []
            for i, score in enumerate(scores):
                ds = [d for d in result.detections if d.frame_index == i]
                identities.append([{**m, 'track_id':owners[ds[m['predicted_index']].detection_id]} for m in score['matches']])
            modes[mode] = dict(status='succeeded', metrics=summarize_frames(scores,[]), runtime_ms=result.runtime_ms,
                timings_ms=diagnostic['timings_ms'], detections=len(result.detections),
                confirmed_tracks=sum(t.status=='confirmed' for t in result.tracks),
                tracks=[dict(id=t.track_id, frames=[p.frame_index for p in t.points], quality=t.quality_score) for t in result.tracks],
                truth_matches=identities)
            (output/f'{name}-{mode}-result.json').write_text(result.model_dump_json(indent=2), encoding='utf-8')
        except TelescopeAnalysisError as error:
            modes[mode] = dict(status='failed', error=error.error.model_dump())
        (output/f'{name}-{mode}-diagnostics.json').write_text(json.dumps(diagnostic,indent=2), encoding='utf-8')
    print(name, {k:{x:v for x,v in row.items() if x in ('status','metrics','detections','confirmed_tracks','error')} for k,row in modes.items()}, flush=True)
    return dict(name=name, modes=modes)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--supplied',type=Path,default=Path('.cache/final-release/supplied'))
    parser.add_argument('--esa',type=Path,default=Path('data/raw/SpotGEOv2'))
    parser.add_argument('--membership',type=Path,default=Path('docs/handoffs/FINAL_ML_EVALUATION.json'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True);cv2.setNumThreads(1)
    rows=[]
    for folder in sorted(args.supplied.glob('0*')):
        if not (folder/'ground_truth.json').is_file(): continue
        frames=[cv2.imread(str(folder/f'{i:02}.png'),-1) for i in range(1,6)]
        def truth_loader():
            truth=json.loads((folder/'ground_truth.json').read_text(encoding='utf-8'))
            return [[p['center_xy'] for p in f['objects'] if p['visibility']=='visible'] for f in truth['frames']]
        rows.append(run(frames,folder.name,args.output,truth_loader))
    dataset=SpotGeoDataset(args.esa,split='test')
    membership=json.loads(args.membership.read_text())
    ids=membership.get('groups',membership)['test'][1][:32]
    _,labels,annotation_hash=discover_annotations(dataset)
    for sid in ids:
        frames=[f.pixels for f in dataset.load_sequence(sid).frames]
        rows.append(run(frames,f'esa-test-{sid}',args.output,lambda:[f.object_coords for f in labels.for_sequence(sid)]))
    (args.output/'evaluation.json').write_text(json.dumps(dict(rows=rows,annotation_sha256=annotation_hash,
        matching_gate_px=5, note='Supplied synthetic QA and ESA are separate validation paths. Metrics absent on rejected registration; compare only mutually successful sequences.'),indent=2))


if __name__=='__main__':main()
