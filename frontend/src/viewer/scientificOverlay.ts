import type { AnalysisResult, TrackPoint } from '../types/contracts';
import type { DemoFrame } from './demoFrames';
import { supportsDemoFrames } from './demoFrames';
import { rawToDecoded } from './geometry';
import type { Point } from './geometry';

export interface OverlayDetection { id: string; center: Point; box: { x: number; y: number; width: number; height: number }; trackId?: string }
export interface OverlayTrack { id: string; observed: (Point & { frame: number })[]; segments: Point[][];
  predictions: (Point & { frame: number })[]; forecast: Point[] }
export interface ScientificOverlayModel { detections: OverlayDetection[]; tracks: OverlayTrack[]; warnings: string[] }

/** Only the verified synthetic static-camera source can establish raw/reference identity. */
export function scientificOverlay(result: AnalysisResult, frame: DemoFrame): ScientificOverlayModel {
  const empty = (warning: string): ScientificOverlayModel => ({ detections: [], tracks: [], warnings: [warning] });
  if (!supportsDemoFrames(result) || frame.source !== 'analyzed_demo' || result.job_id !== frame.job_id || frame.id !== `${result.job_id}/${frame.frame_index}`)
    return empty('Image and analysis provenance do not match; overlays are suppressed.');
  const { header, manifest } = frame, swapped = header.orientation >= 5;
  const metadata = manifest.frames.find(entry => entry.frame_index === frame.frame_index);
  if (manifest.job_id !== result.job_id || !metadata || header.width !== metadata.width_px || header.height !== metadata.height_px ||
    frame.width_px !== (swapped ? header.height : header.width) || frame.height_px !== (swapped ? header.width : header.height))
    return empty('Image dimensions or frame index do not match the backend manifest; overlays are suppressed.');
  if (result.coordinate_frame !== 'raw_pixels' || !['identity', 'not_required'].includes(result.registration.status))
    return empty('A verified raw/reference transform is unavailable; overlays are suppressed.');
  const transform = (point: Point) => rawToDecoded(point, header, header.orientation);
  const allDetections = new Map(result.detections.map(detection => [detection.detection_id, detection]));
  const owners = new Map(result.tracks.flatMap(track => track.points.filter(point => point.point_type === 'observed' && point.detection_id)
    .map(point => [point.detection_id!, track.track_id] as const)));
  const matching = result.detections.filter(detection => detection.frame_index === frame.frame_index);
  for (const detection of result.detections) {
    const source = manifest.frames.find(entry => entry.frame_index === detection.frame_index);
    const [x0, y0, x1, y1] = detection.bbox_raw_px;
    if (!source || x0 < 0 || y0 < 0 || x1 > source.width_px || y1 > source.height_px ||
      detection.x_raw_px < -.5 || detection.x_raw_px >= source.width_px - .5 || detection.y_raw_px < -.5 || detection.y_raw_px >= source.height_px - .5)
      return empty('Detection geometry is outside the manifest source; overlays are suppressed.');
  }
  const detections = matching.map(detection => {
    const [x0, y0, x1, y1] = detection.bbox_raw_px;
    const corners = [{ x: x0 - .5, y: y0 - .5 }, { x: x1 - .5, y: y0 - .5 }, { x: x0 - .5, y: y1 - .5 }, { x: x1 - .5, y: y1 - .5 }].map(transform);
    const xs = corners.map(point => point.x), ys = corners.map(point => point.y);
    return { id: detection.detection_id, trackId: owners.get(detection.detection_id), center: transform({ x: detection.x_raw_px, y: detection.y_raw_px }),
      box: { x: Math.min(...xs), y: Math.min(...ys), width: Math.max(...xs) - Math.min(...xs), height: Math.max(...ys) - Math.min(...ys) } };
  });
  const warnings: string[] = [];
  const position = (point: TrackPoint) => transform({ x: point.x_raw_px ?? point.x_reference_px, y: point.y_raw_px ?? point.y_reference_px });
  const tracks = result.tracks.map(track => {
    const observedAll = track.points.filter(point => point.point_type === 'observed').sort((a, b) => a.frame_index - b.frame_index);
    const safe = observedAll.every(point => {
      const detection = point.detection_id ? allDetections.get(point.detection_id) : undefined;
      return detection && detection.frame_index === point.frame_index && point.x_raw_px === detection.x_raw_px && point.y_raw_px === detection.y_raw_px;
    });
    if (!safe) { warnings.push(`Track ${track.track_id}: observation coordinates do not match detections; track overlay suppressed.`); return { id: track.track_id, observed: [], segments: [], predictions: [], forecast: [] }; }
    const observed = observedAll.filter(point => point.frame_index <= frame.frame_index).map(point => ({ ...position(point), frame: point.frame_index }));
    const segments = observed.flatMap((point, index) => index && point.frame === observed[index - 1].frame + 1 ? [[observed[index - 1], point]] : []);
    const last = observedAll.at(-1);
    const trajectory = track.trajectory;
    const predictions = last && frame.frame_index >= last.frame_index && trajectory?.coordinate_frame === 'raw_pixels'
      ? trajectory.predictions.filter(point => point.point_type === 'extrapolated' && point.frame_index > last.frame_index)
        .sort((a, b) => a.frame_index - b.frame_index).map(point => ({ ...position(point), frame: point.frame_index })) : [];
    return { id: track.track_id, observed, segments, predictions, forecast: predictions.length && last ? [position(last), ...predictions] : [] };
  });
  return { detections, tracks, warnings };
}
