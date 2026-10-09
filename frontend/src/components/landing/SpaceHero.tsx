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
    <div className="hero-art-plane" aria-hidden="true"><img className="hero-artwork" src="/assets/orbittrace-earth-background.webp" alt=""
      width="1536" height="1024" fetchPriority="high" draggable={false} /></div>
    <div className="hero-shade" aria-hidden="true" />
    <div className="hero-atmosphere" aria-hidden="true" />
    <div className="hero-stars" aria-hidden="true"><i /><i /><i /></div>
    <div className="container hero-layout">
      <div className="hero-copy">
        <p className="eyebrow hero-eyebrow"><span className="status-dot" />SPACE OBJECT INTELLIGENCE</p>
        <h1 id="hero-heading">Orbit<span className="brand-accent">Trace</span></h1>
        <p className="hero-subheading">Observe. Track. Anticipate.</p>
        <p className="hero-description">Optical space-object candidate detection and tracking, from telescope imagery to inspectable image-plane predictions.</p>
        <div className="hero-actions"><MagneticLink href="#/workbench">Launch Workbench <Icon name="arrow" /></MagneticLink>
          <a href="#capabilities" className="button button--secondary">Explore the platform</a></div>
        <ul className="hero-principles">{principles.map(item => <li key={item.label}><Icon name={item.icon} /><span>{item.label}</span></li>)}</ul>
      </div>
      <div className="hero-visual"><HeroCanvas3D /><div className="hero-art-caption"><span className="hero-caption-line" />An orbital perspective<small>Decorative illustration · not observation data</small><small>Earth texture: NASA Earth Observatory</small></div></div>
    </div>
  </section>;
}
