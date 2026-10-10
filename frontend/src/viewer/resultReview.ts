import type { AnalysisResult, Track } from '../types/contracts';
import type { ScientificOverlayModel } from './scientificOverlay';

// A review/display threshold, not a reclassification or calibrated probability.
// Preserve the unmodified backend result for exports and candidate inspection.
export function isSupportedTrack(track: Track) {
  const points = track.points.filter(point => point.point_type === 'observed');
  // Repeated stationary stars are associations, not supported motion evidence.
  const span = points.length ? Math.hypot(Math.max(...points.map(p=>p.x_reference_px))-Math.min(...points.map(p=>p.x_reference_px)),
    Math.max(...points.map(p=>p.y_reference_px))-Math.min(...points.map(p=>p.y_reference_px))) : 0;
  return points.length >= 3 && span >= 2
    && track.quality_score >= .5 && track.trajectory !== null
    && (track.trajectory.fit_rmse_px === null || track.trajectory.fit_rmse_px <= 3);
}
export function reviewTracks(result: AnalysisResult, showCandidates: boolean) {
  return result.tracks.filter(track => showCandidates || isSupportedTrack(track));
}
export function reviewOverlay(model: ScientificOverlayModel, result: AnalysisResult, showCandidates: boolean, frameIndex: number): ScientificOverlayModel {
  const ids = new Set(reviewTracks(result, showCandidates).map(track => track.track_id));
  return { ...model,
    detections: model.detections.filter(detection => showCandidates || (detection.trackId !== undefined && ids.has(detection.trackId))),
    tracks: model.tracks.filter(track => ids.has(track.id)).map(track => {
      const predictions = track.predictions.filter(point => point.frame > frameIndex && point.frame <= frameIndex + 1);
      // The forecast origin is already projected into the displayed frame. Original
      // historical positions may belong to earlier images and cannot replace it.
      const origin = track.forecast[0] ?? track.observed.at(-1);
      return { ...track, predictions, forecast: predictions.length && origin ? [origin, ...predictions] : [] };
    }),
  };
}
