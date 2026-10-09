"""Separated box evaluation plus fixed-confidence FP/miss examples; no tuning."""
import argparse
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.optimize import linear_sum_assignment
import yaml

from .adapter import to_detections
from .audit import parse_labels
from .common import fresh_output, runtime_setup, sha256, write_json
from .visualize import panel


def match_boxes(predicted, truth, iou_gate=.5):
    """Max-cardinality gated one-to-one IoU matching then max summed IoU."""
    if not len(predicted) or not len(truth):
        return [],list(range(len(predicted))),list(range(len(truth)))
    a,b=np.asarray(predicted,float),np.asarray(truth,float)
    lower=np.maximum(a[:,None,:2],b[None,:,:2])
    upper=np.minimum(a[:,None,2:],b[None,:,2:])
    intersection=np.prod(np.maximum(upper-lower,0),axis=2)
    area_a=np.prod(a[:,2:]-a[:,:2],axis=1)
    area_b=np.prod(b[:,2:]-b[:,:2],axis=1)
    iou=intersection/(area_a[:,None]+area_b[None,:]-intersection)
    n,m=iou.shape
    penalty=float(min(n,m)+1)
    # Dummy unmatched columns ensure no forbidden match is forced.
    costs=np.full((n,m+n),penalty)
    costs[:,:m]=np.where(iou>=iou_gate,1-iou,3*penalty)
    rows,cols=linear_sum_assignment(costs)
    pairs=[(int(r),int(c),float(iou[r,c])) for r,c in zip(rows,cols) if c<m and iou[r,c]>=iou_gate]
    return pairs,[i for i in range(n) if i not in {p[0] for p in pairs}],[j for j in range(m) if j not in {p[1] for p in pairs}]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data",type=Path,required=True)
    parser.add_argument("--weights",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--split",choices=("val","test"),default="test")
    parser.add_argument("--imgsz",type=int,default=640)
    parser.add_argument("--batch",type=int,default=4)
    parser.add_argument("--device",default="0")
    parser.add_argument("--conf",type=float,default=.25)
    args=parser.parse_args()
    if not args.weights.is_file() or not 0<=args.conf<=1:
        raise ValueError("Existing checkpoint and confidence [0,1] required")
    config=yaml.safe_load(args.data.read_text())
    if "download" in config:
        raise ValueError("Evaluation config must not contain a download directive")
    root=Path(config["path"])
    paths=[Path(p) for p in (root/config[args.split]).read_text().splitlines() if p.strip()]
    output=fresh_output(args.output)
    runtime_setup()
    from ultralytics import YOLO
    import torch
    torch.set_num_threads(2)
    model=YOLO(str(args.weights.resolve()))
    if model.names!={0:"streak"}:
        raise ValueError("Evaluate a trained one-class streak checkpoint, not COCO weights")
    checkpoint_hash=sha256(args.weights)
    metrics=model.val(data=str(args.data.resolve()),split=args.split,imgsz=args.imgsz,batch=args.batch,device=args.device,
                      workers=0,plots=True,project=str(output),name="ultralytics",conf=.001,max_det=200)
    records,by_image,failures=[],{},[]
    totals={"tp":0,"fp":0,"fn":0,"negative_images":0,"negative_fp":0,"negative_images_with_fp":0}
    # One image per timing sample; explicit warm-up excluded from prediction timing.
    model.predict(str(paths[0]),imgsz=args.imgsz,device=args.device,conf=args.conf,verbose=False)
    started=perf_counter()
    timings=[]
    for index,path in enumerate(paths):
        label=path.parent.parent/"labels"/(path.stem+".txt")
        truth=parse_labels(label.read_text()) if label.exists() else []
        result=model.predict(str(path),imgsz=args.imgsz,device=args.device,conf=args.conf,verbose=False,max_det=200)[0]
        h,w=result.orig_shape
        dets,messages=to_detections(result.boxes.xyxy.cpu().tolist(),result.boxes.conf.cpu().tolist(),result.boxes.cls.cpu().tolist(),
                                  width=w,height=h,frame_index=index,sequence_id="evaluation",
                                  model_id="yolo26n-streak-"+checkpoint_hash[:12])
        boxes=[d.bbox_raw_px for d in dets]
        gt=[((x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h) for _,x,y,bw,bh in truth]
        pairs,unmatched_p,unmatched_g=match_boxes(boxes,gt)
        totals["tp"]+=len(pairs);totals["fp"]+=len(unmatched_p);totals["fn"]+=len(unmatched_g)
        if not truth:
            totals["negative_images"]+=1;totals["negative_fp"]+=len(dets);totals["negative_images_with_fp"]+=bool(dets)
        relative=path.relative_to(root).as_posix()
        by_image[relative]=[d.model_dump(mode="json") for d in dets]
        records.append({"image":relative,"boxes":truth,"label_status":"positive" if truth else "assumed_negative"})
        if unmatched_p or unmatched_g:
            failures.append({"image":relative,"false_positives":len(unmatched_p),"missed_streaks":len(unmatched_g)})
        timings.append(result.speed)
    tp,fp,fn=totals["tp"],totals["fp"],totals["fn"]
    report={"state":"evaluated","split":args.split,"images":len(paths),"weights_sha256":sha256(args.weights),
            "data_sha256":sha256(args.data),"ultralytics_precision":float(metrics.box.mp),"ultralytics_recall":float(metrics.box.mr),
            "map50":float(metrics.box.map50),"map50_95":float(metrics.box.map),
            "ultralytics_pr_semantics":"Ultralytics validation PR at its F1 operating point; AP confidence floor .001; not fixed .25 metrics",
            "fixed_confidence":args.conf,"iou_match_gate":.5,"fixed_counts":totals,
            "fixed_precision":tp/(tp+fp) if tp+fp else None,"fixed_recall":tp/(tp+fn) if tp+fn else None,
            "fp_per_assumed_negative":totals["negative_fp"]/totals["negative_images"] if totals["negative_images"] else None,
            "inference_ms_mean":float(np.mean([t['inference'] for t in timings])),
            "inference_ms_p95":float(np.percentile([t['inference'] for t in timings],95)),
            "timing_semantics":"Ultralytics model inference per image; warmup excluded, IO/evaluation/plots excluded; single run",
            "prediction_loop_elapsed_s":perf_counter()-started,"failure_cases":failures,"by_image":by_image}
    write_json(output/"evaluation.json",report)
    failed_names={f["image"] for f in failures[:8]}
    examples=[r for r in records if r["image"] in failed_names]
    examples += [r for r in records if not r["boxes"] and r["image"] not in failed_names][:4]
    if examples:
        panel(root,examples,output/"failure_examples.png",by_image,"Separated streak evaluation; identity unverified")
    print(json.dumps({k:v for k,v in report.items() if k not in ("by_image","failure_cases")},indent=2))


if __name__ == "__main__":
    main()
