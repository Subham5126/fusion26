"""Detection association and track lifecycle management for OrbitTrace.

Complies with Contract 0.1.0 and docs/ALGORITHMS.md (Task T04):
- Gated Euclidean distance association with SciPy linear_sum_assignment
- Constant-velocity motion-aware and nearest-neighbor prediction
- Track lifecycle: tentative -> confirmed (>=3 observations) -> ended (>2 consecutive misses)
- Invariant: observed detections strictly separated from predictions
- Deterministic, CPU-only execution
"""
from dataclasses import dataclass, field
from typing import Literal, Sequence

import numpy as np
from scipy.optimize import linear_sum_assignment

from app.core.config import PipelineConfig
from app.schemas.result import Detection, Track, TrackPoint


def extract_detection_coords(detection: Detection) -> tuple[float, float, float, float]:
    """Extract (x_ref, y_ref, x_raw, y_raw) from a Detection.

    Prefers reference coordinates when both are present; falls back to raw
    coordinates (representing identity alignment) otherwise.
    """
    x_raw = float(detection.x_raw_px)
    y_raw = float(detection.y_raw_px)
    if detection.x_reference_px is not None and detection.y_reference_px is not None:
        x_ref = float(detection.x_reference_px)
        y_ref = float(detection.y_reference_px)
    else:
        x_ref = x_raw
        y_ref = y_raw
    return x_ref, y_ref, x_raw, y_raw


@dataclass
class InternalTrack:
    """Internal mutable tracking state before conversion to frozen schema Track."""

    track_id: str
    points: list[TrackPoint] = field(default_factory=list)
    observed_count: int = 0
    consecutive_misses: int = 0
    status: Literal["tentative", "confirmed", "ended"] = "tentative"
    quality_scores: list[float] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    last_frame_index: int = -1

    def predict_position(
        self, target_frame_index: int, motion_aware: bool = True
    ) -> tuple[float, float]:
        """Predict reference coordinates (x, y) at target_frame_index.

        If motion_aware is True and at least two observed points exist, estimates
        velocity (vx, vy) in px/frame and projects forward. Otherwise holds
        the last observed position.
        """
        if not self.points:
            raise ValueError("Cannot predict position for track with no points")

        last_pt = self.points[-1]
        if not motion_aware or len(self.points) < 2:
            return float(last_pt.x_reference_px), float(last_pt.y_reference_px)

        prev_pt = self.points[-2]
        df = last_pt.frame_index - prev_pt.frame_index
        if df <= 0:
            return float(last_pt.x_reference_px), float(last_pt.y_reference_px)

        vx = (last_pt.x_reference_px - prev_pt.x_reference_px) / df
        vy = (last_pt.y_reference_px - prev_pt.y_reference_px) / df

        dt = target_frame_index - last_pt.frame_index
        pred_x = float(last_pt.x_reference_px + vx * dt)
        pred_y = float(last_pt.y_reference_px + vy * dt)
        return pred_x, pred_y

    def to_schema_track(self) -> Track:
        """Convert internal state to schema-validated Track."""
        q = float(np.mean(self.quality_scores)) if self.quality_scores else 0.5
        q = max(0.0, min(1.0, q))
        return Track(
            track_id=self.track_id,
            status=self.status,
            candidate_label="orbital-object candidate; identity unverified",
            points=list(self.points),
            observed_count=self.observed_count,
            quality_score=q,
            warnings=list(self.warnings),
            trajectory=None,
        )


