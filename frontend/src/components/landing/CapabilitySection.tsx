import { Icon } from '../ui/Icon';
import { usePointerSurface } from '../../hooks/usePointerSurface';

const capabilities = [
  { icon: 'scan', title: 'Optical image analysis', description: 'Find compact and streak-like candidates in ordered telescope images.', detail: 'The planned CPU pipeline uses image-only proposals. It will retain source evidence and support empty frames.' },
  { icon: 'layers', title: 'Multi-frame tracking', description: 'Follow candidate observations across an image sequence.', detail: 'Planned gated association connects observations with persistent IDs. Missing observations stay distinct from predictions.' },
  { icon: 'track', title: 'Trajectory visualization', description: 'Inspect a short path in a declared image coordinate frame.', detail: 'Planned image-plane fits use px/frame or px/s. They do not establish physical orbits, altitude, or collision probability.' },
  { icon: 'file', title: 'Evidence & exports', description: 'Connect every candidate to its observations and provenance.', detail: 'Planned JSON and CSV reports preserve units and observed/predicted point types. Scientific exports are not available yet.' },
] as const;

function CapabilityCard({ item, index }: { item: typeof capabilities[number]; index: number }) {
  const ref = usePointerSurface<HTMLDivElement>('card');
  return <div ref={ref} className="capability-frame scroll-reveal"><details className="capability-card">
    <summary><div className="capability-top"><Icon name={item.icon} /><span className="capability-index">0{index + 1}</span></div>
      <h3>{item.title}</h3><p>{item.description}</p><div className="capability-bottom"><span className="state-label">Planned</span><span className="capability-expand">View scope <Icon name="plus" /></span></div></summary>
    <span className="reactive-light card-light" aria-hidden="true" /><span className="card-rim-light" aria-hidden="true" />
    <div className="capability-detail"><p>{item.detail}</p><a className="text-link" href="#/workbench">Explore workspace <Icon name="arrow" /></a></div>
  </details></div>;
}

export function CapabilitySection() {
  return <section id="capabilities" className="container capabilities-section" aria-labelledby="capabilities-heading">
    <div className="section-heading scroll-reveal"><div><p className="eyebrow">THE RESEARCH WORKFLOW</p><h2 id="capabilities-heading">Small signals. <span>Connected evidence.</span></h2></div>
      <p>Four parts of one scientific workflow.<br />Processing capabilities are planned.</p></div>
    <div className="capability-grid">{capabilities.map((item, index) => <CapabilityCard key={item.title} item={item} index={index} />)}</div>
  </section>;
}
