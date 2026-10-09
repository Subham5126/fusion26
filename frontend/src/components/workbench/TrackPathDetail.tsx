import type { Track } from '../../types/contracts';
import { trackEvidence } from '../../viewer/trackReport';
import { trackColors } from '../../viewer/trackColors';

export function TrackPathDetail({ track, frameIndex, coordinateFrame, visibility }: {
  track: Track; frameIndex: number; coordinateFrame: string;
  visibility: { tracks: boolean; predictions: boolean };
}) {
  const evidence = trackEvidence(track), colors = trackColors(track.track_id);
  const observed = evidence.observations.filter(point => point.frame_index <= frameIndex);
  const last = evidence.observations.at(-1);
  const predicted = track.trajectory?.coordinate_frame === coordinateFrame ? evidence.predictions : [];
  const all = [...evidence.observations, ...predicted];
  if (!all.length) return null;
  const xs = all.map(point => point.x_reference_px), ys = all.map(point => point.y_reference_px);
  const left = Math.min(...xs), top = Math.min(...ys), span = Math.max(Math.max(...xs) - left, Math.max(...ys) - top, 1);
  const pad = span * .2, viewSize = span + pad * 2, unit = viewSize / 160;
  const points = (items: typeof observed) => items.map(point => `${point.x_reference_px},${point.y_reference_px}`).join(' ');
  const showForecast = visibility.predictions && last && frameIndex >= last.frame_index && predicted.length > 0;
  return <section className="track-path-detail" aria-label="Enlarged selected track path">
    <strong>Selected path detail</strong>
    <p>Enlarged {coordinateFrame} coordinates · only this track’s observations are connected.</p>
    <svg viewBox={`${left - pad} ${top - pad} ${viewSize} ${viewSize}`} role="img" aria-label={`Enlarged observed path for ${track.track_id}`}>
      {visibility.tracks && <g style={{ color: colors.observed }}>
        {observed.length > 1 && <polyline className="detail-observed-path" points={points(observed)} fill="none" stroke={colors.observed} strokeWidth={unit * 2.5} />}
        {observed.map((point, index) => <g key={point.frame_index} opacity={.4 + .6 * (index + 1) / observed.length}>
          <circle cx={point.x_reference_px} cy={point.y_reference_px} r={unit * 3} fill={colors.observed} />
          <text x={point.x_reference_px + unit * 6} y={point.y_reference_px + unit * 3} fontSize={unit * 8} fill={colors.observed}>{point.frame_index + 1}</text>
        </g>)}
      </g>}
      {showForecast && <g stroke={colors.forecast} fill="none">
        <polyline className="detail-predicted-path" points={points([last, ...predicted])} strokeWidth={unit * 1.7} strokeDasharray={`${unit * 4} ${unit * 3}`} />
        {predicted.map(point => <circle key={point.frame_index} cx={point.x_reference_px} cy={point.y_reference_px} r={unit * 3.5} strokeWidth={unit * 1.5} />)}
      </g>}
    </svg>
    <p>{observed.length} observed positions through frame {frameIndex + 1}. Net displacement: {evidence.displacement ? `${Math.hypot(evidence.displacement.x_px, evidence.displacement.y_px).toFixed(3)} px over the full track` : 'insufficient observations'}.</p>
  </section>;
}
