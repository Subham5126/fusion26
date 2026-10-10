import type { Track } from '../../types/contracts';
import { trackEvidence } from '../../viewer/trackReport';

export function TrackQualityPanel({ track, coordinateFrame }: { track: Track; coordinateFrame: string }) {
  const evidence = trackEvidence(track, coordinateFrame === 'per_frame_raw_pixels' ? 'original' : 'registered');
  return <section className="track-quality-panel" aria-label="Selected track confidence">
    <div className="track-quality-heading"><span>Heuristic quality</span><strong>{(track.quality_score * 100).toFixed(1)}%</strong></div>
    <div className={`track-confidence-bar quality-${evidence.qualityBand}`} role="meter" aria-label="Track heuristic quality"
      aria-valuemin={0} aria-valuemax={1} aria-valuenow={track.quality_score} aria-valuetext={`${(track.quality_score * 100).toFixed(1)}%, ${evidence.qualityBand} heuristic support`}>
      <span style={{ width: `${track.quality_score * 100}%` }} /></div>
    <p className="quality-explanation">{evidence.qualityBand} support · quality {track.quality_score.toFixed(3)} / 1. Not a debris probability.</p>
    <dl className="evidence-values"><div><dt>Track ID</dt><dd>{track.track_id}</dd></div><div><dt>Actual observations</dt><dd>{evidence.observations.length}</dd></div>
      <div><dt>Image-plane direction</dt><dd>{evidence.direction}</dd></div></dl>
    <p className="quality-explanation">Direction in {coordinateFrame}; image y increases downward.</p>
  </section>;
}
