"""Generate new, actual CV-TRACK-01 results/overlays; never overwrite reports."""
import argparse
from collections import Counter
import hashlib
import html
import inspect
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw

from app.core.config import PipelineConfig
from app.schemas.result import AnalysisResult, Detection
from app.schemas.sequence import SequenceInput
from astrotrace.datasets import SpotGeoDataset
from astrotrace.datasets.stress import create_stress_scene
from astrotrace.datasets.validation import discover_annotations
from astrotrace.detection.evaluation import match_points, summarize_frames
from astrotrace.detection.stress_evaluation import evaluate_stress
from astrotrace.preprocessing.registration import warp_to_reference
from astrotrace.preprocessing.registration_fixtures import create_registration_fixture
from orbittrace.cv_tracking import analyze_telescope_sequence, TelescopeAnalysisError
from orbittrace.evaluation.cv_track_diagnostics import summarize_result, trace_associations, evaluate_synthetic_models, evaluate_raw_detection_models


def metadata(frames, name, source="synthetic", timestamps=None):
    return SequenceInput(schema_version="0.1.0", sequence_id=name, source_type=source, profile="spotgeo",
        frames=[{"frame_index":i,"image_ref":f"frame_{i}","width_px":p.shape[1],"height_px":p.shape[0],
                 "timestamp_s":None if timestamps is None else timestamps[i]} for i,p in enumerate(frames)])


def one_object_frames(seed=101):
    # Authored image generator: adds a moving target to the existing star/noise
    # scene. The generator's parameters/truth never enter inference.
    background = create_stress_scene("empty_targets",seed=seed)
    yy,xx=np.mgrid[:240,:320]
    return tuple(np.rint(np.clip(p.astype(float)+55*np.exp(-.5*((xx-(38+4.5*i))/1.2)**2-.5*((yy-(90-.1*i))/1.2)**2),0,255)).astype(np.uint8)
                 for i,p in enumerate(background.frames))


def write_json(path, data):
    with path.open("x",encoding="utf-8") as handle:
        json.dump(data,handle,indent=2,allow_nan=False)
        handle.write("\n")


