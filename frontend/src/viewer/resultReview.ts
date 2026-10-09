import type { AnalysisResult, Track } from '../types/contracts';
import type { ScientificOverlayModel } from './scientificOverlay';

// A review/display threshold, not a reclassification or calibrated probability.
// Preserve the unmodified backend result for exports and candidate inspection.
export function isSupportedTrack(track: Track) {
  return track.points.filter(point => point.point_type === 'observed').length >= 3
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
      const last = track.observed.at(-1);
      return { ...track, predictions, forecast: predictions.length && last ? [last, ...predictions] : [] };
    }),
  };
}
