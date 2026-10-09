import { T08Overlay } from './T08Overlay';
import type { T08OverlayProps } from './T08Overlay';

// Preserve the API workflow's overlay interface and verified geometry.
export function ScientificOverlay(props: T08OverlayProps) { return <T08Overlay {...props} />; }
