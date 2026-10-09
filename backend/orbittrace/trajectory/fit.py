"""Constant-velocity image-plane trajectory fitting for OrbitTrace (Task T05).

Complies with Contract 0.1.0 and docs/ALGORITHMS.md:
- Fits linear model:
    x(t) = x0 + vx * (t - t0)
    y(t) = y0 + vy * (t - t0)
  using least-squares regression.
- Uses strictly points with point_type == 'observed' (minimum 3 observations).
- Excludes 'interpolated' and 'extrapolated' points from the fit.
- Computes 2D Euclidean RMSE pixel residuals.
- Generates exactly two future forward extrapolated predictions.
- Supports both time_basis='frame' (px/frame) and time_basis='second' (px/s).
"""
import math
from typing import Sequence

import numpy as np

from app.schemas.base import TimeBasis
from app.schemas.result import Track, TrackPoint, Trajectory


def fit_trajectory(
    points: Sequence[TrackPoint],
    coordinate_frame: str = "reference_frame_0",
    time_basis: TimeBasis = "frame",
    prediction_horizon: int = 2,
    frame_dimensions: tuple[int, int] | None = None,
    frame_timestamps: dict[int, float] | None = None,
) -> Trajectory | None:
    """Fit a constant-velocity trajectory to observed TrackPoints.

    Returns Trajectory if at least three valid observations exist;
    returns None otherwise.
    """
    observed = [p for p in points if p.point_type == "observed"]
    if len(observed) < 3:
        return None

    # Sort observed points by frame_index for strict monotonic ordering
    observed = sorted(observed, key=lambda p: p.frame_index)

    if time_basis == "frame":
        t_vals = [float(p.frame_index) for p in observed]
    elif time_basis == "second":
        for p in observed:
            if p.timestamp_s is None:
                raise ValueError("Second-based trajectory requires valid timestamp_s on all observed points")
        t_vals = [float(p.timestamp_s) for p in observed]
        for a, b in zip(t_vals, t_vals[1:]):
            if b <= a:
                raise ValueError(f"Timestamps must be strictly increasing; got {a} >= {b}")
    else:
        raise ValueError(f"Unsupported time_basis: {time_basis}")

    # Require at least three distinct independent-variable coordinates
    if len(set(t_vals)) < 3:
        return None

    t_arr = np.array(t_vals, dtype=np.float64)
    x_arr = np.array([float(p.x_reference_px) for p in observed], dtype=np.float64)
    y_arr = np.array([float(p.y_reference_px) for p in observed], dtype=np.float64)

    t_mean = float(np.mean(t_arr))
    x_mean = float(np.mean(x_arr))
    y_mean = float(np.mean(y_arr))

    s_tt = float(np.sum((t_arr - t_mean) ** 2))
    if s_tt <= 0.0 or not math.isfinite(s_tt):
        return None

    vx = float(np.sum((t_arr - t_mean) * (x_arr - x_mean)) / s_tt)
    vy = float(np.sum((t_arr - t_mean) * (y_arr - y_mean)) / s_tt)
    speed = float(math.hypot(vx, vy))

    # Reference epoch: choose the first observation's independent coordinate
    t0 = float(t_vals[0])
    x0 = float(x_mean + vx * (t0 - t_mean))
    y0 = float(y_mean + vy * (t0 - t_mean))

    # 2D Euclidean RMSE residual across all fitted observations
    x_pred_obs = x0 + vx * (t_arr - t0)
    y_pred_obs = y0 + vy * (t_arr - t0)
    dx = x_arr - x_pred_obs
    dy = y_arr - y_pred_obs
    rmse = float(np.sqrt(np.mean(dx**2 + dy**2)))
    if rmse < 1e-12:
        rmse = 0.0

    # Generate forward extrapolation predictions
    last_frame = observed[-1].frame_index
    predictions: list[TrackPoint] = []

    for step in range(1, prediction_horizon + 1):
        pred_frame = last_frame + step

        if time_basis == "frame":
            pred_t = float(pred_frame)
            pred_ts = None
        else:
            if frame_timestamps and pred_frame in frame_timestamps:
                pred_ts = float(frame_timestamps[pred_frame])
            else:
                df_span = last_frame - observed[0].frame_index
                dt_span = t_vals[-1] - t_vals[0]
                dt_per_frame = dt_span / df_span if df_span > 0 else dt_span / (len(t_vals) - 1)
                pred_ts = float(t_vals[-1] + step * dt_per_frame)
            pred_t = pred_ts

        pred_x = float(x0 + vx * (pred_t - t0))
        pred_y = float(y0 + vy * (pred_t - t0))

        if frame_dimensions is not None:
            w, h = frame_dimensions
            oof = not (0.0 <= pred_x < w and 0.0 <= pred_y < h)
        else:
            oof = None

        predictions.append(
            TrackPoint(
                frame_index=pred_frame,
                timestamp_s=pred_ts,
                x_reference_px=pred_x,
                y_reference_px=pred_y,
                x_raw_px=None,
                y_raw_px=None,
                point_type="extrapolated",
                detection_id=None,
                out_of_field=oof,
            )
        )

    speed_unit = "px/frame" if time_basis == "frame" else "px/s"

    return Trajectory(
        model="constant_velocity",
        coordinate_frame=coordinate_frame,
        time_basis=time_basis,
        vx=vx,
        vy=vy,
        speed=speed,
        speed_unit=speed_unit,
        fit_rmse_px=rmse,
        observations_used=len(observed),
        reference_epoch=t0,
        x_at_epoch_px=x0,
        y_at_epoch_px=y0,
        predictions=predictions,
    )


def fit_track_trajectory(
    track: Track,
    coordinate_frame: str = "reference_frame_0",
    time_basis: TimeBasis = "frame",
    prediction_horizon: int = 2,
    frame_dimensions: tuple[int, int] | None = None,
    frame_timestamps: dict[int, float] | None = None,
) -> Track:
    """Fit trajectory for a single Track and return an updated Track instance."""
    traj = fit_trajectory(
        points=track.points,
        coordinate_frame=coordinate_frame,
        time_basis=time_basis,
        prediction_horizon=prediction_horizon,
        frame_dimensions=frame_dimensions,
        frame_timestamps=frame_timestamps,
    )
    return Track(
        track_id=track.track_id,
        status=track.status,
        candidate_label=track.candidate_label,
        points=list(track.points),
        observed_count=track.observed_count,
        quality_score=track.quality_score,
        warnings=list(track.warnings),
        trajectory=traj,
    )


def attach_trajectories(
    tracks: Sequence[Track],
    coordinate_frame: str = "reference_frame_0",
    time_basis: TimeBasis = "frame",
    prediction_horizon: int = 2,
    frame_dimensions: tuple[int, int] | None = None,
    frame_timestamps: dict[int, float] | None = None,
) -> list[Track]:
    """Fit and attach trajectories to all tracks in a sequence."""
    return [
        fit_track_trajectory(
            t,
            coordinate_frame=coordinate_frame,
            time_basis=time_basis,
            prediction_horizon=prediction_horizon,
            frame_dimensions=frame_dimensions,
            frame_timestamps=frame_timestamps,
        )
        for t in tracks
    ]
