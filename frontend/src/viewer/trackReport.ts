import type { AnalysisResult, SequenceInput, Track } from '../types/contracts';
import type { LocalFrame } from './localSequence';
import { candidateAssessment, originalCandidates } from './candidateAssessment';
import { isSupportedTrack } from './resultReview';

export function trackEvidence(track: Track, history: 'registered' | 'original' = 'registered') {
  const observations = track.points.filter(point => point.point_type === 'observed').sort((a, b) => a.frame_index - b.frame_index);
  const first = observations[0], last = observations.at(-1);
  const displacement = first && last && observations.length > 1
    ? history === 'original'
      ? first.x_raw_px !== null && last.x_raw_px !== null && first.y_raw_px !== null && last.y_raw_px !== null
        ? { x_px:last.x_raw_px-first.x_raw_px, y_px:last.y_raw_px-first.y_raw_px } : null
      : { x_px: last.x_reference_px - first.x_reference_px, y_px: last.y_reference_px - first.y_reference_px } : null;
  const directions = ['right', 'lower right', 'down', 'lower left', 'left', 'upper left', 'up', 'upper right'];
  const direction = !displacement ? 'Insufficient observations'
    : Math.hypot(displacement.x_px, displacement.y_px) < 1e-6 ? 'No net displacement'
    : directions[(Math.round(Math.atan2(displacement.y_px, displacement.x_px) / (Math.PI / 4)) + 8) % 8];
  const predictions = (track.trajectory?.predictions ?? []).filter(point => point.point_type === 'extrapolated'
    && last && point.frame_index > last.frame_index).sort((a, b) => a.frame_index - b.frame_index);
  return { observations, predictions, displacement, direction,
    qualityBand: track.quality_score < .4 ? 'low' : track.quality_score < .7 ? 'medium' : 'high' };
}

// A separate report envelope: the shared AnalysisResult 0.1.0 is preserved verbatim.
// Reference positions are deliberately not relabeled as displayed raw pixels.
export function buildTrackReport(result: AnalysisResult, manifest: SequenceInput, frames: LocalFrame[], selected: string | null, diagnostics: unknown = null) {
  if (manifest.sequence_id !== result.sequence_id || frames.length !== manifest.frames.length) throw new Error('Report sequence does not match the analysis.');
  const track = selected ? result.tracks.find(item => item.track_id === selected) : undefined;
  if (selected && !track) throw new Error('Selected track is absent from this analysis.');
  const evidence = track ? trackEvidence(track) : null;
  return {
    report_version: '1.1', generated_at: new Date().toISOString(),
    candidate_assessment: candidateAssessment(result, diagnostics),
    original_candidates_before_motion_mode: originalCandidates(result, diagnostics),
    source: { source_type: result.source_type, sequence_id: result.sequence_id, job_id: result.job_id,
      frame_count: frames.length, frames: frames.map((frame, index) => ({ frame_index: index, filename: frame.file.name,
        width_px: frame.width_px, height_px: frame.height_px, timestamp_s: manifest.frames[index].timestamp_s })) },
    counts: { detections: result.detections.length, tracks: result.tracks.length,
      observations: result.tracks.reduce((count, item) => count + item.points.filter(point => point.point_type === 'observed').length, 0) },
    detection_summary: {
      per_frame: manifest.frames.map(frame => ({ frame_index: frame.frame_index,
        count: result.detections.filter(d => d.frame_index === frame.frame_index).length })),
      association_confirmed: result.tracks.filter(t => t.status === 'confirmed').length,
      tentative: result.tracks.filter(t => t.status === 'tentative').length,
      ended: result.tracks.filter(t => t.status === 'ended').length,
      supported_motion_tracks: result.tracks.filter(isSupportedTrack).length,
      uncertain_candidate_tracks: result.tracks.filter(t => !isSupportedTrack(t)).length,
    },
    selected_track: track && evidence ? { track_id: track.track_id, status: track.status,
      heuristic_quality: track.quality_score, quality_band: evidence.qualityBand,
      observed_count: evidence.observations.length, linked_detection_count: evidence.observations.filter(point => point.detection_id !== null).length,
      missing_observation_frames: manifest.frames.filter(frame => !evidence.observations.some(p => p.frame_index === frame.frame_index)).map(frame => frame.frame_index),
      detections: result.detections.filter(d => evidence.observations.some(p => p.detection_id === d.detection_id)),
      observed_coordinate_frame: result.coordinate_frame, raw_coordinate_frame: 'per_frame_raw_pixels',
      predicted_coordinate_frame: track.trajectory?.coordinate_frame ?? null, units: 'px',
      prediction_model: track.trajectory?.model ?? null, prediction_uncertainty: null,
      observations: evidence.observations, predictions: evidence.predictions,
      displacement: evidence.displacement, direction: evidence.direction,
      summary: `${track.track_id}: ${evidence.observations.length} observed positions across frames ${evidence.observations.map(point => point.frame_index + 1).join(', ')}. `
        + `Image-plane direction: ${evidence.direction.toLowerCase()} (${result.coordinate_frame}; top-left origin, positive y downward). `
        + `${evidence.predictions.length} future positions supplied by the backend; predictions are not observations.` } : null,
    limitations: ['Quality is a heuristic support score, not a calibrated probability of debris identity.',
      'Motion is in image-plane pixels; no physical orbit or speed is established.',
      'Unknown timestamps and absent image calibration prevent physical-speed estimates.',
      'False positives and missed detections remain possible. Predictions are conditional model estimates; uncertainty is unavailable.',
      'Frame indices in data are zero-based. Summary frame numbers are one-based. Missing observations are not filled in.'],
    analysis_result: result,
  };
}

export function downloadTrackReport(report: ReturnType<typeof buildTrackReport>) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `orbittrace-${report.source.job_id}-${report.selected_track?.track_id ?? 'analysis'}.json`.replace(/[^\w.-]/g, '_');
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  // Allow the browser to consume the Blob before releasing it.
  window.setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
