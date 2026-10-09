import { useEffect, useId, useRef, useState } from 'react';
import type { AnalysisResult } from '../types/contracts';
import { alignmentAvailable, currentDetections, trackColors, visibleTrack, zoomAt } from '../visualization/overlay';
import type { ViewerFrame, Viewport, XY } from '../visualization/overlay';
import './tracking-workbench.css';

export interface TrackingWorkbenchProps { result: AnalysisResult; frames: ViewerFrame[] }
export function TrackingWorkbench({ result, frames }: TrackingWorkbenchProps) {
  const ordered = [...frames].sort((a, b) => a.frameIndex - b.frameIndex);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [showDetections, setShowDetections] = useState(true);
  const [showTracks, setShowTracks] = useState(true);
  const [showPredictions, setShowPredictions] = useState(true);
  const [playing, setPlaying] = useState(false);
  const [view, setView] = useState<Viewport>({ x: 0, y: 0, zoom: 1 });
  const [imageError, setImageError] = useState(false);
  const [nativePerScreenPixel, setNativePerScreenPixel] = useState(1);
  const svgRef = useRef<SVGSVGElement>(null);
  const drag = useRef<{ client: XY; view: Viewport; inverse: DOMMatrix; moved: boolean } | null>(null);
  const id = useId().replace(/:/g, '');
  const frame = ordered[Math.min(index, ordered.length - 1)];
  const finalFrame = index === ordered.length - 1;
  useEffect(() => { setIndex(0); setSelected(null); setPlaying(false); setView({ x: 0, y: 0, zoom: 1 }); }, [result.job_id, result.sequence_id]);
  useEffect(() => { setImageError(false); }, [frame?.imageUrl]);
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg || !frame) return;
    const resize = () => {
      const rect = svg.getBoundingClientRect();
      const fit = Math.min(rect.width / frame.width, rect.height / frame.height);
      if (fit > 0) setNativePerScreenPixel(1 / fit);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(svg); resize();
    return () => observer.disconnect();
  }, [frame?.width, frame?.height, frame?.imageUrl]);
  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => setIndex(i => (i + 1) % ordered.length), 750);
    return () => window.clearInterval(timer);
  }, [playing, ordered.length]);
  // A non-passive wheel listener keeps zoom from also scrolling the page.
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const wheel = (event: WheelEvent) => {
      const matrix = svg.getScreenCTM();
      if (!matrix) return;
      event.preventDefault();
      const anchor = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
      setView(v => zoomAt(v, anchor, v.zoom * Math.exp(-event.deltaY * .002)));
    };
    svg.addEventListener('wheel', wheel, { passive: false });
    return () => svg.removeEventListener('wheel', wheel);
  }, [frame?.imageUrl]);
  if (!frame) return <section className="tw-empty">No image frames supplied.</section>;
  const scale = nativePerScreenPixel / view.zoom;
  const detections = currentDetections(result, frame.frameIndex);
  const active = result.tracks.find(t => t.track_id === selected);
  const aligned = alignmentAvailable(result, frame);
  const forecastCount = result.tracks.reduce((count, track) => count + visibleTrack(track, result, frame).forecast.length, 0);
  const select = (trackId: string) => { if (!drag.current?.moved) setSelected(trackId); };
  const focusOpacity = (trackId: string) => !selected || selected === trackId ? 1 : .3;
  const labelWidth = (text: string) => Math.min(frame.width * .65, (text.length * 6.6 + 14) * scale);
  return <section className="tw" aria-label="Tracking workbench">
    <div className="tw-heading"><div><p className="tw-kicker">Sequence telemetry · {result.source_type}</p>
      <h1>{result.sequence_id}</h1><p>Saved analysis result · {result.tracks.length} tracks · Identity unverified</p></div>
      <div className="tw-status">{finalFrame ? forecastCount > 0 ? 'FINAL FRAME / FORECAST' : 'FINAL FRAME / OBSERVATIONS' : 'OBSERVATION REVIEW'}<small>{result.coordinate_frame} → native image · px</small></div></div>
    <div className="tw-layout"><div className="tw-primary">
      <div className="tw-toolbar"><div className="tw-toggles">
        <label><input type="checkbox" checked={showDetections} onChange={e => setShowDetections(e.target.checked)} />Detections</label>
        <label><input type="checkbox" checked={showTracks} onChange={e => setShowTracks(e.target.checked)} />Tracks</label>
        <label><input type="checkbox" checked={showPredictions} onChange={e => setShowPredictions(e.target.checked)} />Predictions</label></div>
        <div className="tw-zoom"><button aria-label="Zoom out" onClick={() => setView(v => zoomAt(v, { x: v.x + frame.width / v.zoom / 2, y: v.y + frame.height / v.zoom / 2 }, v.zoom / 1.5))}>−</button>
          <output>{view.zoom.toFixed(1)}×</output><button aria-label="Zoom in" onClick={() => setView(v => zoomAt(v, { x: v.x + frame.width / v.zoom / 2, y: v.y + frame.height / v.zoom / 2 }, v.zoom * 1.5))}>+</button>
          <button onClick={() => setView({ x: 0, y: 0, zoom: 1 })}>Fit</button></div></div>
      <div className="tw-image" style={{ aspectRatio: `${frame.width} / ${frame.height}` }}>
        <svg ref={svgRef} role="img" aria-label={`Frame ${frame.frameIndex + 1} tracking overlay`} width="100%" height="100%"
          viewBox={`${view.x} ${view.y} ${frame.width / view.zoom} ${frame.height / view.zoom}`} preserveAspectRatio="xMidYMid meet"
          onPointerDown={event => {
            if (event.button !== 0) return;
            const matrix = svgRef.current?.getScreenCTM();
            if (!matrix) return;
            drag.current = { client: { x: event.clientX, y: event.clientY }, view, inverse: matrix.inverse(), moved: false };
            event.currentTarget.setPointerCapture(event.pointerId);
          }} onPointerMove={event => {
            const start = drag.current;
            if (!start) return;
            const a = new DOMPoint(start.client.x, start.client.y).matrixTransform(start.inverse);
            const b = new DOMPoint(event.clientX, event.clientY).matrixTransform(start.inverse);
            if (Math.hypot(event.clientX - start.client.x, event.clientY - start.client.y) > 4) start.moved = true;
            if (start.moved) setView({ ...start.view, x: start.view.x + a.x - b.x, y: start.view.y + a.y - b.y });
          }} onPointerUp={event => {
            // Pointer capture retargets clicks, so pick using the actual element under release.
            if (drag.current && !drag.current.moved) {
              const target = document.elementFromPoint(event.clientX, event.clientY)?.closest('[data-track-id]');
              if (target) setSelected(target.getAttribute('data-track-id'));
            }
            drag.current = null; event.currentTarget.releasePointerCapture(event.pointerId);
          }} onPointerCancel={() => { drag.current = null; }}>
          <defs><clipPath id={`${id}-clip`}><rect width={frame.width} height={frame.height} /></clipPath></defs>
          <g clipPath={`url(#${id}-clip)`}>
            <image href={frame.imageUrl} width={frame.width} height={frame.height} preserveAspectRatio="xMidYMid meet" onError={() => setImageError(true)} />
            {!imageError && result.tracks.map(track => {
              const { observed, forecast } = visibleTrack(track, result, frame);
              const color = trackColors(track.track_id);
              const brighter = selected === track.track_id;
              const predicted = [observed.at(-1), ...forecast];
              return <g key={track.track_id} data-track-id={track.track_id} opacity={focusOpacity(track.track_id)} className="tw-track" onClick={() => select(track.track_id)}>
                <title>{track.track_id} · {track.status}</title>
                {showTracks && observed.map(({ point, xy }, i) => {
                  if (!xy) return null;
                  const previous = observed[i - 1]?.xy;
                  const opacity = .25 + .75 * (i + 1) / observed.length;
                  return <g key={point.frame_index} opacity={opacity} style={{ color: color.observed }}>
                    {previous && <line x1={previous.x} y1={previous.y} x2={xy.x} y2={xy.y} stroke={color.observed} strokeWidth={brighter ? 2.5 : 1.5} vectorEffect="non-scaling-stroke" />}
                    <circle data-kind="observed" cx={xy.x} cy={xy.y} r={(i === observed.length - 1 ? 3.8 : 2.5) * scale} fill={color.observed} className={i === observed.length - 1 ? 'tw-glow' : ''} />
                  </g>;
                })}
                {showPredictions && forecast.length > 0 && <g className="tw-forecast" opacity={finalFrame ? 1 : .8} style={{ color: color.forecast }}>
                  {predicted.map((item, i) => {
                    if (!item?.xy || i === 0) return null;
                    const previous = predicted[i - 1]?.xy;
                    const xy = item.xy;
                    return <g key={item.point.frame_index}>
                      {previous && <line x1={previous.x} y1={previous.y} x2={xy.x} y2={xy.y} stroke={color.forecast} strokeWidth={brighter || finalFrame ? 2 : 1.5} strokeDasharray="6 5" vectorEffect="non-scaling-stroke" />}
                      <circle data-kind="forecast" cx={xy.x} cy={xy.y} r={4.2 * scale} fill="none" stroke={color.forecast} strokeWidth="1.7" vectorEffect="non-scaling-stroke" className="tw-glow" />
                    </g>;
                  })}
                </g>}
              </g>;
            })}
            {showDetections && !imageError && detections.map(({ detection: d, track }) => {
              const [left, top, right, bottom] = d.bbox_raw_px;
              const color = track ? trackColors(track.track_id).observed : '#b2c4d3';
              const text = track?.track_id ?? 'candidate';
              const width = labelWidth(text);
              const lx = Math.max(0, Math.min(left, frame.width - width));
              const ly = Math.max(0, Math.min(top - 21 * scale, frame.height - 19 * scale));
              return <g key={d.detection_id} data-track-id={track?.track_id} opacity={track ? focusOpacity(track.track_id) : .65}
                onClick={() => track && select(track.track_id)} className={track ? 'tw-track' : ''} style={{ color }}>
                <title>{text} · {d.kind} · heuristic quality {d.quality_score.toFixed(2)}</title>
                <rect data-kind="detection" x={left} y={top} width={right - left} height={bottom - top} fill="none" stroke={color}
                  strokeWidth={selected === track?.track_id ? 3 : 1.7} vectorEffect="non-scaling-stroke" className="tw-glow" />
                <rect x={lx} y={ly} width={width} height={18 * scale} rx={3 * scale} fill="#06121e" fillOpacity=".92" stroke={color} strokeWidth=".6" vectorEffect="non-scaling-stroke" />
                <text x={lx + 6 * scale} y={ly + 12.5 * scale} fill={color} fontSize={11 * scale} fontFamily="monospace">{text.length > 30 ? `${text.slice(0, 27)}…` : text}</text>
              </g>;
            })}
          </g>
        </svg>
        <div className="tw-image-meta">{frame.width} × {frame.height} <span>Drag to pan · Scroll to zoom</span></div>
      </div>
      {imageError && <p role="alert" className="tw-warning">Image unavailable. Overlays are hidden until the frame loads.</p>}
      {!aligned && <p role="status" className="tw-warning">Alignment data needed: history and forecasts hidden for this native frame. Supply its reference_to_raw transform.</p>}
      <div className="tw-timeline"><button aria-label={playing ? 'Pause playback' : 'Play sequence'} onClick={() => setPlaying(!playing)}>{playing ? 'Pause' : 'Play'}</button>
        <button aria-label="Previous frame" disabled={index === 0} onClick={() => { setPlaying(false); setIndex(i => i - 1); }}>‹</button>
        <input aria-label="Visible frame" type="range" min="0" max={ordered.length - 1} value={index} onChange={e => { setPlaying(false); setIndex(Number(e.target.value)); }} />
        <button aria-label="Next frame" disabled={finalFrame} onClick={() => { setPlaying(false); setIndex(i => i + 1); }}>›</button>
        <output>FRAME {index + 1} / {ordered.length}</output></div>
      <div className="tw-legend"><span><i className="tw-legend-observed" />Solid / filled = observed</span><span><i className="tw-legend-forecast" />Dashed / hollow = forecast</span><span>Neon box = current detection</span></div>
      {finalFrame && <p className="tw-forecast-note">{forecastCount > 0
        ? `Forecast continuation · ${forecastCount} backend prediction points. Points outside the image are clipped.`
        : 'No backend forecast available for these tracks.'}{forecastCount > 0 && !showPredictions && ' Enable Predictions to show the continuation.'}</p>}
    </div><aside className="tw-sidebar"><div className="tw-list-heading"><h2>Track channels</h2><button disabled={!selected} onClick={() => setSelected(null)}>All</button></div>
      <div className="tw-track-list">{result.tracks.map(track => {
        const colors = trackColors(track.track_id);
        const visibleCount = track.points.filter(p => p.point_type === 'observed' && p.frame_index <= frame.frameIndex).length;
        return <button key={track.track_id} className={`tw-track-row ${selected === track.track_id ? 'is-selected' : ''}`} style={{ borderLeftColor: colors.observed }}
          aria-pressed={selected === track.track_id} onClick={() => setSelected(track.track_id)}>
          <span style={{ color: colors.observed }}>{track.track_id}</span><small>{track.status} · {visibleCount} observed so far</small>
        </button>;
      })}{result.tracks.length === 0 && <p>No tracks in this result.</p>}</div>
      <div className="tw-evidence"><h2>{active ? active.track_id : 'Select a track'}</h2>
        {active ? <><dl><dt>Actual observations</dt><dd>{active.observed_count}</dd><dt>Candidate quality</dt><dd title="Heuristic support score, not debris probability">{active.quality_score.toFixed(2)}</dd>
          <dt>Image-plane speed</dt><dd>{active.trajectory ? `${active.trajectory.speed.toFixed(2)} ${active.trajectory.speed_unit}` : 'Not fitted'}</dd>
          <dt>Fit RMSE</dt><dd>{active.trajectory?.fit_rmse_px == null ? 'Unknown' : `${active.trajectory.fit_rmse_px.toFixed(2)} px`}</dd></dl>
          <div className="tw-channel-legend"><span style={{ color: trackColors(active.track_id).observed }}>● Observed</span><span style={{ color: trackColors(active.track_id).forecast }}>◌ Forecast</span></div>
          {active.warnings.map((w, i) => <p className="tw-warning" key={i}>{w}</p>)}</> : <p>Click a neon box, path or track channel to isolate its observations and forecast.</p>}
        <p className="tw-disclaimer">Orbital-object candidates; identity unverified. Forecasts are image-plane estimates.</p>
      </div>
    </aside></div>
    {[...result.registration.warnings, ...result.warnings].length > 0 && <details className="tw-warnings"><summary>Result warnings ({result.registration.warnings.length + result.warnings.length})</summary>
      {[...result.registration.warnings, ...result.warnings].map((w, i) => <p key={i}>{w}</p>)}</details>}
  </section>;
}
