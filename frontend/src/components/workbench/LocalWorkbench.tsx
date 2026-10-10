import { useEffect, useId, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useAnalysisJob } from '../../hooks/useAnalysisJob';
import { presentAnalysis } from '../../state/analysis';
import { getJobDiagnostics } from '../../api/client';
import { buildUploadManifest, uploadOverlay } from '../../viewer/uploadOverlay';
import type { HistoryCoordinates } from '../../viewer/uploadOverlay';
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
import { isSupportedTrack, reviewTracks, reviewOverlay } from '../../viewer/resultReview';
import { CandidateAssessmentPanel } from './CandidateAssessmentPanel';
import type { DemoPreset } from '../../api/transport';

export function LocalWorkbench({ overview, navigation }: { overview?: ReactNode; navigation?: ReactNode } = {}) {
  const sequence = useLocalSequence(), playback = useFramePlayback(sequence.frames);
  const analysis = useAnalysisJob();
  const [manifest, setManifest] = useState<SequenceInput | null>(null);
  const [diagnostics, setDiagnostics] = useState<unknown>(null), [uploadError, setUploadError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [showCandidates, setShowCandidates] = useState(true);
  const [showAllTracks, setShowAllTracks] = useState(false);
  const [historyCoordinates, setHistoryCoordinates] = useState<HistoryCoordinates>('original');
  const [showGapEstimates, setShowGapEstimates] = useState(true);
  const [mode, setMode] = useState<'standard' | 'temporal' | 'demo'>('standard');
  const [demoPreset, setDemoPreset] = useState<DemoPreset>('1');
  const [submittedMode, setSubmittedMode] = useState<'standard' | 'temporal'>('standard');
  const [visibility, setVisibility] = useState({ detections: true, tracks: true, predictions: true });
  const result = analysis.state.phase === 'succeeded' ? analysis.state.result : null;
  const busy = ['submitting', 'queued', 'processing', 'awaiting_result'].includes(analysis.state.phase);
  const presentation = presentAnalysis(analysis.state);
  useEffect(() => { analysis.reset(); setManifest(null); setDiagnostics(null); setUploadError(null); setSelected(null); setShowCandidates(true); }, [sequence.frames, analysis.reset]);
  useEffect(() => {
    if (!result) return;
    const request = new AbortController();
    getJobDiagnostics(result.job_id, request.signal).then(data => {
      setDiagnostics(data);
      if (submittedMode === 'temporal' && (data as {detection_mode?: {name?: string}})?.detection_mode?.name !== 'temporal')
        setUploadError('This backend returned Standard results and does not support Motion mode. These overlays show its actual Standard detections.');
    }).catch(error => { if (!request.signal.aborted) setUploadError(String(error)); });
    // Prefer an actual multi-frame path over an unrelated single-frame candidate.
    setSelected([...reviewTracks(result, false)].sort((a, b) => b.observed_count - a.observed_count)[0]?.track_id ?? null);
    return () => request.abort();
  }, [result, submittedMode]);
  const submit = () => {
    if (mode === 'demo') return;
    try { const next = buildUploadManifest(sequence.frames); setManifest(next); setDiagnostics(null); setUploadError(null); setSubmittedMode(mode); analysis.upload(next, sequence.frames.map(frame => frame.file), mode); }
    catch (error) { setUploadError(error instanceof Error ? error.message : 'Invalid upload'); }
  };
  const input = useRef<HTMLInputElement>(null), id = useId();
  const current = sequence.frames[playback.index];
  const model = useMemo(() => result && current && manifest ? reviewOverlay(uploadOverlay(result, current, playback.index, manifest, diagnostics, historyCoordinates, showGapEstimates), result, showCandidates, playback.index) : { detections: [], tracks: [], warnings: [] }, [result, current, manifest, diagnostics, playback.index, showCandidates, historyCoordinates, showGapEstimates]);
  const reviewedTracks = result ? reviewTracks(result, showCandidates) : [];
  const visibleTracks = model.tracks.filter(track => showAllTracks || track.id === selected);
  const supportedCount = result?.tracks.filter(isSupportedTrack).length ?? 0;
  useEffect(() => {
    if (!result) return;
    const choices = reviewTracks(result, showCandidates);
    if (!choices.some(track => track.track_id === selected)) setSelected([...choices].sort((a,b) => b.observed_count - a.observed_count)[0]?.track_id ?? null);
  }, [result, showCandidates, selected]);
  const track = result?.tracks.find(track => track.track_id === selected);
  const ready = !!current && !sequence.loading && !sequence.draft.length;
  const choose = () => { playback.pause(); input.current?.click(); };
  const download = (format: 'pdf' | 'json') => {
    if (!result || !manifest) return;
    try {
      const report = buildTrackReport(result, manifest, sequence.frames, selected, diagnostics);
      if (format === 'pdf') downloadPdfReport(report); else downloadTrackReport(report);
    }
    catch (error) { setUploadError(error instanceof Error ? error.message : 'Report download failed'); }
  };
  const changeMode = (next: 'standard' | 'temporal' | 'demo') => {
    playback.pause(); analysis.reset(); setDiagnostics(null); setUploadError(null); setSelected(null);
    setMode(next); setSubmittedMode('standard');
    if (next === 'demo') analysis.run(demoPreset);
  };
  const modeControl = <label className="analysis-mode-control">Detection mode <select aria-label="Detection mode" value={mode} disabled={busy} onChange={e => changeMode(e.target.value as 'standard' | 'temporal' | 'demo')}><option value="standard">Standard · uploaded images</option><option value="temporal">Motion · experimental uploaded images</option><option value="demo">Synthetic demo · run automatically</option></select></label>;
  if (mode === 'demo') return <section className="workbench-shell local-workbench" aria-label="Mission image workbench" data-source="synthetic_demo" data-job-id={result?.job_id} data-analysis-phase={analysis.state.phase}>
    <header className="workbench-overview">{overview}{navigation}</header>
    {modeControl}
    <label className="analysis-mode-control">Demo sequence <select aria-label="Demo sequence" value={demoPreset} disabled={busy} onChange={e => { const next=e.target.value as DemoPreset; setDemoPreset(next); analysis.run(next); }}>
      <option value="1">Demo 1 · two objects, horizontal paths</option>
      <option value="2">Demo 2 · two objects, diagonal paths</option>
      <option value="3">Demo 3 · three objects, different directions</option>
      <option value="4">Demo 4 · three objects, curved paths</option>
    </select></label>
    {demoPreset === '4' && <p className="analysis-note">Curved observed motion · forecasts use the backend's linear fit and may differ from the continuing curve.</p>}
    <p className="analysis-note">Synthetic demonstration · five backend-generated frames, processed by the real analysis pipeline. These are not uploaded telescope observations. Your local image selection is preserved.</p>
    <div className="sequence-feedback" role={analysis.state.phase === 'failed' ? 'alert' : 'status'}><strong>{presentation.label}</strong> · {presentation.description}
      {busy ? <><progress aria-label="Analysis progress" /><button type="button" onClick={analysis.cancel}>Stop monitoring</button></> : <button type="button" onClick={() => analysis.run(demoPreset)}>Run demo again</button>}
    </div>
    {result && <AnalysisResults result={result} />}
  </section>;
  return <section id="observations" className="workbench-shell local-workbench" aria-label="Mission image workbench" data-source={result ? 'uploaded_images' : 'local_preview'} data-job-id={result?.job_id} data-analysis-phase={analysis.state.phase}>
    <header className="workbench-overview"><div className="workbench-overview-main">{overview}
      {current && <dl className="observation-summary" aria-label="Confirmed local sequence summary">
        <div><Icon name="image" /><div><dt>Frames loaded</dt><dd>{sequence.frames.length}</dd><small>Confirmed sequence</small></div></div>
        <div><Icon name="scan" /><div><dt>Native dimensions</dt><dd>{`${current.width_px} × ${current.height_px}`}</dd><small>Original pixels</small></div></div>
      </dl>}
    </div><div className="workbench-overview-controls">{navigation}</div></header>
    <header className="observation-toolbar" aria-label="Image selection and sequence controls">
      <div className="observation-toolbar-heading"><Icon name="image" /><div><h2>Optical observations</h2><p>Local Image Preview · Analysis uploads your confirmed sequence.</p></div></div>
      <div className="source-actions" role="group" aria-label="Image selection">
        <button className="button button--primary button--small" type="button" onClick={choose}><Icon name="plus" />{current ? 'Replace images' : 'Choose images'}</button>
        <button className="button button--secondary button--small" type="button" aria-label="Analyze local images" title="Analyze five confirmed images" disabled={!ready || busy || sequence.frames.length !== 5} onClick={submit}><Icon name="scan" /><span className="local-analysis-control-label">Analyze local images</span></button>
        {!!(current || sequence.draft.length || sequence.loading) && <button className="button button--quiet button--small" type="button" aria-label="Clear sequence" title="Clear sequence" onClick={() => { playback.pause(); sequence.clear(); }}>Clear</button>}
      </div>
    </header>
    <input ref={input} className="visually-hidden" type="file" multiple accept="image/jpeg,image/png,.jpg,.jpeg,.png" aria-label="Select telescope images" tabIndex={-1}
      onChange={event => { const files = Array.from(event.currentTarget.files ?? []); event.currentTarget.value = ''; if (files.length) { playback.pause(); void sequence.select(files); } }} />
    {modeControl}
    {mode === 'temporal' && <p className="analysis-note">Experimental mode for compact stationary star fields. Use Standard for ESA streak images; Motion performed worse on that evaluation. Slow targets may be suppressed. Original detections remain in Report JSON.</p>}
    <div className="local-sequence-notice"><Icon name="shield" /><span>Confirm exactly five grayscale telescope frames, then Analyze to upload them to the analysis service. Timestamps are unknown.</span></div>
    {analysis.state.phase !== 'idle' && <div className="sequence-feedback" role={analysis.state.phase === 'failed' ? 'alert' : 'status'}>
      <strong>{presentation.label}</strong> · {presentation.description}
      {analysis.state.phase === 'failed' && <span> Error: {analysis.state.error.code}.</span>}
      {busy && <><progress aria-label="Analysis progress" value={presentation.progress ?? undefined} max={1} /><button type="button" onClick={analysis.cancel}>Stop monitoring</button></>}
    </div>}
    {uploadError && <div className="sequence-feedback sequence-feedback--error" role="alert">{uploadError}</div>}
    {result && <div className="demo-overlay-controls" aria-label="Upload overlay visibility">{(['detections','tracks','predictions'] as const).map(key => <label key={key}><input type="checkbox" checked={visibility[key]} onChange={event => setVisibility(v => ({...v, [key]:event.target.checked}))} />{key}</label>)}<label><input type="checkbox" checked={showCandidates} onChange={event => setShowCandidates(event.target.checked)} />Show uncertain candidates</label><label><input type="checkbox" checked={showAllTracks} onChange={event => setShowAllTracks(event.target.checked)} />Show all tracks</label></div>}
    {result && <p className="analysis-note">{supportedCount} supported tracks · {result.tracks.length - supportedCount} unverified candidate tracks. Supported view requires at least 3 observations, quality ≥ 0.5 and a stable fitted path with at least 2 px of displacement.</p>}
    {result && <><label className="analysis-mode-control">Path view <select aria-label="Path coordinate view" value={historyCoordinates} onChange={e=>setHistoryCoordinates(e.target.value as HistoryCoordinates)}>
      <option value="original">Original image path · retain each frame's positions</option><option value="registered">Registered motion · camera corrected</option>
    </select></label><p className="analysis-note">{historyCoordinates === 'original'
      ? 'Dots retain their original positions from each source image. This path includes camera movement; past dots are historical positions, not current detections. Forecasts are separately projected into the current image.'
      : 'Past observations are camera corrected and projected into the current image. The path shows motion relative to the registered scene.'}</p></>}
    {result && historyCoordinates === 'original' && <><label className="analysis-mode-control"><input type="checkbox" aria-label="Show estimated gap positions" checked={showGapEstimates} onChange={e=>setShowGapEstimates(e.target.checked)} />Show estimated gap positions</label>
      {showGapEstimates && <p className="analysis-note">Hollow amber dots and dashed lines estimate missed positions using camera registration and the last observed location. They are not detections or future forecasts and do not increase the observation count.</p>}</>}
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
        overlay={scale => <ScientificOverlay model={model} scale={scale} selected={selected} select={setSelected} visibility={visibility} currentFrame={playback.index} showAllTracks={showAllTracks} uncertainTrackIds={new Set(result?.tracks.filter(t=>!isSupportedTrack(t)).map(t=>t.track_id))}
          nativeSize={current ? { width: current.width_px, height: current.height_px } : undefined} />} />
      {!!model.warnings.length && <p className="analysis-note" role="status">{model.warnings.join(' ')}</p>}
      {result && !model.warnings.length && !model.detections.length && <p className="analysis-note">{!showCandidates && result.detections.length ? 'No supported object in this frame. Enable Show uncertain candidates to inspect the remaining detections.' : 'No candidates in this frame.'}</p>}
      {result && <p className="t08-forecast-status" data-final-frame={playback.index === sequence.frames.length - 1}>
        {playback.index === sequence.frames.length - 1 ? 'Final frame · ' : ''}
        {visibleTracks.some(t => t.predictions.length) ? 'Short forecast · next frame only. Dashed lines and hollow markers.'
          : result.tracks.some(t => t.trajectory?.predictions.length) ? 'Forecasts appear after the last observation.' : 'Insufficient confirmed observations for trajectory prediction.'}
        {!visibility.predictions && ' Predictions are hidden.'}</p>}
    </div><aside className="track-inspector local-sequence-inspector" aria-label="Sequence inspector" tabIndex={0}>
      <div className="inspector-title"><Icon name="layers" /><h3>Sequence inspector</h3></div>
      <span className="inspector-section-label">Source & status</span>
      <dl className="evidence-values"><div><dt>Source</dt><dd>{result ? 'Uploaded images' : 'Local images'}</dd></div><div><dt>Status</dt><dd>{sequence.loading ? 'Validating' : sequence.draft.length ? 'Review order' : result ? 'Live analysis result' : current ? 'Ready to inspect' : 'Awaiting images'}</dd></div><div><dt>Frames</dt><dd>{sequence.frames.length || 'Not loaded'}</dd></div><div><dt>Dimensions</dt><dd>{current ? `${current.width_px} × ${current.height_px} px` : 'Not available'}</dd></div><div><dt>Timestamps</dt><dd>Unknown</dd></div><div><dt>Analysis</dt><dd>{analysis.state.phase === 'idle' ? 'Not performed' : analysis.state.phase}</dd></div></dl>
      <section className="inspector-frame-card" aria-label="Frame order">
      <span className="inspector-section-label inspector-frames-label"><Icon name="layers" />Frame order</span>
      {!current && <div className="inspector-empty-sequence"><span className="empty-frame-stack" aria-hidden="true"><i /><i /><i /></span><strong>Choose images to begin</strong><p className="inspector-empty-text">Your confirmed frame order will appear here. Review the order before playback.</p></div>}
      {current && <ol className="confirmed-frame-list" aria-label="Confirmed frame order">{sequence.frames.map((frame, index) => <li key={frame.id}><button type="button" disabled={sequence.loading || !!sequence.draft.length}
        aria-current={index === playback.index ? 'true' : undefined} aria-label={`Inspect frame ${index + 1}: ${frame.file.name}`} onClick={() => playback.seek(index)}>
        <span>{String(index + 1).padStart(2, '0')}</span><img src={frame.url} alt="" width="44" height="33" /><span title={frame.file.name}>{frame.file.name}</span></button></li>)}</ol>}
      </section>
      {result && <><label className="demo-track-selector">Selected track<select aria-label="Select upload track" value={selected ?? ''} onChange={event => setSelected(event.target.value)}>
        {!reviewedTracks.length && <option value="">No supported tracks</option>}{reviewedTracks.map(track => <option key={track.track_id} value={track.track_id}>{track.track_id} · {track.observed_count} observations</option>)}</select></label>
        {track && <><div className="t08-track-colors"><span style={{ color: trackColors(track.track_id).observed }}>● Observed</span><span style={{ color: trackColors(track.track_id).forecast }}>◌ Forecast</span>{showGapEstimates && historyCoordinates === 'original' && <span style={{color:'#ffbe55'}}>◌ Gap estimate</span>}</div>
          {track.observed_count < 2 && <p className="analysis-note">This track has one observation, so there is no observed path to connect. Select a track with two or more observations.</p>}
          <TrackQualityPanel track={track} coordinateFrame={historyCoordinates === 'original' ? 'per_frame_raw_pixels' : result.coordinate_frame} />
          <CandidateAssessmentPanel result={result} diagnostics={diagnostics} track={track} frame={playback.index} />
          <p className="analysis-note" role="status">{track.points.some(p=>p.point_type === 'observed' && p.frame_index === playback.index) ? 'Observed in this frame.' : 'No observation for this track in the current frame; earlier observations remain visible.'}</p>
          <TrackPathDetail track={track} frameIndex={playback.index} coordinateFrame={historyCoordinates === 'original' ? 'per_frame_raw_pixels' : result.coordinate_frame} visibility={visibility} />
          <dl className="evidence-values"><div><dt>Status</dt><dd>{track.status}</dd></div><div><dt>Image-plane speed</dt><dd>{track.trajectory ? track.trajectory.speed.toFixed(3) + ' ' + track.trajectory.speed_unit : 'No fit'}</dd></div>
            <div><dt>Fit RMSE</dt><dd>{track.trajectory?.fit_rmse_px == null ? 'Not provided' : `${track.trajectory.fit_rmse_px.toFixed(3)} px`}</dd></div></dl>
          {!!track.warnings.length && <details><summary>Track notes</summary>{track.warnings.map((warning, i) => <p className="analysis-note" key={i}>{warning}</p>)}</details>}</>}</>}
      {!result && <div className="local-evidence-pending"><span className="inspector-section-label">Local analysis</span><strong>{analysis.state.phase === 'idle' ? 'Not performed' : presentation.label}</strong><p>Detections, track IDs and predictions will appear only with matching backend results.</p></div>}
      <div className="identity-note"><Icon name="info" /><span>Candidate identity remains unverified.</span></div></aside></div>
    <div className="local-playback-dock" role="group" aria-label="Local frame playback">
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
    </div>
    <footer className="workspace-footer"><span><Icon name="info" />Box: current detection · Filled: observed · Purple dashed: forecast · Amber hollow/dashed: estimated gap</span>
      <div className="export-actions">{result ? <><button type="button" className="button button--primary button--small" onClick={() => download('pdf')}><Icon name="download" />Download Report (PDF)</button><button type="button" className="button button--quiet button--small" onClick={() => download('json')}>Report JSON</button><a className="button button--quiet button--small" target="_blank" rel="noopener noreferrer" href={apiUrl(`/api/jobs/${result.job_id}/exports/csv`)}>Backend CSV</a></> : <span>Exports available after analysis</span>}</div></footer>
    {result && <AnalysisResults result={result} showViewer={false} reviewCounts={{ tracks: supportedCount, predictions: visibility.predictions ? visibleTracks.reduce((n,t) => n+t.predictions.length,0) : 0 }} />}
  </section>;
}
