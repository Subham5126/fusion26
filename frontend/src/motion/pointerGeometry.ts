export type PointerSurface = 'hero' | 'card' | 'button';
export interface SurfaceBounds { left: number; top: number; width: number; height: number }

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

/** Decorative coordinates only. Scientific image/track coordinates never enter this module. */
export function pointerVariables(x: number, y: number, bounds: SurfaceBounds, surface: PointerSurface): Record<string, string> | null {
  if (![x, y, bounds.left, bounds.top, bounds.width, bounds.height].every(Number.isFinite) || bounds.width <= 0 || bounds.height <= 0) return null;
  const localX = clamp(x - bounds.left, 0, bounds.width);
  const localY = clamp(y - bounds.top, 0, bounds.height);
  const nx = localX / bounds.width * 2 - 1;
  const ny = localY / bounds.height * 2 - 1;
  const variables: Record<string, string> = { '--pointer-x': `${localX.toFixed(2)}px`, '--pointer-y': `${localY.toFixed(2)}px` };
  if (surface === 'hero') {
    variables['--parallax-x'] = `${(nx * 8).toFixed(2)}px`;
    variables['--parallax-y'] = `${(ny * 6).toFixed(2)}px`;
  } else if (surface === 'card') {
    variables['--tilt-x'] = `${(-ny * 3).toFixed(2)}deg`;
    variables['--tilt-y'] = `${(nx * 3).toFixed(2)}deg`;
  } else {
    variables['--magnet-x'] = `${(nx * 3).toFixed(2)}px`;
    variables['--magnet-y'] = `${(ny * 2).toFixed(2)}px`;
  }
  return variables;
}
