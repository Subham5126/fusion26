import { Icon } from '../components/ui/Icon';
import { WorkbenchShell } from '../components/workbench/WorkbenchShell';
import { BackendConnection } from '../components/workbench/BackendConnection';

export function WorkbenchPage() {
  return <div className="container workbench-page">
    <div className="workbench-page-heading"><div><h1>Mission Workbench</h1><p>Inspect frames and candidate evidence.</p></div><BackendConnection /></div>
    <nav className="workspace-section-navigation" aria-label="Workbench sections"><button type="button" aria-label="Optical observations" onClick={() => document.getElementById('observations')?.scrollIntoView({ block: 'start' })}><Icon name="image" /><span className="workspace-nav-full">Optical observations</span><span className="workspace-nav-compact">Observations</span></button><button type="button" onClick={() => document.getElementById('synthetic-analysis')?.scrollIntoView({ block: 'start' })}><Icon name="activity" />Synthetic Analysis<span className="simulation-badge">Simulated source</span></button><a className="workspace-readiness-link" aria-label="System readiness" href="#/readiness"><span className="workspace-nav-full">System readiness</span><span className="workspace-nav-compact">Readiness</span><Icon name="external" /></a></nav>
    <WorkbenchShell />
    <p className="workspace-scope"><Icon name="shield" />Local observations and synthetic jobs are independent sources. Predictions describe image-plane motion; object identity and physical orbit remain unverified.</p>
  </div>;
}
