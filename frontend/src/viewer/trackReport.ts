import type { AnalysisResult, SequenceInput, Track } from '../types/contracts';
import type { LocalFrame } from './localSequence';

export function trackEvidence(track: Track) {
  const observations = track.points.filter(point => point.point_type === 'observed').sort((a, b) => a.frame_index - b.frame_index);
  const first = observations[0], last = observations.at(-1);
  const displacement = first && last && observations.length > 1
    ? { x_px: last.x_reference_px - first.x_reference_px, y_px: last.y_reference_px - first.y_reference_px } : null;
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
export function buildTrackReport(result: AnalysisResult, manifest: SequenceInput, frames: LocalFrame[], selected: string | null) {
  if (manifest.sequence_id !== result.sequence_id || frames.length !== manifest.frames.length) throw new Error('Report sequence does not match the analysis.');
  const track = selected ? result.tracks.find(item => item.track_id === selected) : undefined;
  if (selected && !track) throw new Error('Selected track is absent from this analysis.');
  const evidence = track ? trackEvidence(track) : null;
  return {
    report_version: '1.0', generated_at: new Date().toISOString(),
    source: { source_type: result.source_type, sequence_id: result.sequence_id, job_id: result.job_id,
      frame_count: frames.length, frames: frames.map((frame, index) => ({ frame_index: index, filename: frame.file.name,
        width_px: frame.width_px, height_px: frame.height_px, timestamp_s: manifest.frames[index].timestamp_s })) },
    counts: { detections: result.detections.length, tracks: result.tracks.length,
      observations: result.tracks.reduce((count, item) => count + item.points.filter(point => point.point_type === 'observed').length, 0) },
    selected_track: track && evidence ? { track_id: track.track_id, status: track.status,
      heuristic_quality: track.quality_score, quality_band: evidence.qualityBand,
      observed_count: evidence.observations.length, linked_detection_count: evidence.observations.filter(point => point.detection_id !== null).length,
      observed_coordinate_frame: result.coordinate_frame, raw_coordinate_frame: 'per_frame_raw_pixels',
      predicted_coordinate_frame: track.trajectory?.coordinate_frame ?? null, units: 'px',
      observations: evidence.observations, predictions: evidence.predictions,
      displacement: evidence.displacement, direction: evidence.direction,
      summary: `${track.track_id}: ${evidence.observations.length} observed positions across frames ${evidence.observations.map(point => point.frame_index + 1).join(', ')}. `
        + `Image-plane direction: ${evidence.direction.toLowerCase()} (${result.coordinate_frame}; top-left origin, positive y downward). `
        + `${evidence.predictions.length} future positions supplied by the backend; predictions are not observations.` } : null,
    limitations: ['Quality is a heuristic support score, not a calibrated probability of debris identity.',
      'Motion is in image-plane pixels; no physical orbit or speed is established.',
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
