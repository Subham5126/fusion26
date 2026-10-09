import { HealthPanel } from '../components/HealthPanel';
import { emptyResult } from '../fixtures/empty-result';

export function ReadinessPage() {
  return <main>
    <header><div className="brand">ORBITTRACE <span>FUSION 2K26 · SPACE-02</span></div>
      <span className="badge">Bootstrap</span></header>
    <section className="intro"><p className="eyebrow">Telescope sequence workbench</p>
      <h1>Evidence behind<br />every candidate.</h1>
      <p className="lead">The foundation is ready. Detection, tracking, and short image-plane trajectories are the next implementation tasks.</p>
      <p className="notice">No analysis has been performed. Object identity remains unverified; performance has not been measured.</p></section>
    <div className="grid"><HealthPanel />
      <section className="panel"><h2>Build the first real sequence</h2>
        <ol className="tasks"><li><strong>T02 / T03 · Data & CV</strong><p>Generate seeded images with separate truth, then detect image-only candidates.</p></li>
          <li><strong>T04 / T06 · Tracking & evaluation</strong><p>Associate observations on the shared fixture and build the matching protocol.</p></li>
          <li><strong>T08 · Viewer</strong><p>Build ordered frames and overlays, with observed and predicted points distinct.</p></li></ol>
        <p className="muted">Integration prepares T07 after detector, tracker, and trajectory handoffs.</p></section></div>
    <section className="panel fixture"><h2>Illustrative schema fixture</h2>
      <p>This empty example documents the result shape. It is authored for development and is not a detector output or benchmark.</p>
      <details><summary>Inspect example JSON · schema 0.1.0</summary><pre>{JSON.stringify(emptyResult, null, 2)}</pre></details></section>
    <footer>CPU first · Native image coordinates · Pixels/frame when timestamps are unknown</footer>
  </main>;
}
