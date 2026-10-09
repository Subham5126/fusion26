"""Experimental YOLO -> existing Detection bridge; backend code is untouched.

xyxy must already be Ultralytics Results.boxes.xyxy in ORIGINAL image pixels.
Never pass letterboxed tensor coordinates here. Confidence is an uncalibrated
model score, stored explicitly in evidence as well as the bounded quality field.
"""
import hashlib
import math
import re

from app.schemas.result import Detection


def to_detections(xyxy, confidence, classes, *, width, height, frame_index,
                  sequence_id, model_id="yolo26n-streak-experimental", max_candidates=200):
    if type(width) is not int or type(height) is not int or min(width,height) < 1:
        raise ValueError("Original dimensions must be positive integers")
    if type(frame_index) is not int or frame_index < 0:
        raise ValueError("frame_index must be a nonnegative integer")
    if not isinstance(sequence_id,str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}",sequence_id):
        raise ValueError("Invalid sequence_id")
    if not isinstance(model_id,str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}",model_id):
        raise ValueError("Invalid model ID")
    if type(max_candidates) is not int or not 1 <= max_candidates <= 2000:
        raise ValueError("Invalid candidate cap")
    if not len(xyxy) == len(confidence) == len(classes):
        raise ValueError("Box/score/class counts disagree")
    token = hashlib.sha256(f"{sequence_id}/{model_id}".encode()).hexdigest()[:16]
    candidates = []
    for box, score, cls in zip(xyxy, confidence, classes):
        if len(box) != 4:
            raise ValueError("Expected xyxy boxes")
        x0,y0,x1,y1 = map(float,box)
        score,cls = float(score),float(cls)
        if not all(math.isfinite(v) for v in (x0,y0,x1,y1,score,cls)) or not 0<=score<=1 or cls!=0:
            raise ValueError("Expected finite boxes, confidence [0,1], class 0 streak")
        if not (0<=x0<x1<=width and 0<=y0<y1<=height):
            raise ValueError("Box must have positive exclusive upper bounds inside native image")
        candidates.append((score,(x0,y0,x1,y1)))
    candidates.sort(key=lambda row:(-row[0],row[1]))
    warnings=[]
    if len(candidates)>max_candidates:
        warnings.append(f"{len(candidates)} YOLO proposals exceed cap {max_candidates}; strongest retained")
    result = [Detection(detection_id=f"sy{token}-f{frame_index}-c{rank}",frame_index=frame_index,
                        x_raw_px=(box[0]+box[2])/2,y_raw_px=(box[1]+box[3])/2,bbox_raw_px=box,
                        kind="streak",quality_score=score,detector_name=model_id,
                        evidence_statistics={"model_confidence_uncalibrated":score,"yolo_class_id":0.,
                                             "center_is_bbox_midpoint":1.})
              for rank,(score,box) in enumerate(candidates[:max_candidates])]
    return result,warnings
