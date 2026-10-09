import { Icon } from '../components/ui/Icon';
import { WorkbenchShell } from '../components/workbench/WorkbenchShell';

export function WorkbenchPage() {
  return <div className="container workbench-page">
    <div className="workbench-page-heading"><div><h1>Mission Workbench</h1><p>Inspect frames and candidate evidence.</p></div></div>
    <nav className="workspace-section-navigation" aria-label="Workbench sections"><button type="button" aria-label="Optical observations" onClick={() => document.getElementById('observations')?.scrollIntoView({ block: 'start' })}><Icon name="image" /><span className="workspace-nav-full">Optical observations</span><span className="workspace-nav-compact">Observations</span></button></nav>
    <WorkbenchShell />
  </div>;
}
