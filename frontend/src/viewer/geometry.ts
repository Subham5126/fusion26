export interface Point { x: number; y: number }
export interface Size { width: number; height: number }
export interface ViewState { zoom: number; pan: Point }
export interface ImageTransform { scale: number; left: number; top: number }
export const fittedView: ViewState = { zoom: 1, pan: { x: 0, y: 0 } };
export const maxZoom = 8;

export function imageTransform(image: Size, viewport: Size, view: ViewState): ImageTransform {
  const fit = Math.min(viewport.width / image.width, viewport.height / image.height);
  const scale = Math.max(0, fit) * view.zoom;
  const limitX = Math.max(0, (image.width * scale - viewport.width) / 2);
  const limitY = Math.max(0, (image.height * scale - viewport.height) / 2);
  return { scale, left: (viewport.width - image.width * scale) / 2 + clamp(view.pan.x, -limitX, limitX),
    top: (viewport.height - image.height * scale) / 2 + clamp(view.pan.y, -limitY, limitY) };
}

export function clamp(value: number, min: number, max: number) { return Math.min(max, Math.max(min, value)); }

export function boundedView(image: Size, viewport: Size, view: ViewState): ViewState {
  const zoom = clamp(view.zoom, 1, maxZoom);
  const transform = imageTransform(image, viewport, { ...view, zoom });
  return { zoom, pan: { x: transform.left - (viewport.width - image.width * transform.scale) / 2,
    y: transform.top - (viewport.height - image.height * transform.scale) / 2 } };
}

// Contract 0.1.0 pixel centers are integers; raster edges start half a pixel earlier.
export function pixelToViewport(pixel: Point, transform: ImageTransform): Point {
  return { x: transform.left + (pixel.x + .5) * transform.scale, y: transform.top + (pixel.y + .5) * transform.scale };
}
export function viewportToPixel(point: Point, image: Size, transform: ImageTransform): Point | null {
  if (transform.scale <= 0) return null;
  const x = (point.x - transform.left) / transform.scale - .5;
  const y = (point.y - transform.top) / transform.scale - .5;
  return x >= -.5 && y >= -.5 && x < image.width - .5 && y < image.height - .5 ? { x, y } : null;
}
export function zoomAt(image: Size, viewport: Size, view: ViewState, zoom: number, anchor: Point): ViewState {
  const before = imageTransform(image, viewport, view);
  if (before.scale <= 0) return fittedView;
  const next = { zoom: clamp(zoom, 1, maxZoom), pan: { x: 0, y: 0 } };
  const after = imageTransform(image, viewport, next);
  next.pan = { x: anchor.x - (anchor.x - before.left) / before.scale * after.scale - after.left,
    y: anchor.y - (anchor.y - before.top) / before.scale * after.scale - after.top };
  return boundedView(image, viewport, next);
}

// Browser-decoded JPEG/PNG orientation is retained separately from raw geometry.
// A future raw overlay must pass through this transform before the viewport transform.
export function rawToDecoded(point: Point, raw: Size, orientation: number): Point {
  const x = point.x, y = point.y, w = raw.width - 1, h = raw.height - 1;
  switch (orientation) {
    case 2: return { x: w - x, y };
    case 3: return { x: w - x, y: h - y };
    case 4: return { x, y: h - y };
    case 5: return { x: y, y: x };
    case 6: return { x: h - y, y: x };
    case 7: return { x: h - y, y: w - x };
    case 8: return { x: y, y: w - x };
    default: return { x, y };
  }
}
