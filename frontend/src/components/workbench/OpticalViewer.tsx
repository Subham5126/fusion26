import { useEffect, useId, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Icon } from '../ui/Icon';
import type { ViewerFrame } from '../../viewer/localSequence';
import { boundedView, fittedView, imageTransform, maxZoom, viewportToPixel, zoomAt } from '../../viewer/geometry';
import type { Point, Size, ViewState } from '../../viewer/geometry';

export function OpticalViewer({ frame, onSelect, onStep, onToggle, onError, onReady, overlay, nativeSize, emptyState }: {
  frame?: ViewerFrame; onSelect: () => void; onStep: (direction: number) => void;
  onToggle: () => void; onError: () => void; onReady?: (url: string) => void;
  overlay?: (scale: number) => ReactNode; nativeSize?: Size; emptyState?: ReactNode;
}) {
  const viewport = useRef<HTMLDivElement>(null);
  const drag = useRef<{ id: number; origin: Point; pan: Point } | null>(null);
  const [size, setSize] = useState<Size>({ width: 0, height: 0 });
  const [view, setView] = useState<ViewState>(fittedView);
  const [cursor, setCursor] = useState<Point | null>(null);
  const [loaded, setLoaded] = useState(''), [failed, setFailed] = useState(''), [retry, setRetry] = useState(0);
  const helpId = useId();
  const activeUrl = useRef(frame?.url); activeUrl.current = frame?.url;
  const image = { width: frame?.width_px ?? nativeSize?.width ?? 1, height: frame?.height_px ?? nativeSize?.height ?? 1 };
  const transform = imageTransform(image, size, view);
  const ready = !!frame && loaded === frame.url && failed !== frame.url;
  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const observer = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect;
      setSize({ width, height });
    });
    observer.observe(element); return () => observer.disconnect();
  }, []);
  useEffect(() => {
    setView(current => boundedView(image, size, current)); setCursor(null); drag.current = null;
  }, [size.width, size.height, frame?.url]); // Same-size frames retain inspection zoom; new sequences remount this component.
  useEffect(() => {
    const element = viewport.current;
    if (!element || !ready) return;
    const wheel = (event: WheelEvent) => {
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      const bounds = element.getBoundingClientRect();
      setView(current => zoomAt(image, size, current, current.zoom * Math.exp(-Math.max(-100, Math.min(100, event.deltaY)) * .005),
        { x: event.clientX - bounds.left - element.clientLeft, y: event.clientY - bounds.top - element.clientTop }));
      setCursor(null);
    };
    element.addEventListener('wheel', wheel, { passive: false });
    return () => element.removeEventListener('wheel', wheel);
  }, [ready, image.width, image.height, size.width, size.height]);
  const zoom = (factor: number) => {
    setView(current => zoomAt(image, size, current, current.zoom * factor, { x: size.width / 2, y: size.height / 2 })); setCursor(null);
  };
  const reset = () => { setView(fittedView); setCursor(null); drag.current = null; };
  return <>
    <div className="viewer-toolbar local-viewer-toolbar"><div><span className={`status-dot ${ready ? '' : 'status-dot--muted'}`} />Optical image viewer</div>
      <div className="viewer-tools"><output aria-label="Zoom level">{Math.round(view.zoom * 100)}%</output>
        <button type="button" disabled={!ready || view.zoom <= 1} aria-label="Zoom out" title="Zoom out (−)" onClick={() => zoom(1 / 1.5)}><Icon name="minus" /></button>
        <button type="button" disabled={!ready || view.zoom >= maxZoom} aria-label="Zoom in" title="Zoom in (+)" onClick={() => zoom(1.5)}><Icon name="plus" /></button>
        <button type="button" disabled={!ready} className="viewer-fit" onClick={reset} aria-label="Fit image to viewer" title="Fit image (0)"><Icon name="scan" />Fit</button>
        <button type="button" disabled={!ready} className="viewer-fit" onClick={reset} aria-label="Reset zoom and pan" title="Reset zoom and pan (0)">Reset</button>
      </div>
    </div>
    <div ref={viewport} className={`optical-viewer local-image-viewport ${ready && view.zoom > 1 ? 'is-zoomed' : ''}`}
      role="group" aria-label="Image inspection" aria-describedby={helpId} tabIndex={frame ? 0 : -1}
      onKeyDown={event => {
        if ((event.target as Element).closest('[data-track-control]')) return;
        if (!ready) return;
        if (['+', '=', '-', '0', ' ', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) event.preventDefault();
        if (event.key === '+' || event.key === '=') zoom(1.5);
        else if (event.key === '-') zoom(1 / 1.5);
        else if (event.key === '0') reset();
        else if (event.key === ' ') onToggle();
        else if (event.shiftKey && event.key.startsWith('Arrow')) {
          const dx = event.key === 'ArrowLeft' ? 40 : event.key === 'ArrowRight' ? -40 : 0;
          const dy = event.key === 'ArrowUp' ? 40 : event.key === 'ArrowDown' ? -40 : 0;
          setView(current => boundedView(image, size, { ...current, pan: { x: current.pan.x + dx, y: current.pan.y + dy } })); setCursor(null);
        } else if (event.key === 'ArrowLeft') onStep(-1);
        else if (event.key === 'ArrowRight') onStep(1);
      }}
      onPointerDown={event => {
        if ((event.target as Element).closest('[data-track-control]')) return;
        if (!ready || view.zoom <= 1 || event.button !== 0) return;
        event.currentTarget.focus(); event.currentTarget.setPointerCapture(event.pointerId);
        const bounded = boundedView(image, size, view);
        drag.current = { id: event.pointerId, origin: { x: event.clientX, y: event.clientY }, pan: bounded.pan };
      }}
      onPointerMove={event => {
        if (!ready) return;
        if (drag.current?.id === event.pointerId) {
          const start = drag.current;
          setView(current => boundedView(image, size, { ...current, pan: { x: start.pan.x + event.clientX - start.origin.x, y: start.pan.y + event.clientY - start.origin.y } }));
          setCursor(null);
        } else {
          const bounds = event.currentTarget.getBoundingClientRect();
          setCursor(viewportToPixel({ x: event.clientX - bounds.left - event.currentTarget.clientLeft, y: event.clientY - bounds.top - event.currentTarget.clientTop }, image, transform));
        }
      }}
      onPointerUp={event => { drag.current = null; if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId); }}
      onPointerCancel={() => { drag.current = null; setCursor(null); }} onLostPointerCapture={() => { drag.current = null; }}
      onBlur={() => { drag.current = null; }} onPointerLeave={() => { if (!drag.current) setCursor(null); }}>
      {frame ? <>
        <div className="image-coordinate-plane" data-coordinate-frame="decoded_image" style={{ width: image.width, height: image.height,
          transform: `translate(${transform.left}px, ${transform.top}px) scale(${transform.scale})`, visibility: ready ? 'visible' : 'hidden' }}>
          <img key={`${frame.url}-${retry}`} src={frame.url} width={image.width} height={image.height} draggable={false}
            alt={frame.label ?? `Telescope frame: ${frame.file?.name ?? 'observation'}`} onLoad={() => { if (activeUrl.current !== frame.url) return; setLoaded(frame.url); setFailed(''); onReady?.(frame.url); }}
            onError={() => { if (activeUrl.current !== frame.url) return; setFailed(frame.url); onError(); }} />
          <svg className="image-overlay-plane" aria-hidden={overlay ? undefined : true} role={overlay ? 'group' : undefined}
            aria-label={overlay ? 'Scientific image overlays' : undefined} width={image.width} height={image.height}
            viewBox={`-.5 -.5 ${image.width} ${image.height}`}>{ready && overlay?.(transform.scale)}</svg>
        </div>
        {!ready && <div className="viewer-empty" role="status"><Icon name="image" /><h3>{failed === frame.url ? 'This frame could not be displayed.' : 'Loading observation…'}</h3>
          {failed === frame.url && <button className="button button--secondary button--small" type="button" onClick={() => { setFailed(''); setLoaded(''); setRetry(value => value + 1); }}>Retry frame</button>}</div>}
      </> : emptyState ?? <div className="viewer-empty local-viewer-empty"><span className="viewer-reticle" aria-hidden="true" /><span className="viewer-corner-targets" aria-hidden="true" /><Icon name="image" />
        <h3>Bring your observations into focus.</h3><p>Choose 3–30 telescope images, confirm their frame order, and inspect the original pixels.</p>
        <button className="button button--primary button--small" type="button" onClick={onSelect}><Icon name="plus" />Choose images</button>
        <small>JPEG or PNG · images stay in this browser</small>
      </div>}
    </div>
    <div className="image-readout"><span>{frame ? `${frame.width_px} × ${frame.height_px} px · decoded image` : 'Original aspect ratio · native pixel geometry'}</span>
      <output aria-label="Pointer image coordinates">{cursor ? `x ${cursor.x.toFixed(1)} · y ${cursor.y.toFixed(1)} px` : 'Coordinates —'}</output></div>
    <details className="viewer-keyboard-help"><summary>Keyboard shortcuts</summary><p id={helpId}>+ / − zoom · 0 fit · ← / → frames · Space play/pause · Shift + arrows pan · Ctrl/⌘ + wheel zoom</p></details>
  </>;
}
