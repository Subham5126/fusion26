import type { ScientificOverlayModel } from '../../viewer/scientificOverlay';
import type { Point } from '../../viewer/geometry';

const path = (points: Point[]) => points.map(point => `${point.x},${point.y}`).join(' ');
export function ScientificOverlay({ model, scale, selected, select, visibility }: {
  model: ScientificOverlayModel; scale: number; selected: string | null; select: (id: string) => void;
  visibility: { detections: boolean; tracks: boolean; predictions: boolean };
}) {
  const px = (value: number) => value / Math.max(scale, .001);
  return <>
    {visibility.detections && model.detections.map(detection => <g key={detection.id} className="scientific-detection" data-detection-id={detection.id}>
      <rect {...detection.box} fill="none" strokeWidth={px(1.5)} />
      <path d={`M ${detection.center.x - px(4)} ${detection.center.y} h ${px(8)} M ${detection.center.x} ${detection.center.y - px(4)} v ${px(8)}`}
        strokeWidth={px(1)} />
    </g>)}
    {model.tracks.map(track => <g key={track.id} data-track-id={track.id} className={`scientific-track ${selected === track.id ? 'is-selected' : ''}`}>
      {visibility.tracks && <>
        {track.segments.map((segment, index) => <polyline key={index} points={path(segment)} fill="none" strokeWidth={px(selected === track.id ? 2.5 : 1.5)} />)}
        {track.observed.map(point => <g key={point.frame}>
          <circle className="observed-point" cx={point.x} cy={point.y} r={px(3)} stroke="none" data-observed-frame={point.frame} />
          <circle className="track-hit-target" data-track-control="true" cx={point.x} cy={point.y} r={px(12)} fill="transparent" stroke="none" style={{ strokeWidth: px(1) }}
            role="button" tabIndex={0} aria-label={`Select track ${track.id}, observed frame ${point.frame}`} aria-pressed={selected === track.id}
            onClick={() => select(track.id)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); event.stopPropagation(); select(track.id); } }} />
        </g>)}
        {!!track.observed.length && <text x={track.observed.at(-1)!.x + px(10)} y={track.observed.at(-1)!.y - px(10)} fontSize={px(11)} className="track-overlay-label">{track.id}</text>}
      </>}
      {visibility.predictions && !!track.predictions.length && <g className="scientific-forecast">
        <polyline points={path(track.forecast)} fill="none" strokeDasharray={`${px(5)} ${px(4)}`} strokeWidth={px(1.5)} />
        {track.predictions.map(point => <circle key={point.frame} className="predicted-point" data-predicted-frame={point.frame}
          cx={point.x} cy={point.y} r={px(4)} fill="none" strokeWidth={px(1.5)}
          aria-label={`Predicted frame ${point.frame} · not observed`} />)}
      </g>}
    </g>)}
  </>;
}
