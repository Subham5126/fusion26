"""Substantive malformed-label, split-leakage, native box and matching checks."""
import json

import pytest

from experiments.yolo.adapter import to_detections
from experiments.yolo.audit import parse_labels
from experiments.yolo.evaluate import match_boxes
from experiments.yolo.prepare import select_membership


@pytest.mark.parametrize("text", ["0 .5 .5 0 .2", "0 .5 .5 .2 0", "1 .5 .5 .2 .2",
                                    "0 nan .5 .2 .2", "0 .1 .5 .5 .2", "0 .5 .5 .2", "0 .5 .5 .2 .2 .3"])
def test_bad_labels_rejected(text):
    with pytest.raises(ValueError):parse_labels(text)


def test_empty_and_edge_labels():
    assert parse_labels(" \n") == []
    assert parse_labels("0 0.5 0.5 1 1")==[[0,.5,.5,1.,1.]]


def test_split_membership_never_moves_images_and_filters_leakage():
    rows=[{"image":f"{s}/{i}.jpeg","split":s,"boxes":[[0,.5,.5,.2,.2]]}
          for s in ("train","validation","test") for i in range(3)]
    audit={"records":rows,"errors":[],"orphan_labels":[],"duplicates":[{"type":"file_sha256","images":["train/0.jpeg","test/0.jpeg"]}],
           "cross_split_near_pairs":[{"left":"train/1.jpeg","right":"validation/1.jpeg"}]}
    chosen,smoke,excluded=select_membership(audit)
    assert "train/0.jpeg" in excluded and "train/1.jpeg" in excluded
    assert "test/0.jpeg" in chosen["test"]
    assert "validation/1.jpeg" in chosen["validation"]
    assert smoke==chosen["train"]
    assert all(path.startswith(split+"/") for split,paths in chosen.items() for path in paths)


def test_invalid_labels_require_explicit_exclusion():
    audit={"records":[{"image":"train/bad.jpeg","split":"train","boxes":[]}],
           "errors":[{"image":"train/bad.jpeg","error":"zero width"}],"orphan_labels":[],"duplicates":[],"cross_split_near_pairs":[]}
    with pytest.raises(ValueError):select_membership(audit)
    chosen,_,excluded=select_membership(audit,exclude_invalid=True)
    assert chosen["train"]==[] and "train/bad.jpeg" in excluded


def test_original_edge_boxes_confidence_and_frame_ids():
    kwargs=dict(width=640,height=480,sequence_id="native",model_id="yolo26n-test")
    first,_=to_detections([[639,479,640,480],[0,0,20,10]],[.5,.9],[0,0],frame_index=0,**kwargs)
    second,_=to_detections([[639,479,640,480]],[.5],[0],frame_index=1,**kwargs)
    assert first[0].quality_score==.9 and first[0].kind=="streak"
    edge=first[1]
    assert (edge.x_raw_px,edge.y_raw_px)==(639.5,479.5)
    assert edge.bbox_raw_px==(639.,479.,640.,480.)
    assert edge.x_reference_px is None
    assert edge.evidence_statistics["model_confidence_uncalibrated"]==.5
    assert {d.detection_id for d in first}.isdisjoint(d.detection_id for d in second)
    json.dumps([d.model_dump() for d in first+second],allow_nan=False)


@pytest.mark.parametrize("box,score,cls", [([0,0,0,2],.5,0),([-1,0,2,2],.5,0),
                                          ([0,0,641,2],.5,0),([0,0,2,float('inf')],.5,0),
                                          ([0,0,2,2],float('nan'),0),([0,0,2,2],1.1,0),([0,0,2,2],.5,1)])
def test_invalid_prediction_geometry_or_class_rejected(box,score,cls):
    with pytest.raises(ValueError):to_detections([box],[score],[cls],width=640,height=480,frame_index=0,sequence_id="bad")


def test_cap_explicit_empty_and_mismatched_outputs():
    kwargs=dict(width=64,height=64,frame_index=0,sequence_id="cap")
    output,messages=to_detections([[0,0,2,2],[10,10,12,12]],[.2,.8],[0,0],max_candidates=1,**kwargs)
    assert len(output)==1 and output[0].quality_score==.8 and len(messages)==1
    assert to_detections([],[],[],**kwargs)==([],[])
    with pytest.raises(ValueError):to_detections([[0,0,2,2]],[],[],**kwargs)


def test_box_matching_one_to_one_and_forbidden_unmatched():
    pairs,fp,fn=match_boxes([[0,0,10,10],[0,0,10,10],[100,100,110,110]],[[0,0,10,10],[40,40,50,50]])
    assert len(pairs)==1 and len(fp)==2 and fn==[1]
    assert pairs[0][2]==1.
    assert match_boxes([],[[0,0,10,10]])==([],[],[0])
