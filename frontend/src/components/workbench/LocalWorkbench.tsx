import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { useAnalysisJob } from '../../hooks/useAnalysisJob';
import { presentAnalysis } from '../../state/analysis';
import { getJobDiagnostics } from '../../api/client';
import { buildUploadManifest, uploadOverlay } from '../../viewer/uploadOverlay';
import { ScientificOverlay } from './ScientificOverlay';
import { AnalysisResults } from './AnalysisPanel';
import type { SequenceInput } from '../../types/contracts';
import { Icon } from '../ui/Icon';
import { OpticalViewer } from './OpticalViewer';
import { useLocalSequence } from '../../hooks/useLocalSequence';
import { useFramePlayback } from '../../hooks/useFramePlayback';
import { trackColors } from '../../viewer/trackColors';
import { apiUrl } from '../../api/baseUrl';
import { TrackQualityPanel } from './TrackQualityPanel';
import { buildTrackReport, downloadTrackReport } from '../../viewer/trackReport';
import { downloadPdfReport } from '../../viewer/pdfReport';
import { TrackPathDetail } from './TrackPathDetail';

export function LocalWorkbench() {
  const sequence = useLocalSequence(), playback = useFramePlayback(sequence.frames);
  const analysis = useAnalysisJob();
  const [manifest, setManifest] = useState<SequenceInput | null>(null);
  const [diagnostics, setDiagnostics] = useState<unknown>(null), [uploadError, setUploadError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [visibility, setVisibility] = useState({ detections: true, tracks: true, predictions: true });
  const result = analysis.state.phase === 'succeeded' ? analysis.state.result : null;
  const busy = ['submitting', 'queued', 'processing', 'awaiting_result'].includes(analysis.state.phase);
  const presentation = presentAnalysis(analysis.state);
  useEffect(() => { analysis.reset(); setManifest(null); setDiagnostics(null); setUploadError(null); setSelected(null); }, [sequence.frames, analysis.reset]);
  useEffect(() => {
    if (!result) return;
    const request = new AbortController();
    getJobDiagnostics(result.job_id, request.signal).then(setDiagnostics).catch(error => { if (!request.signal.aborted) setUploadError(String(error)); });
    // Prefer an actual multi-frame path over an unrelated single-frame candidate.
    setSelected([...result.tracks].sort((a, b) => b.observed_count - a.observed_count)[0]?.track_id ?? null);
    return () => request.abort();
  }, [result]);
  const submit = () => {
    try { const next = buildUploadManifest(sequence.frames); setManifest(next); setDiagnostics(null); setUploadError(null); analysis.upload(next, sequence.frames.map(frame => frame.file)); }
    catch (error) { setUploadError(error instanceof Error ? error.message : 'Invalid upload'); }
  };
  const input = useRef<HTMLInputElement>(null), id = useId();
  const current = sequence.frames[playback.index];
  const model = useMemo(() => result && current && manifest ? uploadOverlay(result, current, playback.index, manifest, diagnostics) : { detections: [], tracks: [], warnings: [] }, [result, current, manifest, diagnostics, playback.index]);
  const track = result?.tracks.find(track => track.track_id === selected);
  const ready = !!current && !sequence.loading && !sequence.draft.length;
  const choose = () => { playback.pause(); input.current?.click(); };
  const download = (format: 'pdf' | 'json') => {
    if (!result || !manifest) return;
    try {
      const report = buildTrackReport(result, manifest, sequence.frames, selected);
      if (format === 'pdf') downloadPdfReport(report); else downloadTrackReport(report);
    }
    catch (error) { setUploadError(error instanceof Error ? error.message : 'Report download failed'); }
  };
  return <section id="observations" className="workbench-shell local-workbench" aria-label="Mission image workbench" data-source={result ? 'uploaded_images' : 'local_preview'} data-job-id={result?.job_id} data-analysis-phase={analysis.state.phase}>
    <header className="observation-toolbar" aria-label="Image selection and sequence controls">
      <div className="observation-toolbar-heading"><Icon name="image" /><div><h2>Optical observations</h2><p>Local Image Preview · Analyze uploads your confirmed sequence.</p></div></div>
      <div className="source-actions" role="group" aria-label="Image selection">
        <button className="button button--primary button--small" type="button" onClick={choose}><Icon name="plus" />{current ? 'Replace images' : 'Choose images'}</button>
        <button className="button button--secondary button--small" type="button" aria-label="Analyze local images" title="Analyze five confirmed images" disabled={!ready || busy || sequence.frames.length !== 5} onClick={submit}><Icon name="scan" /><span className="local-analysis-control-label">Analyze local images</span></button>
        {!!(current || sequence.draft.length || sequence.loading) && <button className="button button--quiet button--small" type="button" aria-label="Clear sequence" title="Clear sequence" onClick={() => { playback.pause(); sequence.clear(); }}>Clear</button>}
      </div>
    </header>
    <input ref={input} hidden type="file" multiple accept="image/jpeg,image/png,.jpg,.jpeg,.png" aria-label="Select telescope images" tabIndex={-1}
      onChange={event => { const files = Array.from(event.currentTarget.files ?? []); event.currentTarget.value = ''; if (files.length) { playback.pause(); void sequence.select(files); } }} />
    <div className="local-sequence-notice"><Icon name="shield" /><span>Confirm exactly five grayscale telescope frames, then Analyze to upload them to the analysis service. Timestamps are unknown.</span></div>
    {analysis.state.phase !== 'idle' && <div className="sequence-feedback" role={analysis.state.phase === 'failed' ? 'alert' : 'status'}>
      <strong>{presentation.label}</strong> · {presentation.description}
      {analysis.state.phase === 'failed' && <span> Error: {analysis.state.error.code}.</span>}
      {busy && <><progress aria-label="Analysis progress" value={presentation.progress ?? 0} max={1} /><button type="button" onClick={analysis.cancel}>Stop monitoring</button></>}
    </div>}
    {uploadError && <div className="sequence-feedback sequence-feedback--error" role="alert">{uploadError}</div>}
    {result && <div className="demo-overlay-controls" aria-label="Upload overlay visibility">{(['detections','tracks','predictions'] as const).map(key => <label key={key}><input type="checkbox" checked={visibility[key]} onChange={event => setVisibility(v => ({...v, [key]:event.target.checked}))} />{key}</label>)}</div>}
    {sequence.loading && <div className="sequence-feedback" role="status">Validating file contents, dimensions and browser decoding…</div>}
    {sequence.error && <div className="sequence-feedback sequence-feedback--error" role="alert"><Icon name="info" /><span>{sequence.error}{current ? ' Your confirmed sequence is preserved.' : ''}</span></div>}
    {!!sequence.draft.length && <section className="frame-order-editor" aria-labelledby={`${id}-order`}>
      <div className="order-editor-heading"><div><p className="eyebrow">REVIEW BEFORE PLAYBACK</p><h3 id={`${id}-order`}>Confirm the frame order.</h3><p>{sequence.draft.length} frames selected. Move frames into the order you intend; filenames do not establish acquisition order.</p></div>
        <div className="order-editor-actions"><button type="button" className="button button--quiet button--small" disabled={sequence.loading} onClick={sequence.cancelDraft}>Cancel</button>
          <button type="button" className="button button--primary button--small" disabled={sequence.loading} onClick={() => { playback.pause(); sequence.confirm(); }}>Confirm order & view</button></div></div>
      <ol className="draft-frame-list" aria-label="Proposed frame order">{sequence.draft.map((frame, index) => <li key={frame.id}>
        <span className="frame-order-number">{String(index + 1).padStart(2, '0')}</span><img src={frame.url} alt="" width="48" height="36" />
        <span className="draft-frame-name" title={frame.file.name}>{frame.file.name}<small>{frame.width_px} × {frame.height_px} px</small></span>
        <div className="frame-order-buttons"><button type="button" disabled={index === 0 || sequence.loading} aria-label={`Move frame ${index + 1} earlier`} onClick={() => sequence.reorder(index, -1)}><Icon name="up" /></button>
          <button type="button" disabled={index === sequence.draft.length - 1 || sequence.loading} aria-label={`Move frame ${index + 1} later`} onClick={() => sequence.reorder(index, 1)}><Icon name="down" /></button></div>
      </li>)}</ol>
      {current && <p className="order-preservation-note">Your confirmed sequence stays available until you confirm this replacement.</p>}
    </section>}
    <div className="workspace-body"><div className="observation-area">
      <OpticalViewer key={sequence.frames[0]?.id ?? 'empty'} frame={current} onSelect={choose} onStep={direction => playback.seek(playback.index + direction)}
        onToggle={() => { if (ready) playback.toggle(); }} onError={playback.pause}
        overlay={scale => <ScientificOverlay model={model} scale={scale} selected={selected} select={setSelected} visibility={visibility} currentFrame={playback.index}
          nativeSize={current ? { width: current.width_px, height: current.height_px } : undefined} />} />
      {!!model.warnings.length && <p className="analysis-note" role="status">{model.warnings.join(' ')}</p>}
      {result && !model.warnings.length && !model.detections.length && <p className="analysis-note">No candidates in this frame.</p>}
      {result && <p className="t08-forecast-status" data-final-frame={playback.index === sequence.frames.length - 1}>
        {playback.index === sequence.frames.length - 1 ? 'Final frame · ' : ''}
        {model.tracks.some(t => t.predictions.length) ? `Forecast continuation · ${model.tracks.reduce((n, t) => n + t.predictions.length, 0)} backend predictions. Dashed lines and hollow dots are not observations.`
          : result.tracks.some(t => t.trajectory?.predictions.length) ? 'Forecasts appear once the timeline reaches each track’s last observation.' : 'No backend forecasts available for these tracks.'}
        {!visibility.predictions && ' Predictions are hidden.'}</p>}
      <div className="frame-caption"><span>{current ? `FRAME ${String(playback.index + 1).padStart(2, '0')}` : 'NO FRAME SELECTED'}</span><strong title={current?.file.name}>{current?.file.name ?? 'Choose and confirm your observations'}</strong></div>
      <div className="frame-timeline local-frame-timeline"><div className="timeline-controls">
        <button type="button" disabled={!ready || playback.index === 0} aria-label="Previous frame" onClick={() => playback.seek(playback.index - 1)}><Icon name="back" /></button>
        <button type="button" disabled={!ready} className="timeline-play" aria-label={playback.playing ? 'Pause frames' : 'Play frames'} onClick={playback.toggle}><Icon name={playback.playing ? 'pause' : 'play'} /></button>
        <button type="button" disabled={!ready || playback.index === sequence.frames.length - 1} aria-label="Next frame" onClick={() => playback.seek(playback.index + 1)}><Icon name="next" /></button>
        <button type="button" disabled={!ready} aria-label="Restart from first frame" onClick={playback.restart}><Icon name="restart" /></button>
        <output aria-label="Current frame">Frame {current ? playback.index + 1 : '—'} / {sequence.frames.length || '—'}</output>
      </div>
      <label className="playback-speed">Display rate<select aria-label="Playback display rate" value={playback.rate} disabled={!ready} onChange={event => playback.setRate(Number(event.target.value))}>
        {[.5, 1, 2, 4].map(rate => <option key={rate} value={rate}>{rate} frames/s</option>)}</select></label>
      <div className="frame-slider"><input type="range" aria-label="Frame timeline" min="1" max={Math.max(1, sequence.frames.length)} value={current ? playback.index + 1 : 1} disabled={!ready}
        aria-valuetext={current ? `Frame ${playback.index + 1} of ${sequence.frames.length}: ${current.file.name}` : 'No confirmed sequence'} onChange={event => playback.seek(Number(event.target.value) - 1)} />
        <div><span>01</span><span>{sequence.frames.length ? String(sequence.frames.length).padStart(2, '0') : '—'}</span></div></div>
      <p>Display rate only · acquisition timing unknown</p></div>
    </div><aside className="track-inspector local-sequence-inspector" aria-label="Sequence inspector">
      <div className="inspector-title"><Icon name="layers" /><h3>Sequence inspector</h3></div>
      <span className="inspector-section-label">Source & status</span>
      <dl className="evidence-values"><div><dt>Source</dt><dd>{result ? 'Uploaded images' : 'Local images'}</dd></div><div><dt>Status</dt><dd>{sequence.loading ? 'Validating' : sequence.draft.length ? 'Review order' : result ? 'Live analysis result' : current ? 'Ready to inspect' : 'Awaiting images'}</dd></div><div><dt>Frames</dt><dd>{sequence.frames.length || 'Not loaded'}</dd></div><div><dt>Dimensions</dt><dd>{current ? `${current.width_px} × ${current.height_px} px` : 'Not available'}</dd></div><div><dt>Timestamps</dt><dd>Unknown</dd></div><div><dt>Analysis</dt><dd>{analysis.state.phase === 'idle' ? 'Not performed' : analysis.state.phase}</dd></div></dl>
      <span className="inspector-section-label inspector-frames-label">Frames</span>
      {!current && <p className="inspector-empty-text">Your confirmed frame order will appear here.</p>}
      {current && <ol className="confirmed-frame-list" aria-label="Confirmed frame order">{sequence.frames.map((frame, index) => <li key={frame.id}><button type="button" disabled={sequence.loading || !!sequence.draft.length}
        aria-current={index === playback.index ? 'true' : undefined} aria-label={`Inspect frame ${index + 1}: ${frame.file.name}`} onClick={() => playback.seek(index)}>
        <span>{String(index + 1).padStart(2, '0')}</span><img src={frame.url} alt="" width="44" height="33" /><span title={frame.file.name}>{frame.file.name}</span></button></li>)}</ol>}
      {result && <><label className="demo-track-selector">Selected track<select aria-label="Select upload track" value={selected ?? ''} onChange={event => setSelected(event.target.value)}>
        {!result.tracks.length && <option value="">No tracks</option>}{result.tracks.map(track => <option key={track.track_id} value={track.track_id}>{track.track_id} · {track.observed_count} observations</option>)}</select></label>
        {track && <><div className="t08-track-colors"><span style={{ color: trackColors(track.track_id).observed }}>● Observed</span><span style={{ color: trackColors(track.track_id).forecast }}>◌ Forecast</span></div>
          {track.observed_count < 2 && <p className="analysis-note">This track has one observation, so there is no observed path to connect. Select a track with two or more observations.</p>}
          <TrackQualityPanel track={track} coordinateFrame={result.coordinate_frame} />
          <TrackPathDetail track={track} frameIndex={playback.index} coordinateFrame={result.coordinate_frame} visibility={visibility} />
          <dl className="evidence-values"><div><dt>Status</dt><dd>{track.status}</dd></div><div><dt>Image-plane speed</dt><dd>{track.trajectory ? track.trajectory.speed.toFixed(3) + ' ' + track.trajectory.speed_unit : 'No fit'}</dd></div>
            <div><dt>Fit RMSE</dt><dd>{track.trajectory?.fit_rmse_px == null ? 'Not provided' : `${track.trajectory.fit_rmse_px.toFixed(3)} px`}</dd></div></dl>
          {track.warnings.map((warning, i) => <p className="analysis-note" key={i}>{warning}</p>)}</>}</>}
      {!result && <div className="local-evidence-pending"><span className="inspector-section-label">Local analysis</span><strong>{analysis.state.phase === 'idle' ? 'Not performed' : presentation.label}</strong><p>Detections, track IDs and predictions will appear only with matching backend results.</p></div>}
      <div className="identity-note"><Icon name="info" /><span>Candidate identity remains unverified.</span></div></aside></div>
    <footer className="workspace-footer"><span><Icon name="info" />Observed tracks use solid lines; predictions use dashed lines. Candidate identity is unverified.</span>
      <div className="export-actions">{result ? <><button type="button" className="button button--primary button--small" onClick={() => download('pdf')}><Icon name="download" />Download Report (PDF)</button><button type="button" className="button button--quiet button--small" onClick={() => download('json')}>Report JSON</button><a className="button button--quiet button--small" target="_blank" rel="noopener noreferrer" href={apiUrl(`/api/jobs/${result.job_id}/exports/csv`)}>Backend CSV</a></> : <span>Exports available after analysis</span>}</div></footer>
    {result && <AnalysisResults result={result} showViewer={false} />}
  </section>;
}
