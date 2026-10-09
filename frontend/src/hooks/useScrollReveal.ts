import { useEffect, useRef } from 'react';

export function useScrollReveal() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const root = ref.current;
    if (!root || typeof IntersectionObserver === 'undefined') return;
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    const elements = Array.from(root.querySelectorAll<HTMLElement>('.scroll-reveal'));
    const revealed = new Set<Element>();
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting || revealed.has(entry.target)) continue;
        revealed.add(entry.target); observer.unobserve(entry.target);
        if (!preference.matches) entry.target.classList.add('is-revealing');
      }
    }, { threshold: .08 });
    const end = (event: AnimationEvent) => { if (event.animationName === 'scroll-reveal' && event.target instanceof Element) event.target.classList.remove('is-revealing'); };
    const reduce = () => { if (preference.matches) elements.forEach(element => element.classList.remove('is-revealing')); };
    elements.forEach(element => observer.observe(element));
    root.addEventListener('animationend', end); preference.addEventListener('change', reduce);
    return () => { observer.disconnect(); root.removeEventListener('animationend', end); preference.removeEventListener('change', reduce); elements.forEach(element => element.classList.remove('is-revealing')); };
  }, []);
  return ref;
}
