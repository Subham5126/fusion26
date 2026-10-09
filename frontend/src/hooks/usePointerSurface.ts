import { useEffect, useRef } from 'react';
import { attachPointerSurface } from '../motion/surfaceEffects';
import type { PointerSurface } from '../motion/pointerGeometry';

export function usePointerSurface<T extends HTMLElement>(surface: PointerSurface) {
  const ref = useRef<T>(null);
  useEffect(() => {
    if (ref.current) return attachPointerSurface(ref.current, surface);
  }, [surface]);
  return ref;
}
