import type { ReactNode } from 'react';
import { usePointerSurface } from '../../hooks/usePointerSurface';

export function MagneticLink({ href, children }: { href: string; children: ReactNode }) {
  const ref = usePointerSurface<HTMLAnchorElement>('button');
  return <a ref={ref} href={href} draggable={false} className="button button--primary magnetic-button">
    <span className="button-sheen" aria-hidden="true" />
    <span className="magnetic-label">{children}</span>
  </a>;
}
