import { useEffect, useRef } from 'react';
import { AppFooter } from './components/layout/AppFooter';
import { AppNavigation } from './components/layout/AppNavigation';
import { useHashRoute } from './hooks/useHashRoute';
import { LandingPage } from './pages/LandingPage';
import { ReadinessPage } from './pages/ReadinessPage';
import { WorkbenchPage } from './pages/WorkbenchPage';

export default function App() {
  const { page, hash } = useHashRoute();
  const main = useRef<HTMLElement>(null);
  const previousHash = useRef(hash);

  useEffect(() => {
    const title = page === 'home' ? 'Optical observation studio'
      : page === 'workbench' ? 'Mission workbench' : 'System readiness';
    document.title = `OrbitTrace · ${title}`;
    if (hash === '#capabilities') {
      document.getElementById('capabilities')?.scrollIntoView({ block: 'start' });
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
      <div className="page-enter" key={page}>
        {page === 'home' ? <LandingPage />
          : page === 'workbench' ? <WorkbenchPage /> : <ReadinessPage />}
      </div>
    </main>
    <AppFooter />
  </>;
}
