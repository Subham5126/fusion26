import { useId } from 'react';
import { Icon } from '../ui/Icon';
import { useAnalysisJob } from '../../hooks/useAnalysisJob';
import { presentAnalysis } from '../../state/analysis';
import type { AnalysisResult, TrackPoint } from '../../types/contracts';
import { DemoWorkbench } from './DemoWorkbench';
import { useState } from 'react';
import { emptyResult } from '../../fixtures/empty-result';

const numeric = new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 });
const value = (number: number | null) => number === null ? 'Not provided' : numeric.format(number);

function Warnings({ warnings, label = 'Backend warnings' }: { warnings: string[]; label?: string }) {
  if (!warnings.length) return null;
  return <div className="analysis-warnings"><strong>{label}</strong><ul>{warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></div>;
}

function Points({ points, label }: { points: TrackPoint[]; label: string }) {
  if (!points.length) return <p className="analysis-note">{label}: none returned.</p>;
  return <div className="analysis-table-scroll" role="region" aria-label={label} tabIndex={0}><table>
    <caption>{label} · backend frame indexes start at zero</caption>
    <thead><tr><th>Frame</th><th>Point type</th><th>Reference x (px)</th><th>Reference y (px)</th><th>Timestamp (s)</th><th>Outside field</th></tr></thead>
    <tbody>{points.map((point, index) => <tr key={index}><td>{point.frame_index}</td>
      <td><span className={`analysis-point-type analysis-point-type--${point.point_type}`}>{point.point_type}</span></td>
      <td>{value(point.x_reference_px)}</td><td>{value(point.y_reference_px)}</td><td>{value(point.timestamp_s)}</td>
      <td>{point.out_of_field === null ? 'Unknown' : point.out_of_field ? 'Yes' : 'No'}</td></tr>)}</tbody>
  </table></div>;
}

export function AnalysisResults({ result, showViewer = true, reviewCounts }: { result: AnalysisResult; showViewer?: boolean; reviewCounts?: { tracks: number; predictions: number } }) {
  const predictions = result.tracks.reduce((count, track) => count + (track.trajectory?.predictions.length ?? 0), 0);
  return <div className="analysis-results">
    <div className="analysis-counts" aria-label="Completed analysis counts">
      <div><Icon name="scan" /><span>{reviewCounts ? 'Candidate detections' : 'Detections'}</span><strong>{result.detections.length}</strong></div>
      <div><Icon name="track" /><span>{reviewCounts ? 'Supported tracks' : 'Tracks'}</span><strong>{reviewCounts?.tracks ?? result.tracks.length}</strong></div>
      <div><Icon name="clock" /><span>{reviewCounts ? 'Forecast points shown' : 'Predicted points'}</span><strong>{reviewCounts?.predictions ?? predictions}</strong></div>
    </div>
    {showViewer && <DemoWorkbench result={result} />}
    {showViewer && <p className="analysis-note">Synthetic results belong to this backend job. Local telescope observations remain a separate sequence.</p>}
    <details className="analysis-details"><summary>Inspect detection tables, track history & provenance</summary>
    <Warnings warnings={result.warnings} /><Warnings warnings={result.registration.warnings} label="Registration warnings" />
    <h3>Sequence metadata</h3>
    <dl className="analysis-metadata">
      <div><dt>Job ID</dt><dd>{result.job_id}</dd></div><div><dt>Sequence ID</dt><dd>{result.sequence_id}</dd></div>
      <div><dt>Source / profile</dt><dd>{result.source_type} / {result.profile}</dd></div>
      <div><dt>Schema / coordinate frame</dt><dd>{result.schema_version} / {result.coordinate_frame}</dd></div>
      <div><dt>Time basis / registration</dt><dd>{result.time_basis} / {result.registration.status}</dd></div>
      <div><dt>Runtime</dt><dd>{result.runtime_ms === null ? 'Not provided' : `${value(result.runtime_ms)} ms`}</dd></div>
    </dl>
    <h3>Detections</h3>
    {result.detections.length ? <div className="analysis-table-scroll" role="region" aria-label="Backend detections" tabIndex={0}><table>
      <caption>Original image coordinates · pixels · frame indexes start at zero</caption>
      <thead><tr><th>Detection</th><th>Frame</th><th>Raw x / y (px)</th><th>Raw bounding box (px)</th><th>Kind</th><th>Heuristic quality</th></tr></thead>
      <tbody>{result.detections.map(detection => <tr key={detection.detection_id}><td>{detection.detection_id}</td><td>{detection.frame_index}</td>
        <td>{value(detection.x_raw_px)} / {value(detection.y_raw_px)}</td><td>{detection.bbox_raw_px.map(value).join(', ')}</td>
        <td>{detection.kind}</td><td>{value(detection.quality_score)}</td></tr>)}</tbody>
    </table></div> : <p className="analysis-note">No candidates found in the completed backend result.</p>}
    <h3>Tracks & image-plane predictions</h3>
    {!result.tracks.length && <p className="analysis-note">No tracks returned by the backend.</p>}
    {result.tracks.map((track, index) => <details className="analysis-track" key={track.track_id} open={index === 0}>
      <summary><strong>{track.track_id}</strong><span>{track.status} · {track.observed_count} observations</span></summary>
      <div className="analysis-track-content"><p className="analysis-note">{track.candidate_label}</p>
        <dl className="analysis-metadata"><div><dt>Heuristic quality</dt><dd>{value(track.quality_score)}</dd></div>
          <div><dt>Observed support</dt><dd>{track.observed_count} actual observations</dd></div>
          <div><dt>Image-plane speed</dt><dd>{track.trajectory ? `${value(track.trajectory.speed)} ${track.trajectory.speed_unit}` : 'No fit returned'}</dd></div>
          <div><dt>Fit RMSE</dt><dd>{track.trajectory?.fit_rmse_px == null ? 'Not provided' : `${value(track.trajectory.fit_rmse_px)} px`}</dd></div>
          {track.trajectory && <><div><dt>Fit model / observations used</dt><dd>{track.trajectory.model} / {track.trajectory.observations_used}</dd></div>
            <div><dt>Velocity x / y</dt><dd>{value(track.trajectory.vx)} / {value(track.trajectory.vy)} {track.trajectory.speed_unit}</dd></div></>}
        </dl>
        <Warnings warnings={track.warnings} label="Track warnings" />
        <Points points={track.points} label={`Track ${track.track_id} points`} />
        <Points points={track.trajectory?.predictions ?? []} label={`Track ${track.track_id} extrapolated predictions`} />
      </div>
    </details>)}
    <details className="analysis-provenance"><summary>Backend provenance & metrics</summary>
      <dl className="analysis-metadata">{Object.entries(result.provenance).map(([key, entry]) => <div key={key}><dt>{key}</dt><dd>{entry ?? 'Not provided'}</dd></div>)}</dl>
      {result.metrics === null ? <p className="analysis-note">Benchmark metrics were not provided for this run.</p> : <dl className="analysis-metadata">
        <div><dt>Benchmark / split</dt><dd>{result.metrics.benchmark_id} / {result.metrics.split}</dd></div>
        <div><dt>Matching gate</dt><dd>{value(result.metrics.matching_gate_px)} px</dd></div>
        <div><dt>TP / FP / FN</dt><dd>{result.metrics.tp} / {result.metrics.fp} / {result.metrics.fn}</dd></div>
        <div><dt>Precision / recall</dt><dd>{value(result.metrics.precision)} / {value(result.metrics.recall)}</dd></div>
        <div><dt>Localization RMSE</dt><dd>{result.metrics.localization_rmse_px === null ? 'Not provided' : `${value(result.metrics.localization_rmse_px)} px`}</dd></div>
        {Object.entries(result.metrics.null_reasons).map(([key, reason]) => <div key={key}><dt>{key}</dt><dd>{reason}</dd></div>)}
      </dl>}
    </details>
    </details>
  </div>;
}

export function AnalysisPanel() {
  const [fixture, setFixture] = useState(false);
  const { state, run, cancel } = useAnalysisJob();
  const id = useId();
  const busy = ['submitting', 'queued', 'processing', 'awaiting_result'].includes(state.phase);
  const presentation = presentAnalysis(state);
  const job = 'job' in state ? state.job : undefined;
  const jobId = state.phase === 'queued' ? state.submission.job_id : state.phase === 'cancelled' ? state.jobId : job?.job_id;
  const label = state.phase === 'idle' ? 'Ready' : state.phase === 'succeeded' ? 'Succeeded' : state.phase === 'failed' ? job?.status === 'failed' ? 'Failed' : 'Request failed' : presentation.label;
  return <section id="synthetic-analysis" className="workbench-shell analysis-panel" aria-labelledby={`${id}-heading`} data-source="synthetic">
    <header className="workbench-topbar"><div className="workbench-heading"><span className="workspace-emblem"><Icon name="activity" /></span>
      <div><h2 id={`${id}-heading`}>Synthetic Analysis <span className="simulation-badge">Simulated source</span></h2><p>Backend-generated sequence <span>/</span> Separate from your observations</p></div></div>
      <div className="analysis-actions"><button type="button" className="button button--primary button--small" disabled={busy} onClick={run}><Icon name="scan" />Run Synthetic Demo</button>
        {busy && <button type="button" className="button button--quiet button--small" onClick={cancel}>Stop monitoring</button>}</div>
    </header>
    <div className="analysis-status" role={state.phase === 'failed' ? 'alert' : 'status'} aria-live="polite" aria-atomic="true">
      <span className={`workbench-stage analysis-state--${state.phase}`}><span className={`status-dot ${busy || state.phase === 'succeeded' ? '' : 'status-dot--muted'}`} />{label}</span>
      <p>{state.phase === 'idle' ? 'Run the backend-generated synthetic sequence to inspect detections, tracks and predictions.' : presentation.description}</p>
      {jobId && <small>Job: {jobId}{job ? ` · Backend status: ${job.status} · Stage: ${job.progress_stage}` : ''}</small>}
      {presentation.progress !== null && <label className="analysis-progress">Backend progress: {value(presentation.progress * 100)}%<progress value={presentation.progress} max={1} /></label>}
    </div>
    {state.phase === 'failed' && <div className="analysis-error-details"><strong>Error code: {state.error.code}</strong>
      {state.error.details && <dl className="analysis-metadata">{Object.entries(state.error.details).map(([key, detail]) => <div key={key}><dt>{key}</dt><dd>{detail}</dd></div>)}</dl>}
      <p className="analysis-note">No result was substituted. A new run creates a new backend job.</p></div>}
    {!!job?.warnings.length && <div className="analysis-job-warnings"><Warnings warnings={job.warnings} label="Job warnings" /></div>}
    {state.phase === 'succeeded' && <AnalysisResults key={state.result.job_id} result={state.result} />}
    <button type="button" className="button button--quiet button--small" onClick={() => setFixture(value => !value)}>Toggle contract fixture backup</button>
    {fixture && <div><p role="status">CONTRACT FIXTURE — illustrative empty output, no inference performed.</p><AnalysisResults result={emptyResult} showViewer={false} /></div>}
  </section>;
}
