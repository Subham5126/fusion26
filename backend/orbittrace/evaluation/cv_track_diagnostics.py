"""Offline CV-TRACK-01 probes: existing tracker decisions, never inference truth.

Instrumentation replays the actual Tracker. Private active prediction state is
observed only here; no association algorithm or lifecycle implementation is copied.
"""
from collections import Counter
import numpy as np
from app.core.config import PipelineConfig
from orbittrace.tracking.tracker import Tracker, extract_detection_coords


def summarize_result(result):
    return {"status": result.status,
            "detections_per_frame": [sum(d.frame_index == i for d in result.detections) for i in range(5)],
            "lifecycle": dict(Counter(t.status for t in result.tracks)),
            "tracks": len(result.tracks), "confirmed_tracks": sum(t.status == "confirmed" for t in result.tracks),
            "fits": sum(t.trajectory is not None for t in result.tracks),
            "support_histogram": dict(sorted(Counter(t.observed_count for t in result.tracks).items())),
            "time_basis": result.time_basis, "coordinate_frame": result.coordinate_frame,
            "scores_per_frame": [{"frame_index": i, "quantiles_min_q25_median_q75_max":
                np.percentile([d.quality_score for d in result.detections if d.frame_index == i], [0,25,50,75,100]).tolist()
                if any(d.frame_index == i for d in result.detections) else None} for i in range(5)]}


def trace_associations(detections, *, config=None, frame_indices=range(5), frame_timestamps=None):
    """Record predictions, ALL distances, gate rejections, births/matches/misses.

    Full pair traces are for the small offline diagnostics only, not HTTP. They
    consume no labels, and call the actual prediction and assignment methods.
    """
    frames = []
    class RecordingTracker(Tracker):
        def process_frame(self, frame_index, detections, timestamp_s=None):
            before = list(self._active_tracks)
            dets = sorted(detections, key=lambda d: d.detection_id)
            predictions = [t.predict_position(frame_index, motion_aware=self.motion_aware) for t in before]
            pairs = [{"track_id": t.track_id, "detection_id": d.detection_id,
                      "distance_px": float(np.linalg.norm(np.asarray(prediction)-extract_detection_coords(d)[:2])),
                      "within_gate": bool(np.linalg.norm(np.asarray(prediction)-extract_detection_coords(d)[:2]) <= self.gate_distance_px)}
                     for t,prediction in zip(before,predictions) for d in dets]
            output = super().process_frame(frame_index, detections, timestamp_s)
            assigned = {p.detection_id:t.track_id for t in output for p in t.points if p.frame_index == frame_index and p.point_type == "observed"}
            for pair in pairs:
                pair["selected"] = assigned.get(pair["detection_id"]) == pair["track_id"]
            previous = {t.track_id for t in before}
            matched = {track for track in assigned.values() if track in previous}
            frames.append({"frame_index":frame_index, "timestamp_s":timestamp_s,
                "gate_distance_px":self.gate_distance_px,
                "predictions":[{"track_id":t.track_id,"reference_xy_px":list(pred)} for t,pred in zip(before,predictions)],
                "pairs":pairs, "births":[track for track in assigned.values() if track not in previous],
                "missed_tracks":sorted(previous-matched), "assignments":assigned})
            return output
    tracker = RecordingTracker(config=config or PipelineConfig())
    tracks = tracker.process_sequence(detections, frame_indices=frame_indices, frame_timestamps=frame_timestamps)
    return {"frames":frames, "tracks":[t.model_dump(mode="json") for t in tracks],
            "confirmation_observations":tracker.confirmation_observations,
            "max_consecutive_misses":tracker.max_consecutive_misses,
            "scope":"actual tracker replay; no ESA identity truth assumed"}


def evaluate_synthetic_models(result, truth):
    """Member 3 evaluator, using authored reference truth in declared ref space.

    Post-inference only. Crossing identity ambiguity is not masked by this legacy
    evaluator; the companion evaluate_stress report states excluded ambiguity.
    """
    from orbittrace.evaluation.evaluator import GroundTruthPoint, evaluate_tracks
    points = [GroundTruthPoint(frame_index=f["frame_index"],
              x=obj["reference_xy_px"][0], y=obj["reference_xy_px"][1],
              target_id=obj["object_id"], visible=obj["visible"])
              for f in truth["frames"] for obj in f["objects"]]
    metrics, tracking = evaluate_tracks(result.tracks, points,
        benchmark_id="cv-track-synthetic", split="development", matching_gate_px=5.)
    return {"metrics": metrics.model_dump(mode="json"), "tracking": tracking,
            "coordinate_frame": "reference_frame_0",
            "scope": "authored synthetic reference truth; legacy evaluator does not exclude coincident identity ambiguity"}


def evaluate_raw_detection_models(detections, annotations):
    """Member 3 raw-point evaluator; remove optional references on new copies.

    Its coordinate extractor prefers references, so passing registered detections
    directly against ESA raw labels would be a coordinate-space integration bug.
    No source Detection or shared schema is modified.
    """
    from app.schemas.result import Detection
    from orbittrace.evaluation.evaluator import GroundTruthPoint, evaluate_detections
    raw = [Detection.model_validate({**d.model_dump(), "x_reference_px":None,"y_reference_px":None}) for d in detections]
    truth = [GroundTruthPoint(frame_index=f.frame_index, x=xy[0], y=xy[1], target_id=None)
             for f in annotations for xy in f.object_coords]
    return evaluate_detections(raw,truth,benchmark_id="cv-track-esa-diagnostic",split="development",matching_gate_px=5.)
