import { useId, useState } from 'react';
import { Icon } from '../ui/Icon';
import { ConceptualField } from './ConceptualField';
import { presentAnalysis, unavailableAnalysis } from '../../state/analysis';
import type { AnalysisState } from '../../state/analysis';
import { LocalWorkbench } from './LocalWorkbench';

function TrackInspector() {
  const [tab, setTab] = useState<'evidence' | 'sequence'>('evidence');
  const id = useId();
  return <aside className="track-inspector" aria-label="Track inspector">
    <div className="inspector-title"><Icon name="scan" /><h3>Track inspector</h3></div>
    <div className="inspector-tabs" role="tablist" aria-label="Inspection">
      {(['evidence', 'sequence'] as const).map(name => <button key={name} type="button" role="tab"
        id={`${id}-${name}`} aria-controls={`${id}-panel`} aria-selected={tab === name}
        tabIndex={tab === name ? 0 : -1} onClick={() => setTab(name)}
        onKeyDown={event => {
          if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
            event.preventDefault();
            const next = event.key === 'Home' ? 'evidence' : event.key === 'End' ? 'sequence'
              : name === 'evidence' ? 'sequence' : 'evidence';
            setTab(next);
            document.getElementById(`${id}-${next}`)?.focus();
          }
        }}>{name === 'evidence' ? 'Evidence' : 'Sequence'}</button>)}
    </div>
    <div id={`${id}-panel`} role="tabpanel" aria-labelledby={`${id}-${tab}`} className="inspector-content">
      {tab === 'evidence' ? <><div className="inspector-empty-mark"><Icon name="track" /></div><h4>Every track starts with evidence.</h4>
        <p>Observed points, candidate quality, and fit evidence will appear after a sequence is analyzed.</p>
        <dl className="evidence-values"><div><dt>Observations</dt><dd>—</dd></div><div><dt>Candidate quality</dt><dd>—</dd></div><div><dt>Fit residual</dt><dd>—</dd></div></dl>
      </> : <><div className="inspector-empty-mark"><Icon name="layers" /></div><h4>No sequence selected.</h4>
        <p>Ordered frame metadata will appear here once sequence loading is available.</p>
        <dl className="evidence-values"><div><dt>Source</dt><dd>—</dd></div><div><dt>Frames</dt><dd>—</dd></div><div><dt>Timestamps</dt><dd>Unknown</dd></div></dl></>}
    </div>
    <div className="identity-note"><Icon name="info" /><span>Candidate identity remains unverified.</span></div>
  </aside>;
}

export function WorkbenchShell({ preview = false, analysis = unavailableAnalysis }: { preview?: boolean; analysis?: AnalysisState }) {
  if (!preview) return <LocalWorkbench />;
  const presentation = presentAnalysis(analysis);
  return <section className={`workbench-shell ${preview ? 'workbench-shell--preview' : ''}`}
    aria-label={preview ? 'Conceptual mission workbench preview' : 'Mission workbench shell'}>
    <header className="workbench-topbar"><div className="workbench-heading"><span className="workspace-emblem"><Icon name="scan" /></span><div><h2>Observation workspace</h2><p>OPTICAL SEQUENCES <span>/</span> IMAGE-PLANE EVIDENCE</p></div></div>
      <span className="workbench-stage"><span className="status-dot" />{preview ? 'Conceptual preview' : presentation.label}</span></header>
    <div className="sequence-source"><div className="source-description"><Icon name="layers" /><div><span>Observation sequence</span><strong>No sequence selected</strong></div></div>
      <div className="source-actions"><button className="button button--secondary button--small" type="button" disabled><Icon name="upload" />Load sequence</button>
        <button className="button button--primary button--small" type="button" disabled><Icon name="scan" />Run analysis</button></div></div>
    <div className="workspace-body"><div className="observation-area">
      <div className="viewer-toolbar"><div><span className="status-dot status-dot--muted" />Optical observation viewer</div><div className="viewer-tools"><span>Raw image</span><button type="button" disabled aria-label="Zoom out"><Icon name="minus" /></button><button type="button" disabled aria-label="Zoom in"><Icon name="plus" /></button></div></div>
      <div className={`optical-viewer ${preview ? 'optical-viewer--concept' : ''}`}>
        {preview ? <><ConceptualField /><span className="viewer-concept-label">CONCEPTUAL ILLUSTRATION</span></>
          : <div className="viewer-empty" role="status"><span className="viewer-reticle" aria-hidden="true" /><Icon name="image" /><h3>{presentation.title}</h3><p>{presentation.description}</p></div>}
        <div className="viewer-corner viewer-corner--tl" aria-hidden="true" /><div className="viewer-corner viewer-corner--br" aria-hidden="true" />
        <div className="viewer-bottom"><div className="point-legend"><span><i className="observed-key" />Observed</span><span><i className="predicted-key" />Predicted</span></div><span>{preview ? 'Illustration only' : 'Image plane · no data'}</span></div>
      </div>
      <div className="frame-timeline"><div className="timeline-controls"><button type="button" disabled aria-label="Previous frame"><Icon name="back" /></button><button type="button" disabled className="timeline-play" aria-label="Play frames"><Icon name="play" /></button><button type="button" disabled aria-label="Next frame"><Icon name="next" /></button><span>Frame — / —</span></div><div className="timeline-empty"><span /><span /><span /></div><p>Ordered frames will appear here.</p></div>
    </div><TrackInspector /></div>
    <footer className="workspace-footer"><span><Icon name="info" />{preview ? 'Conceptual layout · no analysis performed' : 'Sequence loading and analysis are not available in this increment.'}</span>
      {preview ? <a href="#/workbench" className="text-link">Open workspace <Icon name="arrow" /></a>
        : <div className="export-actions"><button type="button" className="button button--quiet button--small" disabled><Icon name="download" />JSON</button><button type="button" className="button button--quiet button--small" disabled>CSV</button></div>}
    </footer>
  </section>;
}