class Tracker:
    """Gated association and track lifecycle manager (Task T04).

    Implements:
    - Bounded Euclidean distance gating
    - Minimum-cost assignment via scipy.optimize.linear_sum_assignment
    - Tentative -> Confirmed lifecycle (>= confirmation_observations)
    - Consecutive missed detection tracking with termination (max_consecutive_misses)
    - Strict separation of observed detections from predictions
    - Deterministic, unique track IDs
    """

    def __init__(
        self,
        gate_distance_px: float = 20.0,
        confirmation_observations: int = 3,
        max_consecutive_misses: int = 2,
        motion_aware: bool = True,
        track_prefix: str = "track",
        config: PipelineConfig | None = None,
    ) -> None:
        if config is not None:
            self.gate_distance_px = float(config.gate_distance_px)
            self.confirmation_observations = int(config.confirmation_observations)
            self.max_consecutive_misses = int(config.max_consecutive_misses)
        else:
            self.gate_distance_px = float(gate_distance_px)
            self.confirmation_observations = int(confirmation_observations)
            self.max_consecutive_misses = int(max_consecutive_misses)

        self.motion_aware = motion_aware
        self.track_prefix = track_prefix
        self._active_tracks: list[InternalTrack] = []
        self._ended_tracks: list[InternalTrack] = []
        self._next_track_num: int = 1

    def reset(self) -> None:
        """Reset all tracker state for a fresh sequence."""
        self._active_tracks = []
        self._ended_tracks = []
        self._next_track_num = 1

    def _generate_track_id(self) -> str:
        tid = f"{self.track_prefix}-{self._next_track_num:04d}"
        self._next_track_num += 1
        return tid

    def process_frame(
        self,
        frame_index: int,
        detections: Sequence[Detection],
        timestamp_s: float | None = None,
    ) -> list[Track]:
        """Associate detections in frame_index with active tracks and update lifecycle.

        Returns the snapshot of all tracks (active + ended) after this frame.
        """
        # Sort detections deterministically by detection_id to ensure exact reproducibility
        dets = sorted(detections, key=lambda d: d.detection_id)

        m = len(self._active_tracks)
        n = len(dets)

        matched_track_indices: set[int] = set()
        matched_det_indices: set[int] = set()

        if m > 0 and n > 0:
            track_preds = [
                t.predict_position(frame_index, motion_aware=self.motion_aware)
                for t in self._active_tracks
            ]
            det_coords = [extract_detection_coords(d)[:2] for d in dets]

            preds_arr = np.array(track_preds, dtype=np.float64)
            dets_arr = np.array(det_coords, dtype=np.float64)

            diff = preds_arr[:, np.newaxis, :] - dets_arr[np.newaxis, :, :]
            dist_matrix = np.hypot(diff[:, :, 0], diff[:, :, 1])

            # Build cost matrix with penalty for forbidden assignments beyond distance gate
            cost_matrix = dist_matrix.copy()
            penalty = self.gate_distance_px + 1e6
            cost_matrix[dist_matrix > self.gate_distance_px] = penalty

            row_ind, col_ind = linear_sum_assignment(cost_matrix)

            for r, c in zip(row_ind, col_ind):
                d = dist_matrix[r, c]
                if d <= self.gate_distance_px:
                    matched_track_indices.add(int(r))
                    matched_det_indices.add(int(c))
                    self._update_matched_track(
                        self._active_tracks[r], dets[c], frame_index, timestamp_s
                    )

        # Handle unmatched active tracks (missed detections in this frame)
        remaining_active: list[InternalTrack] = []
        for i, track in enumerate(self._active_tracks):
            if i not in matched_track_indices:
                track.consecutive_misses += 1
                if track.consecutive_misses > self.max_consecutive_misses:
                    track.status = "ended"
                    track.warnings.append(
                        f"Track ended after {track.consecutive_misses} consecutive missed frames."
                    )
                    self._ended_tracks.append(track)
                else:
                    remaining_active.append(track)
            else:
                remaining_active.append(track)
        self._active_tracks = remaining_active

        # Handle unmatched detections (start new tentative tracks)
        for j, det in enumerate(dets):
            if j not in matched_det_indices:
                new_track = self._create_new_track(det, frame_index, timestamp_s)
                self._active_tracks.append(new_track)

        return self.get_tracks()

    def _update_matched_track(
        self,
        track: InternalTrack,
        detection: Detection,
        frame_index: int,
        timestamp_s: float | None,
    ) -> None:
        x_ref, y_ref, x_raw, y_raw = extract_detection_coords(detection)
        pt = TrackPoint(
            frame_index=frame_index,
            timestamp_s=timestamp_s,
            x_reference_px=x_ref,
            y_reference_px=y_ref,
            x_raw_px=x_raw,
            y_raw_px=y_raw,
            point_type="observed",
            detection_id=detection.detection_id,
            out_of_field=False,
        )
        track.points.append(pt)
        track.observed_count += 1
        track.consecutive_misses = 0
        track.quality_scores.append(float(detection.quality_score))
        track.last_frame_index = frame_index
        if track.observed_count >= self.confirmation_observations:
            track.status = "confirmed"

    def _create_new_track(
        self,
        detection: Detection,
        frame_index: int,
        timestamp_s: float | None,
    ) -> InternalTrack:
        tid = self._generate_track_id()
        x_ref, y_ref, x_raw, y_raw = extract_detection_coords(detection)
        pt = TrackPoint(
            frame_index=frame_index,
            timestamp_s=timestamp_s,
            x_reference_px=x_ref,
            y_reference_px=y_ref,
            x_raw_px=x_raw,
            y_raw_px=y_raw,
            point_type="observed",
            detection_id=detection.detection_id,
            out_of_field=False,
        )
        return InternalTrack(
            track_id=tid,
            points=[pt],
            observed_count=1,
            consecutive_misses=0,
            status="tentative",
            quality_scores=[float(detection.quality_score)],
            warnings=[],
            last_frame_index=frame_index,
        )

    def process_sequence(
        self,
        detections: Sequence[Detection],
        frame_indices: Sequence[int] | None = None,
        frame_timestamps: dict[int, float] | None = None,
    ) -> list[Track]:
        """Process a sequence of detections organized across frames.

        If frame_indices is provided, steps through every frame in that list
        (including empty frames with 0 detections). Otherwise, determines
        frames from the detections themselves.
        """
        self.reset()

        by_frame: dict[int, list[Detection]] = {}
        for d in detections:
            by_frame.setdefault(d.frame_index, []).append(d)

        if frame_indices is not None:
            frames_to_process = list(frame_indices)
        elif by_frame:
            frames_to_process = list(range(min(by_frame.keys()), max(by_frame.keys()) + 1))
        else:
            frames_to_process = []

        for fi in frames_to_process:
            ts = frame_timestamps.get(fi) if frame_timestamps else None
            frame_dets = by_frame.get(fi, [])
            self.process_frame(fi, frame_dets, timestamp_s=ts)

        return self.get_tracks()

    def get_tracks(
        self, status: Literal["tentative", "confirmed", "ended"] | None = None
    ) -> list[Track]:
        """Return all tracks, sorted deterministically by track_id."""
        all_tracks = [t.to_schema_track() for t in self._active_tracks + self._ended_tracks]
        all_tracks.sort(key=lambda t: t.track_id)
        if status is not None:
            return [t for t in all_tracks if t.status == status]
        return all_tracks

    @property
    def active_tracks(self) -> list[Track]:
        return [t.to_schema_track() for t in self._active_tracks]

    @property
    def ended_tracks(self) -> list[Track]:
        return [t.to_schema_track() for t in self._ended_tracks]
