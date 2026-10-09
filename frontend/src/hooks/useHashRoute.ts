import { useEffect, useState } from 'react';

export type AppPage = 'home' | 'workbench' | 'readiness';

function resolvePage(hash: string): AppPage {
  if (hash === '#/workbench') return 'workbench';
  if (hash === '#/readiness' || hash === '#system-diagnostics') return 'readiness';
  return 'home';
}

export function useHashRoute() {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const onChange = () => setHash(window.location.hash);
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return { hash, page: resolvePage(hash) };
}
