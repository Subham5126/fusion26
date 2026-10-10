import { useEffect, useRef } from 'react';

export function CustomCursor() {
  const root = useRef<HTMLDivElement>(null), ring = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = root.current;
    if (!element) return;
    const reduced = matchMedia('(prefers-reduced-motion: reduce)'), coarse = matchMedia('(pointer: coarse)');
    let x = -100, y = -100, rx = x, ry = y, raf = 0;
    const enabled = () => !reduced.matches && !coarse.matches && !document.hidden;
    const stop = () => { cancelAnimationFrame(raf); raf = 0; element.classList.remove('is-visible', 'is-clicking'); };
    const draw = () => {
      raf = 0;
      if (!enabled()) { stop(); return; }
      rx = x; ry = y;
      if (ring.current) ring.current.style.transform = `translate3d(${rx}px,${ry}px,0)`;
      if (Math.abs(x-rx)+Math.abs(y-ry) > .2) raf=requestAnimationFrame(draw);
    };
    const move = (event: PointerEvent) => {
      const target = event.target instanceof Element ? event.target : null;
      // Never obscure scientific pixel inspection or editing controls.
      if (!enabled() || event.pointerType === 'touch' || target?.closest('.image-viewport, [aria-label="Image inspection"], input, select, textarea')) { stop(); return; }
      x=event.clientX; y=event.clientY;
      if (!element.classList.contains('is-visible')) {rx=x;ry=y;}
      element.classList.add('is-visible');
      element.classList.toggle('is-hovered', !!target?.closest('a,button,summary,.capability-card'));
      if (!raf) raf=requestAnimationFrame(draw);
    };
    const down = () => { if(enabled()) element.classList.add('is-clicking'); };
    const up = () => element.classList.remove('is-clicking');
    window.addEventListener('pointermove',move,{passive:true});window.addEventListener('pointerdown',down);
    window.addEventListener('pointerup',up);window.addEventListener('blur',stop);
    document.addEventListener('pointerleave',stop);document.addEventListener('visibilitychange',stop);
    reduced.addEventListener('change',stop);coarse.addEventListener('change',stop);
    return () => { stop();window.removeEventListener('pointermove',move);window.removeEventListener('pointerdown',down);
      window.removeEventListener('pointerup',up);window.removeEventListener('blur',stop);document.removeEventListener('pointerleave',stop);
      document.removeEventListener('visibilitychange',stop);reduced.removeEventListener('change',stop);coarse.removeEventListener('change',stop); };
  }, []);
  return <div ref={root} className="custom-cursor-container" aria-hidden="true"><div ref={ring} className="custom-cursor-ring" /></div>;
}
