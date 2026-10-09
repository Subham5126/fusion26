export function Brand({ compact = false }: { compact?: boolean }) {
  return <a className={`brand-link ${compact ? 'brand-link--compact' : ''}`}
    href="#/" aria-label="OrbitTrace home">
    <span className="brand-symbol" aria-hidden="true"><span /></span>
    <span>Orbit<span className="brand-accent">Trace</span></span>
  </a>;
}
