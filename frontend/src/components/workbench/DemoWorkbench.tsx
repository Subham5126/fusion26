import { useEffect, useId, useMemo, useState } from 'react';
import type { AnalysisResult } from '../../types/contracts';
import { useDemoFrames } from '../../hooks/useDemoFrames';
import { useFramePlayback } from '../../hooks/useFramePlayback';
import { supportsDemoFrames } from '../../viewer/demoFrames';
import { scientificOverlay } from '../../viewer/scientificOverlay';
import { Icon } from '../ui/Icon';
import { OpticalViewer } from './OpticalViewer';
import { ScientificOverlay } from './ScientificOverlay';
import { trackColors } from '../../viewer/trackColors';

export function DemoWorkbench({ result }: { result: AnalysisResult }) {
  if (!supportsDemoFrames(result)) return <p className="analysis-note">Frame metadata for this source has not been verified. No images or overlays are substituted.</p>;
  return <VerifiedDemoWorkbench key={result.job_id} result={result} />;
}

function VerifiedDemoWorkbench({ result }: { result: AnalysisResult }) {
  const backend = useDemoFrames(result.job_id), id = useId();
  const [displayedUrl, setDisplayedUrl] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(result.tracks[0]?.track_id ?? null);
  const [visibility, setVisibility] = useState({ detections: true, tracks: true, predictions: true });
  const readyId = backend.state.phase === 'ready' && backend.state.frame?.url === displayedUrl ? backend.state.frame.id : null;
  const playback = useFramePlayback(backend.frames, readyId);
  const listed = backend.frames[playback.index];
  useEffect(() => { if (listed) backend.select(listed.frame_index); }, [backend.select, listed]);
  useEffect(() => { if (backend.state.phase === 'failed') playback.pause(); }, [backend.state.phase]);
  const current = backend.state.jobId === result.job_id && backend.state.index === listed?.frame_index ? backend.state : undefined;
  const frame = current?.phase === 'ready' ? current.frame : undefined;
  const model = useMemo(() => frame ? scientificOverlay(result, frame) : { detections: [], tracks: [], warnings: [] }, [result, frame]);
  const ready = !!frame && frame.url === displayedUrl;
  const track = result.tracks.find(entry => entry.track_id === selected);
  const number = (value: number) => value.toLocaleString(undefined, { maximumFractionDigits: 3 });
  if (!backend.manifest || !listed) return <section className="demo-workbench" aria-labelledby={`${id}-heading`} data-source="analyzed_demo" data-job-id={result.job_id}>
    <div className="demo-source-heading"><div><p className="eyebrow">Synthetic source · backend results</p><h3 id={`${id}-heading`}>Analyzed sequence</h3></div></div>
    <p className="analysis-note demo-provenance-note">PNGs and overlays from this job. Local Image Preview has independent images and no synthetic overlays.</p>
    <div className="sequence-feedback" role={backend.metadata.phase === 'failed' ? 'alert' : 'status'}>
      <strong>{backend.metadata.phase === 'failed' ? 'Backend frame manifest unavailable' : 'Loading backend frame manifest…'}</strong>
      <p>{backend.metadata.error ?? 'Waiting for authoritative frame order, dimensions and acquisition timestamps.'}</p>
      {backend.metadata.errorStatus && <p>{backend.metadata.errorCode} · HTTP {backend.metadata.errorStatus}</p>}
      {backend.metadata.errorStatus === 404 && <p>This job may have expired or the server restarted. Run Synthetic Demo again for a fresh job.</p>}
      {backend.metadata.phase === 'failed' && <button type="button" className="button button--secondary button--small" onClick={backend.retryManifest}>Retry backend manifest</button>}
    </div>
  </section>;
  return <section className="demo-workbench" aria-labelledby={`${id}-heading`} data-source="analyzed_demo" data-job-id={result.job_id}>
    <div className="demo-source-heading"><div><p className="eyebrow">Synthetic source · backend results</p><h3 id={`${id}-heading`}>Analyzed sequence</h3></div>
      <span className="workbench-stage"><span className="status-dot" />{backend.manifest.frame_count} frames</span></div>
    <p className="analysis-note demo-provenance-note">PNGs and overlays from this job. Local Image Preview has independent images and no synthetic overlays.</p>
    <div className="demo-overlay-controls" aria-label="Overlay visibility">{(['detections', 'tracks', 'predictions'] as const).map(key => <label key={key}>
      <input type="checkbox" checked={visibility[key]} onChange={event => setVisibility(current => ({ ...current, [key]: event.target.checked }))} />
      {key === 'tracks' ? 'Observed tracks' : key === 'predictions' ? 'Predictions' : 'Detection boxes & centroids'}</label>)}</div>
    <div className="workspace-body"><div className="observation-area">
      <OpticalViewer frame={frame} nativeSize={{ width: listed.width_px, height: listed.height_px }} onSelect={() => {}} onStep={direction => playback.seek(playback.index + direction)}
        onToggle={() => { if (ready || playback.playing) playback.toggle(); }} onError={playback.pause} onReady={setDisplayedUrl}
        overlay={scale => <ScientificOverlay model={model} scale={scale} selected={selected} select={setSelected} visibility={visibility}
          nativeSize={{ width: listed.width_px, height: listed.height_px }} />}
        emptyState={<div className="viewer-empty" role={current?.phase === 'failed' ? 'alert' : 'status'}><Icon name="image" />
          <h3>{current?.phase === 'failed' ? 'Backend frame unavailable' : 'Loading backend PNG…'}</h3>
          <p>{current?.phase === 'failed' ? current.error : `Frame ${playback.index + 1} of ${backend.frames.length} · index ${listed.frame_index}`}</p>
          {current?.errorCode && <p>{current.errorCode} · HTTP {current.errorStatus}</p>}
          {current?.errorStatus === 404 && <p>Frames may have expired or the server restarted. Run Synthetic Demo again for a fresh job.</p>}
          {current?.phase === 'failed' && <button type="button" className="button button--secondary button--small" onClick={() => backend.select(listed.frame_index, true)}>Retry backend frame</button>}</div>} />
      <div className="frame-caption"><span>FRAME {String(playback.index + 1).padStart(2, '0')} / {backend.frames.length}</span><strong>Backend index {listed.frame_index} · {listed.width_px} × {listed.height_px} px · {ready ? 'PNG ready' : current?.phase === 'failed' ? 'Unavailable' : 'Loading'}</strong></div>
      <p className="analysis-note demo-acquisition-note">Acquisition time: {listed.timestamp_s === null ? 'Not provided' : `${String(listed.timestamp_s)} s`}</p>
      <div className="frame-timeline local-frame-timeline"><div className="timeline-controls">
        <button type="button" disabled={playback.index === 0} aria-label="Previous demo frame" title="Previous demo frame" onClick={() => playback.seek(playback.index - 1)}><Icon name="back" /></button>
        <button type="button" disabled={!ready && !playback.playing} className="timeline-play" aria-label={playback.playing ? 'Pause demo frames' : 'Play demo frames'} onClick={playback.toggle}><Icon name={playback.playing ? 'pause' : 'play'} /></button>
        <button type="button" disabled={playback.index === backend.frames.length - 1} aria-label="Next demo frame" title="Next demo frame" onClick={() => playback.seek(playback.index + 1)}><Icon name="next" /></button>
        <button type="button" aria-label="Restart demo from first frame" title="Restart demo from first frame" onClick={playback.restart}><Icon name="restart" /></button>
        <output aria-label="Current demo frame">Frame {playback.index + 1} / {backend.frames.length}</output>
      </div><label className="playback-speed">Display rate<select aria-label="Demo playback display rate" value={playback.rate} onChange={event => playback.setRate(Number(event.target.value))}>
        {[.5, 1, 2, 4].map(rate => <option key={rate} value={rate}>{rate} frames/s</option>)}</select></label>
      <div className="frame-slider"><input type="range" aria-label="Demo frame timeline" min="1" max={backend.frames.length} value={playback.index + 1}
        aria-valuetext={`Frame ${playback.index + 1} of ${backend.frames.length}, backend index ${listed.frame_index}`} onChange={event => playback.seek(Number(event.target.value) - 1)} />
        <div><span>01</span><span>{String(backend.frames.length).padStart(2, '0')}</span></div></div></div>
      <div className="demo-overlay-legend" aria-label="Overlay legend"><span><i className="legend-detection" />Neon current detection</span><span><i className="legend-observed" />Observed · solid track color + filled points</span><span><i className="legend-predicted" />Forecast · contrasting dashed line + hollow points</span></div>
      <p className="t08-forecast-status" data-final-frame={playback.index === backend.frames.length - 1}>
        {playback.index === backend.frames.length - 1 ? 'Final frame · ' : ''}
        {model.tracks.some(t => t.predictions.length) ? `Forecast continuation · ${model.tracks.reduce((n,t) => n+t.predictions.length,0)} backend predictions. Dashed lines and hollow dots are not observations.`
          : result.tracks.some(t => t.trajectory?.predictions.length) ? 'Forecasts appear once the timeline reaches each track’s last observation.' : 'No backend forecasts available for these tracks.'}
        {!visibility.predictions && ' Predictions are hidden.'}</p>
      {!!model.warnings.length && <div className="sequence-feedback sequence-feedback--error" role="alert">{model.warnings.join(' ')}</div>}
      {!model.warnings.length && ready && !model.detections.length && <p className="analysis-note">No detections in this frame. No points were added.</p>}
      <p className="analysis-note demo-forecast-note">Forecasts appear at the final observed frame. Future points have no source images and are not observations.</p>
    </div><aside className="track-inspector demo-track-inspector" aria-label="Analyzed demo track inspector">
      <div className="inspector-title"><Icon name="track" /><h3>Track evidence</h3></div>
      <button type="button" className="button button--primary button--small demo-final-forecast" onClick={() => playback.seek(backend.frames.length - 1)}><span>Inspect final frame & forecasts</span><Icon name="arrow" /></button>
      <label className="demo-track-selector">Selected track<select aria-label="Select analyzed track" value={selected ?? ''} disabled={!result.tracks.length} onChange={event => setSelected(event.target.value)}>
        {!result.tracks.length && <option value="">No tracks returned</option>}{result.tracks.map(track => <option key={track.track_id} value={track.track_id}>{track.track_id}</option>)}</select></label>
      {track ? <><p className="analysis-note">{track.candidate_label}</p>
        <div className="t08-track-colors"><span style={{ color: trackColors(track.track_id).observed }}>● Observed</span><span style={{ color: trackColors(track.track_id).forecast }}>◌ Forecast</span></div>
        <dl className="evidence-values">
        <div><dt>Status</dt><dd>{track.status}</dd></div><div><dt>Actual observations</dt><dd>{track.observed_count}</dd></div>
        <div><dt>Heuristic quality</dt><dd>{number(track.quality_score)}</dd></div>
        <div><dt>Image-plane speed</dt><dd>{track.trajectory ? `${number(track.trajectory.speed)} ${track.trajectory.speed_unit}` : 'No fit'}</dd></div>
        <div><dt>Fit RMSE</dt><dd>{track.trajectory?.fit_rmse_px == null ? 'Not provided' : `${number(track.trajectory.fit_rmse_px)} px`}</dd></div>
      </dl>{!!track.warnings.length && <ul className="analysis-note">{track.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>}</> : <p className="analysis-note">No tracks were returned.</p>}

      <div className="identity-note"><Icon name="info" /><span>Image-plane candidate evidence. Identity and physical orbit remain unverified.</span></div>
    </aside></div>
    <p className="demo-metadata-note">Frame order, dimensions and acquisition times come from this job’s backend manifest. Playback rate is a display control. Local observations have independent upload jobs.</p>
  </section>;
}
