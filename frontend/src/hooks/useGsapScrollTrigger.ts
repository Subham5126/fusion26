import { useEffect } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export function useGsapScrollTrigger(scopeRef: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion || !scopeRef.current) return;

    const ctx = gsap.context(() => {
      // 1. Dashboard Preview 3D Perspective Roll & Lift
      const dashboardPreview = scopeRef.current?.querySelector('.dashboard-preview');
      if (dashboardPreview) {
        gsap.fromTo(
          dashboardPreview,
          {
            opacity: 0.4,
            y: 60,
            scale: 0.94,
            rotationX: 12,
            transformPerspective: 1200,
          },
          {
            opacity: 1,
            y: 0,
            scale: 1,
            rotationX: 0,
            ease: 'power3.out',
            scrollTrigger: {
              trigger: dashboardPreview,
              start: 'top 85%',
              end: 'top 45%',
              scrub: 0.8,
            },
          }
        );
      }

      // 2. Section Headings Reveal
      const headings = scopeRef.current?.querySelectorAll('.section-heading, .closing-section > div:first-child');
      headings?.forEach(heading => {
        gsap.fromTo(
          heading,
          { opacity: 0, y: 35 },
          {
            opacity: 1,
            y: 0,
            duration: 0.85,
            ease: 'power3.out',
            scrollTrigger: {
              trigger: heading,
              start: 'top 88%',
              toggleActions: 'play none none none',
            },
          }
        );
      });

      // 3. Capability Cards Stagger Slide-Up with 3D Depth
      const cards = scopeRef.current?.querySelectorAll('.capability-frame');
      if (cards && cards.length > 0) {
        gsap.fromTo(
          cards,
          {
            opacity: 0,
            y: 45,
            scale: 0.96,
          },
          {
            opacity: 1,
            y: 0,
            scale: 1,
            duration: 0.7,
            stagger: 0.12,
            ease: 'power3.out',
            scrollTrigger: {
              trigger: '.capability-grid',
              start: 'top 85%',
              toggleActions: 'play none none none',
            },
          }
        );
      }

      // 4. Closing CTA Section Actions Reveal
      const closingActions = scopeRef.current?.querySelector('.closing-actions');
      if (closingActions) {
        gsap.fromTo(
          closingActions,
          { opacity: 0, x: 30 },
          {
            opacity: 1,
            x: 0,
            duration: 0.8,
            ease: 'power3.out',
            scrollTrigger: {
              trigger: closingActions,
              start: 'top 88%',
              toggleActions: 'play none none none',
            },
          }
        );
      }
    }, scopeRef);

    return () => {
      ctx.revert();
    };
  }, [scopeRef]);
}
