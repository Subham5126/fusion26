import { useEffect } from 'react';
import type { RefObject } from 'react';
import { attachAmbientVisibility } from '../motion/surfaceEffects';

export function useAmbientVisibility(ref: RefObject<HTMLElement | null>) {
  useEffect(() => {
    if (ref.current) return attachAmbientVisibility(ref.current);
  }, [ref]);
}
