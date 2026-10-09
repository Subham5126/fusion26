import type { AnalysisResult, SequenceInput } from '../types/contracts';
import type { LocalFrame } from './localSequence';
import type { ScientificOverlayModel } from './scientificOverlay';
import { rawToDecoded } from './geometry';

export function buildUploadManifest(frames: LocalFrame[]): SequenceInput {
  if (frames.length !== 5) throw new Error('Select and confirm exactly five telescope frames.');
  if (frames.some(frame => frame.header.orientation !== 1)) throw new Error('Orientation 1 is required for scientific upload.');
  return { schema_version: '0.1.0', sequence_id: `upload-${crypto.randomUUID()}`, source_type: 'user_upload', profile: 'spotgeo',
    frames: frames.map((frame, index) => ({ frame_index: index, image_ref: `frame_${index}`, width_px: frame.header.width,
      height_px: frame.header.height, timestamp_s: null })), dataset_id: null, dataset_version: null, input_sha256: null };
}

export function uploadOverlay(result: AnalysisResult, frame: LocalFrame, index: number, manifest: SequenceInput, diagnostics: unknown): ScientificOverlayModel {
  const empty = (message: string) => ({ detections: [], tracks: [], warnings: [message] });
  if (!diagnostics) return empty('Loading registration diagnostics before projecting track overlays.');
  const data = diagnostics as { sequence?: SequenceInput; registration?: { status: string; transform_direction: string;
    frames: { reference_to_raw: number[][] | null }[] } };
  const registration = data.registration, metadata = data.sequence;
  if (result.sequence_id !== manifest.sequence_id || metadata?.sequence_id !== manifest.sequence_id ||
      result.source_type !== 'user_upload' || result.coordinate_frame !== 'reference_frame_0' || result.registration.status !== 'estimated' ||
      registration?.status !== 'estimated' || registration.transform_direction !== 'raw_to_reference' ||
      !Array.isArray(metadata.frames) || !Array.isArray(registration.frames) || registration.frames.length !== 5 ||
      metadata.frames.length !== 5 || manifest.frames.some((meta, i) => meta.width_px !== metadata.frames[i]?.width_px || meta.height_px !== metadata.frames[i]?.height_px) ||
      manifest.frames[index]?.width_px !== frame.header.width || manifest.frames[index]?.height_px !== frame.header.height)
    return empty('Image, manifest, result or registration provenance mismatch; overlays suppressed.');
  const matrix = registration.frames[index]?.reference_to_raw;
  if (!Array.isArray(matrix) || matrix.length !== 3 || matrix.some(row => !Array.isArray(row) || row.length !== 3 || row.some(v => !Number.isFinite(v))) ||
      matrix[0][0] !== 1 || matrix[0][1] !== 0 || matrix[1][0] !== 0 || matrix[1][1] !== 1 || matrix[2][0] !== 0 || matrix[2][1] !== 0 || matrix[2][2] !== 1)
    return empty('Usable translation inverse unavailable; overlays suppressed.');
  const decoded = (x: number, y: number) => rawToDecoded({ x, y }, frame.header, 1);
  const project = (x: number, y: number) => decoded(x + matrix[0][2], y + matrix[1][2]);
  const owners = new Map(result.tracks.flatMap(track => track.points.filter(point => point.detection_id).map(point => [point.detection_id!, track.track_id] as const)));
  const byId = new Map(result.detections.map(d => [d.detection_id, d]));
  if (result.tracks.some(track => track.points.some(point => point.point_type === 'observed' &&
      (!point.detection_id || point.x_raw_px !== byId.get(point.detection_id)?.x_raw_px || point.y_raw_px !== byId.get(point.detection_id)?.y_raw_px))))
    return empty('Track observations disagree with actual detections; overlays suppressed.');
  const detections = result.detections.filter(d => d.frame_index === index).map(d => {
    const [x0, y0, x1, y1] = d.bbox_raw_px;
    const a = decoded(x0 - .5, y0 - .5), b = decoded(x1 - .5, y1 - .5);
    return { id: d.detection_id, trackId: owners.get(d.detection_id), center: decoded(d.x_raw_px, d.y_raw_px), box: { x: a.x, y: a.y, width: b.x-a.x, height: b.y-a.y } };
  });
  const tracks = result.tracks.map(track => {
    const points = track.points.filter(p => p.point_type === 'observed').sort((a,b) => a.frame_index-b.frame_index);
    const observed = points.filter(p => p.frame_index <= index).map(p => ({ ...project(p.x_reference_px, p.y_reference_px), frame: p.frame_index }));
    const segments = observed.flatMap((p,i) => i && p.frame === observed[i-1].frame+1 ? [[observed[i-1],p]] : []);
    const last = points.at(-1);
    const predictions = last && index >= last.frame_index && track.trajectory?.coordinate_frame === 'reference_frame_0'
      ? track.trajectory.predictions.filter(p => p.point_type === 'extrapolated' && p.frame_index > last.frame_index)
        .sort((a,b) => a.frame_index-b.frame_index).map(p => ({ ...project(p.x_reference_px,p.y_reference_px), frame:p.frame_index })) : [];
    return { id:track.track_id, observed, segments, predictions, forecast: predictions.length && last ? [project(last.x_reference_px,last.y_reference_px),...predictions] : [] };
  });
  return { detections, tracks, warnings: [] };
}
