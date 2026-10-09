import { HealthPanel } from '../components/HealthPanel';
import { emptyResult } from '../fixtures/empty-result';

export function ReadinessPage() {
  return <div className="container readiness-page">
    <section className="readiness-intro"><div className="readiness-heading"><p className="eyebrow">System readiness</p></div>
      <h1>Know what is available.</h1>
      <p className="lead">Live backend connectivity, current frontend capabilities and the remaining integration boundaries.</p>
      <p className="notice">Candidate identity and physical orbit remain unverified. Synthetic processing does not establish performance on real observations.</p></section>
    <div className="grid"><HealthPanel />
      <section className="panel"><h2>Application capabilities</h2>
        <ul className="application-capabilities"><li><div><strong>Local observation viewer</strong><p>Ordered images, playback, zoom, pan and pixel coordinates.</p></div><span className="ready">Implemented</span></li>
          <li><div><strong>Synthetic Analysis</strong><p>Job submission, polling, results, manifests, frames and aligned overlays. Requires the backend.</p></div><span className="ready">Integrated</span></li>
          <li><div><strong>Local image analysis</strong><p>The frontend upload workflow and registration handling are pending.</p></div><span className="pending">Pending</span></li>
          <li><div><strong>Scientific exports</strong><p>JSON and CSV controls remain disabled.</p></div><span className="pending">Pending</span></li></ul>
        <a className="text-link" href="#/workbench">Open Mission Workbench →</a></section></div>
    <section className="panel fixture"><h2>Illustrative schema fixture</h2>
      <p>This empty example documents the result shape. It is authored for development and is not a detector output or benchmark.</p>
      <details><summary>Inspect example JSON · schema 0.1.0</summary><pre>{JSON.stringify(emptyResult, null, 2)}</pre></details></section>
    <p className="readiness-footnote">CPU first · Native image coordinates · Pixels/frame when timestamps are unknown</p>
  </div>;
}
