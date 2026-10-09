import type { KeyboardEvent } from 'react';
import type { ScientificOverlayModel } from '../../viewer/scientificOverlay';
import type { Size } from '../../viewer/geometry';
import { trackColors } from '../../viewer/trackColors';
import './t08-overlay.css';

export interface T08OverlayProps {
  model: ScientificOverlayModel;
  scale: number;
  selected: string | null;
  select: (id: string) => void;
  visibility: { detections: boolean; tracks: boolean; predictions: boolean };
  nativeSize?: Size;
  currentFrame?: number;
}
// Positions are already projected by the verified source-specific mappers.
// Keep OpticalViewer's integer pixel centers and exclusive raster edges intact.
export function T08Overlay({ model, scale, selected, select, visibility, nativeSize, currentFrame }: T08OverlayProps) {
  const px = (value: number) => value / Math.max(scale, .001);
  const glow = (color: string) => ({ filter: `drop-shadow(0 0 ${px(2.5)}px ${color})` });
  const opacity = (id?: string) => !selected || selected === id ? 1 : .3;
  const controls = (id: string, label: string) => ({
    'data-track-control': true,
    role: 'button', tabIndex: 0, 'aria-label': label, 'aria-pressed': selected === id,
    onClick: () => select(id),
    onKeyDown: (event: KeyboardEvent<SVGElement>) => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); event.stopPropagation(); select(id); }
    },
  });
  return <g className="t08-overlay" data-renderer="t08-live">
    {model.tracks.map(track => {
      const color = trackColors(track.id), highlighted = selected === track.id;
      return <g key={track.id} data-track-id={track.id} className={`scientific-track t08-track ${highlighted ? 'is-selected' : ''}`}
        style={{ color: color.observed, stroke: color.observed, fill: color.observed, opacity: opacity(track.id) }}>
        {visibility.tracks && track.observed.map((point, index) => {
          const previous = track.observed[index - 1];
          const recent = index === track.observed.length - 1;
          const current = point.frame === currentFrame;
          const ageOpacity = .25 + .75 * (index + 1) / track.observed.length;
          return <g key={point.frame} opacity={ageOpacity}>
            {previous && <line className="t08-observed-segment" data-from-frame={previous.frame} data-to-frame={point.frame}
              x1={previous.x} y1={previous.y} x2={point.x} y2={point.y} strokeWidth={px(highlighted ? 3.2 : 1.6)} style={highlighted ? glow(color.observed) : undefined} />}
            <circle className={`observed-point ${recent ? 't08-glow' : ''}`} cx={point.x} cy={point.y} r={px(highlighted ? recent ? 5.5 : 3.5 : recent ? 3.7 : 2.5)}
              stroke="none" data-observed-frame={point.frame} style={recent ? glow(color.observed) : undefined} />
            {highlighted && current && <circle className="t08-current-observation" data-current-observed-frame={point.frame}
              cx={point.x} cy={point.y} r={px(9)} fill="none" strokeWidth={px(1.5)} style={glow(color.observed)} />}
            {highlighted && current && <text className="t08-frame-label" x={point.x + px(10)} y={point.y + px(17)}
              fontSize={px(10)} stroke="#071520" strokeWidth={px(3)} paintOrder="stroke">F{point.frame + 1}</text>}
            <circle className="track-hit-target" cx={point.x} cy={point.y} r={px(11)} fill="transparent" stroke="none"
              {...controls(track.id, `Select track ${track.id}, observed frame ${point.frame}`)} />
          </g>;
        })}
        {visibility.predictions && track.predictions.length > 0 && <g className="scientific-forecast t08-forecast t08-glow"
          style={{ color: color.forecast, stroke: color.forecast, ...glow(color.forecast) }}>
          <polyline points={track.forecast.map(point => `${point.x},${point.y}`).join(' ')} fill="none"
            strokeDasharray={`${px(5)} ${px(4)}`} strokeWidth={px(highlighted ? 2.2 : 1.7)} />
          {track.predictions.map(point => <circle key={point.frame} className="predicted-point" data-predicted-frame={point.frame}
            cx={point.x} cy={point.y} r={px(4.2)} fill="none" strokeWidth={px(1.7)} aria-label={`Predicted frame ${point.frame} · not observed`} />)}
        </g>}
      </g>;
    })}
    {visibility.detections && model.detections.map(detection => {
      const id = detection.trackId, color = id ? trackColors(id).observed : '#a3bbc9';
      const fullLabel = id ?? 'candidate';
      const label = fullLabel.length > 28 ? `${fullLabel.slice(0, 25)}…` : fullLabel;
      const width = px(label.length * 6.6 + 12);
      const x = nativeSize ? Math.max(-.5, Math.min(detection.box.x, nativeSize.width - .5 - width)) : detection.box.x;
      const y = Math.max(-.5, detection.box.y - px(22));
      return <g key={detection.id} className={`scientific-detection t08-detection ${id === selected ? 'is-selected' : ''}`}
        data-detection-id={detection.id} data-current-track-id={id} style={{ color, stroke: color, opacity: id ? opacity(id) : .65 }}>
        <title>{`${fullLabel} · ${detection.id} · current detection`}</title>
        <rect {...detection.box} className="t08-neon-box t08-glow" fill="none" strokeWidth={px(id === selected ? 2.7 : 1.7)} style={glow(color)} />
        {id && <rect {...detection.box} fill="transparent" stroke="none" {...controls(id, `Select track ${id}, current detection ${detection.id}`)} />}
        <g className="t08-box-label" {...(id ? controls(id, `Select track ${id} label`) : {})}>
          <rect x={x} y={y} width={width} height={px(18)} rx={px(3)} fill="#071520" strokeWidth={px(.65)} />
          <text x={x + px(6)} y={y + px(12.5)} fill={color} stroke="none" fontSize={px(11)}>{label}</text>
        </g>
      </g>;
    })}
  </g>;
}
