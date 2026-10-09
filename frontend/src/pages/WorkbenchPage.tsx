import { useEffect, useState } from 'react';
import { Icon } from '../components/ui/Icon';
import { WorkbenchShell } from '../components/workbench/WorkbenchShell';
import { BackendConnection } from '../components/workbench/BackendConnection';
import { SystemDiagnostics } from '../components/workbench/SystemDiagnostics';

export function WorkbenchPage({ initialDiagnosticsOpen = false }: { initialDiagnosticsOpen?: boolean }) {
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(initialDiagnosticsOpen);

  useEffect(() => {
    if (initialDiagnosticsOpen || window.location.hash === '#/readiness' || window.location.hash === '#system-diagnostics') {
      setDiagnosticsOpen(true);
      setTimeout(() => {
        document.getElementById('system-diagnostics')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 50);
    }
  }, [initialDiagnosticsOpen]);

  const toggleDiagnostics = () => {
    setDiagnosticsOpen(prev => {
      const next = !prev;
      if (next) {
        setTimeout(() => {
          document.getElementById('system-diagnostics')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 50);
      }
      return next;
    });
  };

  return <div className="container workbench-page">
    <SystemDiagnostics
      isOpen={diagnosticsOpen}
      onClose={() => setDiagnosticsOpen(false)}
    />

    <WorkbenchShell connection={<BackendConnection onToggleDiagnostics={toggleDiagnostics} diagnosticsOpen={diagnosticsOpen} />} overview={<div className="workbench-page-heading"><div className="workbench-title-group">
      <span className="workbench-title-emblem" aria-hidden="true"><Icon name="scan" /></span>
      <div><h1>Mission Workbench</h1><p>Inspect frames and candidate evidence.</p></div>
    </div></div>} navigation={<nav className="workspace-section-navigation" aria-label="Workbench sections">
      <button type="button" aria-label="Optical observations" onClick={() => document.getElementById('observations')?.scrollIntoView({ block: 'start' })}>
        <Icon name="image" />
        <span className="workspace-nav-full">Optical observations</span>
        <span className="workspace-nav-compact">Observations</span>
      </button>
      <button type="button" onClick={() => document.getElementById('synthetic-analysis')?.scrollIntoView({ block: 'start' })}>
        <Icon name="activity" />
        Synthetic Analysis
        <span className="simulation-badge">Simulated source</span>
      </button>
      <button
        type="button"
        className={`workspace-readiness-toggle ${diagnosticsOpen ? 'is-active' : ''}`}
        aria-expanded={diagnosticsOpen}
        aria-controls="system-diagnostics"
        onClick={toggleDiagnostics}
      >
        <Icon name="shield" />
        <span className="workspace-nav-full">System readiness & diagnostics</span>
        <span className="workspace-nav-compact">Readiness</span>
      </button>
    </nav>} />
    <p className="workspace-scope">
      <Icon name="shield" />Local observations and synthetic jobs are independent sources. Predictions describe image-plane motion; object identity and physical orbit remain unverified.
    </p>
  </div>;
}
