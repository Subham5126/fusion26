import { Icon } from '../ui/Icon';
import { usePointerSurface } from '../../hooks/usePointerSurface';

const capabilities = [
  { icon: 'image', title: 'Optical detection', state: 'Local & synthetic', description: 'Find space-object candidates in telescope imagery.', detail: 'Local JPEG and PNG sequences support confirmed frame order, playback, zoom, pan and native pixel inspection. Images remain in your browser; local analysis is awaiting integration.' },
  { icon: 'scan', title: 'Persistent tracks', state: 'Linked frames', description: 'Link detections across frames into coherent tracks.', detail: 'The synthetic workflow retrieves actual job results and matching source PNGs. Backend-generated inputs are explicitly labelled as synthetic. Local observations are never paired with these results.' },
  { icon: 'track', title: 'Short-term prediction', state: 'Image plane', description: 'Predict near-future image-plane positions for each candidate.', detail: 'Returned tracks preserve observation counts, quality and units. Observed points are solid; predictions are dashed. Image-plane fits do not establish physical orbits, altitude or collision probability.' },
  { icon: 'file', title: 'Observation evidence', state: 'Inspected diagnostics', description: 'Inspect supporting imagery and track diagnostics.', detail: 'Job manifests and result tables are connected to the synthetic backend workflow. Local metadata is available independently. JSON and CSV export controls remain disabled until implemented.' },
] as const;

function CapabilityCard({ item, index }: { item: typeof capabilities[number]; index: number }) {
  const ref = usePointerSurface<HTMLDivElement>('card');
  return <div ref={ref} className="capability-frame scroll-reveal"><details className="capability-card">
    <summary><div className="capability-top"><Icon name={item.icon} /><span className="capability-index">0{index + 1}</span></div>
      <h3>{item.title}</h3><p>{item.description}</p><div className="capability-bottom"><span className="state-label">{item.state}</span><span className="capability-expand">Details <Icon name="plus" /></span></div></summary>
    <div className="capability-detail"><p>{item.detail}</p><a className="text-link" href="#/workbench">Explore workspace <Icon name="arrow" /></a></div>
  </details></div>;
}

export function CapabilitySection() {
  return <section id="capabilities" className="container capabilities-section" aria-labelledby="capabilities-heading">
    <div className="section-heading scroll-reveal"><div><p className="eyebrow">SPACE OBJECT INTELLIGENCE</p><h2 id="capabilities-heading">Your mission. <span>In focus.</span></h2></div>
      <p>A unified workbench for optical space-object candidate detection,<br className="desktop-break" />tracking, and short-term image-plane trajectory prediction.</p></div>
    <div className="capability-grid">{capabilities.map((item, index) => <CapabilityCard key={item.title} item={item} index={index} />)}</div>
  </section>;
}
