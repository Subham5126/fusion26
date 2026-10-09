import { Icon } from '../components/ui/Icon';
import { WorkbenchShell } from '../components/workbench/WorkbenchShell';
import { BackendConnection } from '../components/workbench/BackendConnection';

export function WorkbenchPage() {
  return <div className="container workbench-page"><div className="workbench-page-heading"><div><p className="eyebrow">MISSION WORKBENCH</p><h1>Follow the evidence.</h1><p>A focused workspace for ordered optical observations.</p></div><a className="button button--secondary" href="#/readiness"><Icon name="activity" />System readiness</a></div>
    <BackendConnection />
    <WorkbenchShell />
    <section className="workbench-guidance" aria-labelledby="workflow-heading"><div><p className="eyebrow">OBSERVATION WORKFLOW</p><h2 id="workflow-heading">An observation-first workflow.</h2></div><ol><li><span>01</span><div><h3>Run the synthetic demo</h3><p>Submit a backend job and inspect its genuine results.</p></div></li><li><span>02</span><div><h3>Inspect local source pixels</h3><p>Confirm your images, then play, scrub, zoom and pan.</p></div></li><li><span>03</span><div><h3>Review the evidence</h3><p>Keep observations distinct from image-plane predictions.</p></div></li></ol><p className="scope-note">The synthetic demo uses backend-generated frames. Local images stay in this browser and are not analyzed or paired with demo results. Local image analysis requires backend registration support.</p></section>
  </div>;
}
