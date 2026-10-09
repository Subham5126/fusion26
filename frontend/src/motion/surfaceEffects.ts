import { pointerVariables } from './pointerGeometry';
import type { PointerSurface, SurfaceBounds } from './pointerGeometry';

/** Event-driven DOM effects: one pending frame per surface, no React updates. */
export function attachPointerSurface(element: HTMLElement, surface: PointerSurface) {
  const preference = window.matchMedia('(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)');
  let bounds: SurfaceBounds | null = null;
  let frame: number | null = null;
  let inside = false;
  let x = 0; let y = 0;
  const written = new Set<string>();
  const reset = () => {
    inside = false;
    if (frame !== null) window.cancelAnimationFrame(frame);
    frame = null; bounds = null;
    element.removeAttribute('data-pointer-active');
    written.forEach(key => element.style.removeProperty(key));
    written.clear();
  };
  const render = () => {
    frame = null;
    if (!inside || !preference.matches || document.hidden) return;
    if (!bounds) {
      const rect = element.getBoundingClientRect();
      bounds = { left: rect.left + window.scrollX, top: rect.top + window.scrollY, width: rect.width, height: rect.height };
    }
    const variables = pointerVariables(x, y, bounds, surface);
    if (!variables) return;
    for (const [key, value] of Object.entries(variables)) { element.style.setProperty(key, value); written.add(key); }
    element.dataset.pointerActive = 'true';
  };
  const move = (event: PointerEvent) => {
    if (event.pointerType !== 'mouse' || !preference.matches || document.hidden) return;
    // The main CTA owns its own feedback; keep the hero still while using it.
    if (surface === 'hero' && event.target instanceof Element && event.target.closest('.magnetic-button')) return;
    inside = true; x = event.pageX; y = event.pageY;
    if (frame === null) frame = window.requestAnimationFrame(render);
  };
  const invalidate = () => { bounds = null; };
  const visibility = () => { if (document.hidden) reset(); };
  const resize = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(invalidate);
  resize?.observe(element);
  element.addEventListener('pointerenter', move, { passive: true });
  element.addEventListener('pointermove', move, { passive: true });
  element.addEventListener('pointerleave', reset);
  element.addEventListener('pointercancel', reset);
  element.addEventListener('animationend', invalidate);
  window.addEventListener('resize', invalidate, { passive: true });
  window.addEventListener('blur', reset);
  document.addEventListener('visibilitychange', visibility);
  preference.addEventListener('change', reset);
  return () => {
    reset(); resize?.disconnect();
    element.removeEventListener('pointerenter', move); element.removeEventListener('pointermove', move);
    element.removeEventListener('pointerleave', reset); element.removeEventListener('pointercancel', reset);
    element.removeEventListener('animationend', invalidate); window.removeEventListener('resize', invalidate);
    window.removeEventListener('blur', reset); document.removeEventListener('visibilitychange', visibility);
    preference.removeEventListener('change', reset);
  };
}

export function attachAmbientVisibility(element: HTMLElement) {
  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  let inView = true;
  const update = () => { element.dataset.ambientRunning = String(inView && !document.hidden && !preference.matches); };
  const observer = typeof IntersectionObserver === 'undefined' ? null : new IntersectionObserver(entries => {
    inView = entries[0].isIntersecting; update();
  });
  observer?.observe(element); update();
  document.addEventListener('visibilitychange', update);
  preference.addEventListener('change', update);
  return () => { observer?.disconnect(); document.removeEventListener('visibilitychange', update); preference.removeEventListener('change', update); element.removeAttribute('data-ambient-running'); };
}
