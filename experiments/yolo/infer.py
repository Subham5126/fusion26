"""Image-only local YOLO inference; no labels read, original geometry exported."""
import argparse
import json
from pathlib import Path
from time import perf_counter

from .adapter import to_detections
from .common import fresh_output, runtime_setup, sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True, help="Ordered local image-list TXT, one file per frame")
    parser.add_argument("--sequence-id", default="yolo-inference")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--device", default="0")
    parser.add_argument("--seed", type=int, default=26)
    parser.add_argument("--conf", type=float, default=.25)
    parser.add_argument("--max-candidates", type=int, default=200)
    args = parser.parse_args()
    if not args.weights.is_file() or not 0<=args.conf<=1:
        raise ValueError("Existing local weights and confidence [0,1] required")
    paths = [line.strip() for line in args.images.read_text().splitlines() if line.strip()]
    if not paths or any(not Path(p).is_file() for p in paths):
        raise ValueError("Image list must contain existing local files")
    runtime_setup()
    from ultralytics import YOLO
    import torch
    torch.set_num_threads(2)
    torch.manual_seed(args.seed)
    output=fresh_output(args.output)
    model=YOLO(str(args.weights.resolve()))
    if model.names!={0:"streak"}:
        raise ValueError("Inference requires a trained one-class streak checkpoint; COCO labels must not be relabeled as streaks")
    model_id="yolo26n-streak-"+sha256(args.weights)[:12]
    started=perf_counter()
    frames=[]
    results=model.predict(source=paths,stream=True,imgsz=args.imgsz,batch=args.batch,device=args.device,
                          conf=args.conf,max_det=args.max_candidates+1,verbose=False,save=False)
    for index,result in enumerate(results):
        h,w=result.orig_shape
        dets,messages=to_detections(result.boxes.xyxy.cpu().tolist(),result.boxes.conf.cpu().tolist(),
                                  result.boxes.cls.cpu().tolist(),width=w,height=h,frame_index=index,
                                  sequence_id=args.sequence_id,model_id=model_id,max_candidates=args.max_candidates)
        result.save(filename=str(output/f"frame_{index:04d}.jpg"))
        frames.append({"frame_index":index,"image_name":Path(result.path).name,"width":w,"height":h,
                       "warnings":messages,"speed_ms":result.speed,
                       "detections":[d.model_dump(mode="json") for d in dets]})
    if len(frames)!=len(paths):
        raise ValueError("YOLO output count does not match ordered input frames")
    report={"schema_version":"0.1.0","sequence_id":args.sequence_id,"annotations_read":False,
            "weights_sha256":sha256(args.weights),"confidence_semantics":"uncalibrated_model_score",
            "elapsed_s":perf_counter()-started,"frames":frames,"metrics":None}
    write_json(output/"predictions.json",report)
    print(json.dumps({"frames":len(frames),"detections":sum(len(f['detections']) for f in frames),"output":str(output)},indent=2))


if __name__ == "__main__":
    main()
