import { useRef, useState } from 'react';
import type { AppPage } from '../../hooks/useHashRoute';
import { Icon } from '../ui/Icon';
import { Brand } from './Brand';

export function AppNavigation({ page, hash }: { page: AppPage; hash: string }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuToggle = useRef<HTMLButtonElement>(null);
  const destinations = [
    { label: 'Home', href: '#/', active: page === 'home' && hash !== '#capabilities' },
    { label: 'Mission Workbench', href: '#/workbench', active: page === 'workbench' },
    { label: 'Capabilities', href: '#capabilities', active: hash === '#capabilities' },
    { label: 'System Readiness', href: '#/readiness', active: page === 'readiness' },
  ];

  return <header className="site-header" onKeyDown={event => {
    if (event.key === 'Escape' && menuOpen) {
      setMenuOpen(false);
      menuToggle.current?.focus();
    }
  }}>
    <div className="container navigation-bar">
      <Brand />
      <button className="menu-toggle button button--quiet" type="button" ref={menuToggle}
        aria-expanded={menuOpen} aria-controls="primary-navigation"
        aria-label={menuOpen ? 'Close navigation' : 'Open navigation'}
        onClick={() => setMenuOpen(value => !value)}>
        <Icon name={menuOpen ? 'close' : 'menu'} />
      </button>
      <nav id="primary-navigation" className={`primary-navigation ${menuOpen ? 'is-open' : ''}`}
        aria-label="Primary">
        {destinations.map(link => <a key={link.href} href={link.href}
          aria-current={link.active ? (link.href === '#capabilities' ? 'location' : 'page') : undefined}
          onClick={() => setMenuOpen(false)}>{link.label}</a>)}
        <a className="button button--primary nav-launch" href="#/workbench"
          onClick={() => setMenuOpen(false)}>Launch Workbench <Icon name="arrow" /></a>
      </nav>
    </div>
  </header>;
}
