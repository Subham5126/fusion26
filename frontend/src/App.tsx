import { lazy, Suspense, useEffect, useRef } from 'react';
import { AppFooter } from './components/layout/AppFooter';
import { AppNavigation } from './components/layout/AppNavigation';
import { useHashRoute } from './hooks/useHashRoute';
import { WorkbenchPage } from './pages/WorkbenchPage';

// Keep the decorative Three.js/GSAP scene out of the scientific workspace's initial bundle.
const LandingPage = lazy(() => import('./pages/LandingPage').then(module => ({ default: module.LandingPage })));

export default function App() {
  const { page, hash } = useHashRoute();
  const main = useRef<HTMLElement>(null);
  const previousHash = useRef(hash);

  useEffect(() => {
    const title = page === 'home' ? 'Optical observation studio' : 'Mission workbench';
    document.title = `OrbitTrace · ${title}`;
    if (hash === '#capabilities' || hash === '#/capabilities') {
      document.getElementById('capabilities')?.scrollIntoView({ block: 'start' });
    } else if (hash === '#/readiness' || hash === '#system-diagnostics') {
      document.getElementById('system-diagnostics')?.scrollIntoView({ block: 'start' });
    } else {
      window.scrollTo({ top: 0, behavior: 'instant' });
    }
    if (previousHash.current !== hash) main.current?.focus({ preventScroll: true });
    previousHash.current = hash;
  }, [page, hash]);

  return <>
    <a className="skip-link" href="#main-content" onClick={event => {
      event.preventDefault();
      main.current?.focus();
    }}>Skip to content</a>
    <AppNavigation page={page} hash={hash} />
    <main id="main-content" ref={main} tabIndex={-1}>
      <div className="page-enter" key={page === 'readiness' ? 'workbench' : page}>
        {page === 'home' ? <Suspense fallback={<div className="container route-loading" role="status">Loading OrbitTrace…</div>}><LandingPage /></Suspense>
          : <WorkbenchPage initialDiagnosticsOpen={page === 'readiness' || hash === '#/readiness' || hash === '#system-diagnostics'} />}
      </div>
    </main>
    <AppFooter />
  </>;
}
