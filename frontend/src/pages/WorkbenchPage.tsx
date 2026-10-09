import { Icon } from '../components/ui/Icon';
import { WorkbenchShell } from '../components/workbench/WorkbenchShell';
import { BackendConnection } from '../components/workbench/BackendConnection';

export function WorkbenchPage() {
  return <div className="container workbench-page"><div className="workbench-page-heading"><div><p className="eyebrow">MISSION WORKBENCH</p><h1>Follow the evidence.</h1><p>A focused workspace for ordered optical observations.</p></div><a className="button button--secondary" href="#/readiness"><Icon name="activity" />System readiness</a></div>
    <BackendConnection />
    <WorkbenchShell />
    <section className="workbench-guidance" aria-labelledby="workflow-heading"><div><p className="eyebrow">WHAT COMES NEXT</p><h2 id="workflow-heading">An observation-first workflow.</h2></div><ol><li><span>01</span><div><h3>Load ordered frames</h3><p>Keep image order and acquisition metadata together.</p></div></li><li><span>02</span><div><h3>Inspect candidate evidence</h3><p>Review actual observations, uncertainty, and associations.</p></div></li><li><span>03</span><div><h3>Trace & export</h3><p>Separate observed and predicted points with explicit units.</p></div></li></ol><p className="scope-note">This increment provides the visual shell. Image loading, processing, playback, tracking, and scientific exports are planned.</p></section>
  </div>;
}
