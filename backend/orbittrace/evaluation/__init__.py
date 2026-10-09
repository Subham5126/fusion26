"""OrbitTrace orbittrace/evaluation package; Task T06 implementation."""
from .evaluator import (
    GroundTruthPoint,
    create_sequence_splits,
    evaluate_detections,
    evaluate_tracks,
    match_points_frame,
)

__all__ = [
    "GroundTruthPoint",
    "evaluate_detections",
    "evaluate_tracks",
    "create_sequence_splits",
    "match_points_frame",
]
