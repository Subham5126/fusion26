import { useEffect } from 'react';
import { CapabilitySection } from '../components/landing/CapabilitySection';
import { SpaceHero } from '../components/landing/SpaceHero';
import { Icon } from '../components/ui/Icon';
import { useScrollReveal } from '../hooks/useScrollReveal';

export function LandingPage() {
  const revealRoot = useScrollReveal();
  useEffect(() => {
    // The page can arrive after the hash router's effect when its graphics bundle loads.
    if (window.location.hash === '#capabilities') document.getElementById('capabilities')?.scrollIntoView({ block: 'start' });
  }, []);
  return <div ref={revealRoot} className="landing-page"><SpaceHero />
    <CapabilitySection />
    <section className="container closing-section scroll-reveal" aria-labelledby="closing-heading"><div><p className="eyebrow">PURPOSE-BUILT FOR INVESTIGATION</p><h2 id="closing-heading">From a point of light.<br /><span>To a trail of evidence.</span></h2><p>A clear place to inspect observations, question a candidate,<br className="desktop-break" /> and understand what the data can actually support.</p></div>
      <div className="closing-actions"><a className="text-link" href="#/readiness"><Icon name="activity" />Check system readiness</a><span>Ground-based observations · image-plane evidence</span></div>
    </section>
  </div>;
}
