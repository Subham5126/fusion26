import { CapabilitySection } from '../components/landing/CapabilitySection';
import { SpaceHero } from '../components/landing/SpaceHero';
import { Icon } from '../components/ui/Icon';
import { WorkbenchShell } from '../components/workbench/WorkbenchShell';
import { useScrollReveal } from '../hooks/useScrollReveal';
import { useGsapScrollTrigger } from '../hooks/useGsapScrollTrigger';

export function LandingPage() {
  const revealRoot = useScrollReveal();
  useGsapScrollTrigger(revealRoot);
  return <div ref={revealRoot} className="landing-page"><SpaceHero />
    <div className="container dashboard-preview scroll-reveal"><div className="preview-depth"><WorkbenchShell preview /></div></div>
    <CapabilitySection />
    <section className="container closing-section scroll-reveal" aria-labelledby="closing-heading"><div><p className="eyebrow">PURPOSE-BUILT FOR INVESTIGATION</p><h2 id="closing-heading">From a point of light.<br /><span>To a trail of evidence.</span></h2><p>A clear place to inspect observations, question a candidate,<br className="desktop-break" /> and understand what the data can actually support.</p></div>
      <div className="closing-actions"><a className="button button--primary" href="#/workbench">Enter the workbench <Icon name="arrow" /></a><a className="text-link" href="#/readiness"><Icon name="activity" />Check system readiness</a><span>Research prototype · image-plane scope</span></div>
    </section>
  </div>;
}
