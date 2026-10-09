import type { AnalysisResult, Detection, Track, TrackPoint } from '../types/contracts';

export type XY = { x: number; y: number };
export type Matrix = [[number, number, number], [number, number, number], [number, number, number]];
// Display metadata, separate from the unchanged AnalysisResult transport contract.
export interface ViewerFrame {
  frameIndex: number;
  imageUrl: string;
  width: number;
  height: number;
  referenceToRaw?: Matrix;
}
const colors = ['#36e6ff', '#b5ff45', '#ff68dd', '#ffad45', '#fff06a'];
const forecastColors = ['#ffad45', '#ff68dd', '#36e6ff', '#b5ff45', '#ff68dd'];
export function trackColors(id: string) {
  let hash = 0;
  for (const c of id) hash = (Math.imul(hash, 31) + c.charCodeAt(0)) >>> 0;
  const index = hash % colors.length;
  return { observed: colors[index], forecast: forecastColors[index] };
}
export function transformPoint(point: XY, matrix: Matrix): XY | null {
  const [a, b, c] = matrix;
  const w = c[0] * point.x + c[1] * point.y + c[2];
  if (!Number.isFinite(w) || Math.abs(w) < 1e-10) return null;
  const x = (a[0] * point.x + a[1] * point.y + a[2]) / w;
  const y = (b[0] * point.x + b[1] * point.y + b[2]) / w;
  return Number.isFinite(x) && Number.isFinite(y) ? { x, y } : null;
}
export function alignmentAvailable(result: AnalysisResult, frame: ViewerFrame) {
  return result.registration.status === 'identity' || result.registration.status === 'not_required'
    || result.coordinate_frame === 'raw' || frame.referenceToRaw !== undefined
    || (frame.frameIndex === 0 && result.coordinate_frame === 'reference_frame_0');
}
export function displayPoint(point: TrackPoint, result: AnalysisResult, frame: ViewerFrame): XY | null {
  if (!alignmentAvailable(result, frame)) return null;
  const xy = { x: point.x_reference_px, y: point.y_reference_px };
  if (!Number.isFinite(xy.x) || !Number.isFinite(xy.y)) return null;
  return frame.referenceToRaw && result.coordinate_frame !== 'raw' ? transformPoint(xy, frame.referenceToRaw) : xy;
}
export function visibleTrack(track: Track, result: AnalysisResult, frame: ViewerFrame) {
  const all = track.points.filter(p => p.point_type === 'observed').sort((a, b) => a.frame_index - b.frame_index);
  const observed = all.filter(p => p.frame_index <= frame.frameIndex).map(point => ({ point, xy: displayPoint(point, result, frame) }));
  const last = all.at(-1);
  // Never reveal later observations or forecasts fitted to them while scrubbing the past.
  const forecast = last && frame.frameIndex >= last.frame_index
    ? (track.trajectory?.predictions ?? []).filter(p => p.point_type === 'extrapolated' && p.frame_index > last.frame_index)
      .sort((a, b) => a.frame_index - b.frame_index).map(point => ({ point, xy: displayPoint(point, result, frame) })) : [];
  return { observed, forecast };
}
export function currentDetections(result: AnalysisResult, frameIndex: number): { detection: Detection; track: Track | undefined }[] {
  const owners = new Map<string, Track>();
  for (const track of result.tracks) for (const point of track.points) {
    if (point.point_type === 'observed' && point.frame_index === frameIndex && point.detection_id) owners.set(point.detection_id, track);
  }
  return result.detections.filter(d => d.frame_index === frameIndex).map(detection => ({ detection, track: owners.get(detection.detection_id) }));
}
export interface Viewport { x: number; y: number; zoom: number }
export function zoomAt(view: Viewport, anchor: XY, nextZoom: number): Viewport {
  const zoom = Math.max(1, Math.min(8, nextZoom));
  const ratio = view.zoom / zoom;
  return { x: anchor.x - (anchor.x - view.x) * ratio, y: anchor.y - (anchor.y - view.y) * ratio, zoom };
}
