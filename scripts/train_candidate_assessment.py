"""Local CPU logistic regression; whole sequences split before label evaluation.

No downloads or runtime dependency beyond existing NumPy/SciPy. The output is
an optional experimental JSON model, never a calibrated debris classifier.
"""
import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter
import tracemalloc
import cv2
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from astrotrace.datasets import SpotGeoDataset
from astrotrace.datasets.validation import discover_annotations
from astrotrace.detection.optimized import detect_optimized_sequence
from astrotrace.detection.precision import precision_config
from astrotrace.detection.assessment import FEATURES, VERSION, feature_vector, score_candidates
from astrotrace.detection.evaluation import match_points, summarize_frames


def fit_logistic(x, y):
    mean, scale = x.mean(axis=0), np.maximum(x.std(axis=0), 1e-8)
    a = (x-mean)/scale
    def objective(w):
        z=a@w[:-1]+w[-1]; error=expit(z)-y
        return (np.mean(np.logaddexp(0,z)-y*z)+.01*np.sum(w[:-1]**2),
                np.r_[a.T@error/len(y)+.02*w[:-1], error.mean()])
    fit=minimize(objective,np.zeros(a.shape[1]+1),jac=True,method='L-BFGS-B',options={'maxiter':500})
    if not fit.success: raise RuntimeError(fit.message)
    return {'mean':mean.tolist(),'scale':scale.tolist(),'coef':fit.x[:-1].tolist(),'intercept':float(fit.x[-1])}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/raw/SpotGEOv2'))
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False);cv2.setNumThreads(1)
    cfg=precision_config().to_dict()
    datasets={s:SpotGeoDataset(args.source,split=s) for s in ('train','test')}
    excluded=json.loads(Path('docs/handoffs/CV_PRECISION_MEMBERSHIP.json').read_text())
    train_ex=set(excluded['development']['sequence_ids'])
    test_ex=set(excluded['held_out']['sequence_ids'])|{'3','138','1003'}
    order=lambda ids:sorted(ids,key=lambda s:hashlib.sha256(('orbittrace-assess-v1:'+s).encode()).hexdigest())
    available=order(set(datasets['train'].sequence_ids)-train_ex)
    groups={'train':('train',available[:96]),'validation':('train',available[96:128]),
            'test':('test',order(set(datasets['test'].sequence_ids)-test_ex)[:64])}
    (args.output/'membership.json').write_text(json.dumps(groups,indent=2))
    collected={};hashes={};detection_ms={};frame_hash_groups={}
    for group,(split,ids) in groups.items():
        records=[];started=perf_counter()
        for sid in ids:
            seq=datasets[split].load_sequence(sid)
            for f in seq.frames:
                h=hashlib.sha256(f.pixels.tobytes()).hexdigest()
                if h in frame_hash_groups and frame_hash_groups[h]!=group:
                    raise ValueError('Duplicate decoded image crosses model split')
                frame_hash_groups[h]=group
            detected=detect_optimized_sequence(seq,cfg)
            # Match only AFTER image-only candidate extraction; labels are y, never features.
            records.append((sid,detected))
        detection_ms[group]=(perf_counter()-started)*1000
        _,labels,hashes[group]=discover_annotations(datasets[split]);rows=[]
        for sid,detected in records:
            # Existing envelope exposes detections; runtime uses these exact features.
            for i,truth in enumerate(labels.for_sequence(sid)):
                ds=list(detected.frames[i].detections)
                matched=match_points([(d.x_raw_px,d.y_raw_px) for d in ds],truth.object_coords,5)
                positives={m['predicted_index'] for m in matched['matches']}
                rows.append({'detections':ds,'truth':truth.object_coords,'y':[int(k in positives) for k in range(len(ds))]})
        collected[group]=rows
        print(group,len(ids),'sequences',sum(len(r['detections']) for r in rows),'candidates',flush=True)
    train=collected['train'];x=np.array([feature_vector(d) for r in train for d in r['detections']]);y=np.array([v for r in train for v in r['y']])
    if len(set(y))!=2: raise ValueError('Both classes are required')
    model={'version':VERSION,'features':list(FEATURES),'detector_name':'opencv_context_filtered_v2','detector_config':cfg,
           'training_source':'ESA spotGEO v2 point annotations; candidate match within 5 raw pixels',
           'status':'experimental; uncalibrated; no automated filtering',**fit_logistic(x,y)}
    def evaluate(rows,threshold):
        frames=[]
        for row in rows:
            scored=score_candidates(row['detections'],model)['candidates']
            keep=[d for d,s in zip(row['detections'],scored) if s['score']>=threshold]
            frames.append(match_points([(d.x_raw_px,d.y_raw_px) for d in keep],row['truth'],5))
        return summarize_frames(frames,[])
    baseline=evaluate(collected['validation'],0)
    choices=[(t,evaluate(collected['validation'],float(t))) for t in np.arange(.05,.96,.05)]
    valid=[(t,m) for t,m in choices if (m['recall'] or 0)>=.95*(baseline['recall'] or 0)]
    threshold=float(max(valid,key=lambda tm:(tm[1]['precision'] or 0,tm[1]['recall'] or 0))[0]) if valid else 0.
    model['review_threshold']=threshold
    (args.output/'model.json').write_text(json.dumps(model,indent=2))
    tracemalloc.start();started=perf_counter()
    scores=score_candidates([d for r in collected['test'] for d in r['detections']],model)
    score_ms=(perf_counter()-started)*1000;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    report={'model':VERSION,'groups':groups,'annotation_sha256':hashes,'selection':'validation precision retaining >=95% baseline recall; fixed L2 .01',
            'scope':'sequence-disjoint sample, not session-disjoint: capture sessions unavailable; no official benchmark claim',
            'threshold':threshold,'detector_ms':detection_ms,'score_ms':score_ms,'score_peak_python_bytes':peak,
            'model_bytes':(args.output/'model.json').stat().st_size,'metrics':{g:{'baseline':evaluate(rows,0),'ml_review_filter':evaluate(rows,threshold)} for g,rows in collected.items()},
            'automatic_filtering':False,'attribution':'Chen et al., spotGEO v2, doi:10.5281/zenodo.4432143; metadata reports CC BY 4.0; images not redistributed'}
    (args.output/'evaluation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report['metrics']['test']),flush=True)

if __name__=='__main__':main()
