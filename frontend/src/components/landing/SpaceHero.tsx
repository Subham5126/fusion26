import { Icon } from '../ui/Icon';
import { MagneticLink } from '../ui/MagneticLink';
import { usePointerSurface } from '../../hooks/usePointerSurface';
import { useAmbientVisibility } from '../../hooks/useAmbientVisibility';
import { HeroCanvas3D } from './HeroCanvas3D';

const principles = [
  { icon: 'image', label: 'Optical observations' },
  { icon: 'layers', label: 'Sequence-first research' },
  { icon: 'track', label: 'Image-plane trajectories' },
  { icon: 'shield', label: 'Evidence-led review' },
] as const;

export function SpaceHero() {
  const hero = usePointerSurface<HTMLElement>('hero');
  useAmbientVisibility(hero);
  return <section ref={hero} className="space-hero" aria-labelledby="hero-heading">
    <HeroCanvas3D />
    <div className="hero-art-plane" aria-hidden="true"><img className="hero-artwork" src="/assets/orbittrace-space.webp" alt=""
      width="1536" height="1024" fetchPriority="high" draggable={false} /></div>
    <div className="hero-shade" aria-hidden="true" />
    <div className="hero-atmosphere" aria-hidden="true" />
    <div className="hero-stars" aria-hidden="true"><i /><i /><i /></div>
    <span className="reactive-light hero-light" aria-hidden="true" />
    <div className="container hero-layout">
      <div className="hero-copy">
        <p className="eyebrow hero-eyebrow"><span className="status-dot" />GROUND-BASED OPTICAL RESEARCH</p>
        <h1 id="hero-heading">See the Unseen.<br /><span>Track What Moves.</span></h1>
        <p className="hero-description">Explore optical observations and the evidence behind moving-object candidates in one focused scientific workspace.</p>
        <div className="hero-actions"><MagneticLink href="#/workbench">Launch Mission Workbench <Icon name="arrow" /></MagneticLink>
          <a href="#capabilities" className="text-link">Explore the project <Icon name="external" /></a></div>
        <ul className="hero-principles">{principles.map(item => <li key={item.label}><Icon name={item.icon} /><span>{item.label}</span></li>)}</ul>
      </div>
      <div className="hero-art-caption"><span className="hero-caption-line" />SPACE, IN PERSPECTIVE.<small>Decorative illustration · not observation data</small></div>
    </div>
  </section>;
}