def overlays(folder, frames, result, diagnostic):
    # Scientific plotting, using actual reference_to_raw for every track point.
    # No reference point is drawn directly on a raw image.
    registration=diagnostic.get("registration")
    detections=result.detections if result else [Detection.model_validate(d) for d in diagnostic.get("detections",[])]
    owners={p.detection_id:t.track_id for t in (result.tracks if result else []) for p in t.points}
    for index,pixels in enumerate(frames):
        scale=float(np.iinfo(pixels.dtype).max) if pixels.dtype.kind=="u" else 1.
        gray=np.rint(np.clip(pixels.astype(float)/scale,0,1)*255).astype(np.uint8)
        image=Image.fromarray(gray).convert("RGB"); draw=ImageDraw.Draw(image)
        for d in detections:
            if d.frame_index==index:
                x0,y0,x1,y1=d.bbox_raw_px
                draw.rectangle((x0,y0,x1-1,y1-1),outline="yellow",width=1)
                if d.detection_id not in owners and not (diagnostic.get("status")=="failed"):
                    draw.text((d.x_raw_px+3,d.y_raw_px+3),d.detection_id[-5:],fill="yellow")
        frame_reg=registration["frames"][index] if registration else None
        if result and frame_reg and frame_reg["reference_to_raw"] is not None:
            matrix=np.asarray(frame_reg["reference_to_raw"])
            def project(point):
                return tuple((matrix@np.array([point.x_reference_px,point.y_reference_px,1]))[:2])
            for track in result.tracks:
                observed=[p for p in track.points if p.point_type=="observed" and p.frame_index<=index]
                for a,b in zip(observed,observed[1:]):
                    if b.frame_index==a.frame_index+1: draw.line([project(a),project(b)],fill="cyan",width=1)
                if observed and observed[-1].frame_index==index:
                    x,y=project(observed[-1]); draw.text((x+3,y+3),track.track_id,fill="cyan")
                if track.trajectory and index>=track.points[-1].frame_index:
                    for prediction in track.trajectory.predictions:
                        x,y=project(prediction); draw.ellipse((x-2,y-2,x+2,y+2),outline="orange")
        if frame_reg and frame_reg["status"]=="failed":
            draw.text((5,5),"REGISTRATION REJECTED",fill="red")
            draw.text((5,20),"No aligned tracking",fill="red")
            import textwrap
            for row,text in enumerate(textwrap.wrap(", ".join(frame_reg["warnings"]),width=45)):
                draw.text((5,35+row*13),text,fill="red")
        image.save(folder/f"raw_{index}.png")
        if frame_reg and frame_reg["status"] != "failed":
            # Use original accepted transform with explicit border mask.
            from astrotrace.preprocessing.registration import FrameRegistration
            mapped,mask=warp_to_reference(pixels,FrameRegistration(**frame_reg))
            aligned=Image.fromarray(np.rint(np.clip(mapped,0,1)*255).astype(np.uint8)).convert("RGB")
            pen=ImageDraw.Draw(aligned)
            for d in (result.detections if result else []):
                if d.frame_index==index:
                    x,y=d.x_reference_px,d.y_reference_px
                    pen.ellipse((x-2,y-2,x+2,y+2),outline="yellow")
            pen.text((5,5),"REFERENCE FRAME 0: masked preview",fill="cyan")
            aligned.save(folder/f"reference_{index}.png")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--esa",type=Path)
    args=parser.parse_args(); args.output.mkdir(parents=True,exist_ok=False)
    report={"scope":"actual algorithm outputs; ESA diagnostic samples are previously used, not tuning data",
            "signature":str(inspect.signature(analyze_telescope_sequence)),"scenarios":{},"development_probes":{}}
    successful={}
    def run(name,frames,source="synthetic",truth=None,method="optimized"):
        folder=args.output/name; folder.mkdir()
        sequence=metadata(frames,name,source); diagnostic={}
        write_json(folder/"sequence.json",sequence.model_dump(mode="json"))
        try:
            result=analyze_telescope_sequence(frames,sequence=sequence,method=method,diagnostics=diagnostic)
            serialized=result.model_dump(mode="json")
            AnalysisResult.model_validate_json(json.dumps(serialized,allow_nan=False))
            write_json(args.output/f"{name}.json",serialized)
            summary=summarize_result(result)
            trace=trace_associations(result.detections,config=PipelineConfig(profile=sequence.profile))
            assert [(t["track_id"],t["observed_count"]) for t in trace["tracks"]]==[(t.track_id,t.observed_count) for t in result.tracks]
            write_json(folder/"association_trace.json",trace)
            if truth:
                summary["synthetic_evaluation"]=evaluate_stress(result.detections,result.tracks,truth)
                summary["member3_evaluation"]=evaluate_synthetic_models(result,truth)
            successful[name]=(result,frames)
        except TelescopeAnalysisError as exc:
            result=None
            write_json(args.output/f"{name}.json",exc.as_job_state().model_dump(mode="json"))
            summary={"status":"failed","error":exc.error.model_dump(mode="json"),"tracks":None,"fits":None}
        write_json(folder/"diagnostics.json",diagnostic)
        summary["native_input_sha256"]=[hashlib.sha256(p.tobytes()).hexdigest() for p in frames]
        summary["runtime_ms"]=diagnostic["runtime_ms"]
        report["scenarios"][name]=summary
        overlays(folder,frames,result,diagnostic)
        print(name,summary["status"],summary.get("detections_per_frame"),summary.get("lifecycle"),summary.get("fits"))
        return result
    run("synthetic_success",one_object_frames())
    base=create_stress_scene("empty_targets",seed=101).frames[0]
    rng=np.random.default_rng(101)
    stationary=tuple(np.rint(np.clip(base.astype(float)+rng.normal(0,.2,base.shape),0,255)).astype(np.uint8) for _ in range(5))
    run("stationary_stars",stationary)
    for name,case in [("multi_object_success","counts_change"),("crossing","crossing"),("empty_success","empty_targets"),
                      ("false_detections","artifacts"),("camera_motion","camera_motion"),("unsuitable_input","daylight_like"),("uncertain_input","noise_only")]:
        scene=create_stress_scene(case); run(name,scene.frames,truth=scene.truth)
    failure=list(create_registration_fixture().frames)
    failure[1]=cv2.warpAffine(failure[0],cv2.getRotationMatrix2D((128,96),5,1),(256,192))
    run("registration_failure",failure)
    run("baseline_success",one_object_frames(),method="baseline")
    # Controlled development seeds; fixed gate/confirmation/config, no tuning.
    for seed in (101,102,103):
        scene=create_stress_scene("counts_change",seed=seed)
        result=analyze_telescope_sequence(scene.frames,sequence=metadata(scene.frames,f"development-{seed}"))
        report["development_probes"][str(seed)]=evaluate_stress(result.detections,result.tracks,scene.truth)
    if args.esa:
        dataset=SpotGeoDataset(args.esa,split="train")
        for key in ("84","438"):
            seq=dataset.load_sequence(key)
            run(f"real_esa_train{key}",tuple(f.pixels for f in seq.frames),source="real")
        # Labels are loaded only AFTER all inference, for raw-point evaluation.
        label_name,labels,label_hash=discover_annotations(dataset)
        report["esa_evaluation"]={"annotation_sha256":label_hash,"label_file":label_name,
            "identity_metrics":None,"identity_null_reason":"ESA point array order is not persistent identity truth","sequences":{}}
        for key in ("84","438"):
            name=f"real_esa_train{key}"
            if name not in successful: continue
            result,_=successful[name]
            scores=[]
            for f in labels.for_sequence(key):
                points=[(d.x_raw_px,d.y_raw_px) for d in result.detections if d.frame_index==f.frame_index]
                scores.append({"frame_index":f.frame_index,**match_points(points,f.object_coords,5.)})
            report["esa_evaluation"]["sequences"][key]={"cv_raw_point_metrics":summarize_frames(scores,[]),
                "member3_raw_point_metrics":evaluate_raw_detection_models(result.detections,labels.for_sequence(key)).model_dump(mode="json")}
    write_json(args.output/"report.json",report)
    sections=[]
    for name,summary in report["scenarios"].items():
        image_index = 4
        if summary.get("error",{}).get("code")=="registration_failed":
            diagnostic=json.loads((args.output/name/"diagnostics.json").read_text(encoding="utf-8"))
            image_index=next(frame["frame_index"] for frame in diagnostic["registration"]["frames"] if frame["status"]=="failed")
        sections.append(f'<section><h2>{html.escape(name)}</h2><p>{html.escape(json.dumps(summary))}</p><a href="{name}.json">Contract JSON</a> <a href="{name}/diagnostics.json">Diagnostics</a><br><img src="{name}/raw_{image_index}.png" alt="Actual raw overlay">'+
                        (f'<img src="{name}/reference_4.png" alt="Accepted reference preview">' if (args.output/name/'reference_4.png').exists() else '')+'</section>')
    (args.output/"index.html").write_text('<!doctype html><meta charset="utf-8"><title>CV-TRACK-01 actual evidence</title><style>body{background:#101923;color:#ddd;font:15px sans-serif;padding:20px}img{max-width:48%;height:auto}p{overflow-wrap:anywhere}a{color:#6df}</style><h1>Actual CV + tracking outputs</h1><p>Yellow raw detections, cyan observed paths/IDs, orange extrapolated predictions. Reference points are mapped through the accepted inverse on raw images. Candidate identity unverified.</p>'+''.join(sections),encoding="utf-8")


if __name__=="__main__":
    main()
