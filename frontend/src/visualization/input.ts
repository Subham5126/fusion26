import type { AnalysisResult } from '../types/contracts';
import type { Matrix } from './overlay';

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Expected a JSON object.');
  return value as Record<string, unknown>;
}
function array(value: unknown): unknown[] { if (!Array.isArray(value)) throw new Error('Expected a JSON array.'); return value; }
function finite(value: unknown): number { if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error('Coordinates and scores must be finite numbers.'); return value; }
function text(value: unknown): string { if (typeof value !== 'string' || !value) throw new Error('Missing result identifier.'); return value; }
function strings(value: unknown) { array(value).forEach(text); }
function point(value: unknown) {
  const p = object(value);
  if (!Number.isInteger(finite(p.frame_index)) || (p.frame_index as number) < 0) throw new Error('Invalid frame index.');
  finite(p.x_reference_px); finite(p.y_reference_px);
  if (!['observed', 'interpolated', 'extrapolated'].includes(String(p.point_type))) throw new Error('Unknown point type.');
}
// Rendering guard for local files; backend remains the authoritative contract validator.
export function parseResult(value: unknown): AnalysisResult {
  const r = object(value);
  if (r.schema_version !== '0.1.0' || r.status !== 'succeeded') throw new Error('Choose a succeeded AnalysisResult using schema 0.1.0.');
  text(r.sequence_id); text(r.coordinate_frame); text(r.source_type);
  const registration = object(r.registration);
  if (!['identity', 'estimated', 'failed', 'not_required'].includes(String(registration.status))) throw new Error('Invalid registration status.');
  strings(registration.warnings); strings(r.warnings);
  const detectionIds = new Set<string>();
  for (const item of array(r.detections)) {
    const d = object(item); const id = text(d.detection_id);
    if (detectionIds.has(id)) throw new Error('Duplicate detection ID.');
    detectionIds.add(id);
    if (!Number.isInteger(finite(d.frame_index)) || (d.frame_index as number) < 0) throw new Error('Invalid detection frame.');
    const box = array(d.bbox_raw_px).map(finite);
    const x = finite(d.x_raw_px), y = finite(d.y_raw_px), quality = finite(d.quality_score);
    if (box.length !== 4 || box[0] < 0 || box[1] < 0 || box[2] <= box[0] || box[3] <= box[1]
      || x < box[0] || x >= box[2] || y < box[1] || y >= box[3] || quality < 0 || quality > 1) throw new Error('Invalid exclusive-upper bounding box or quality score.');
  }
  const trackIds = new Set<string>();
  for (const item of array(r.tracks)) {
    const t = object(item); const id = text(t.track_id);
    if (trackIds.has(id)) throw new Error('Duplicate track ID.');
    trackIds.add(id); text(t.status); strings(t.warnings); finite(t.observed_count); finite(t.quality_score);
    array(t.points).forEach(point);
    if (t.trajectory !== null) {
      const trajectory = object(t.trajectory); finite(trajectory.speed); text(trajectory.speed_unit);
      if (trajectory.fit_rmse_px !== null) finite(trajectory.fit_rmse_px);
      array(trajectory.predictions).forEach(point);
    }
  }
  return value as AnalysisResult;
}
export function parseRegistration(value: unknown): Map<number, Matrix> {
  const result = object(value);
  if (result.coordinate_frame !== 'reference_frame_0' || result.transform_direction !== 'raw_to_reference') throw new Error('Expected a T13 raw_to_reference registration report.');
  const matrices = new Map<number, Matrix>();
  for (const value of array(result.frames)) {
    const frame = object(value);
    if (frame.status !== 'estimated' && frame.status !== 'identity') continue;
    const index = finite(frame.frame_index);
    const matrix = array(frame.reference_to_raw).map(row => array(row).map(finite));
    if (!Number.isInteger(index) || index < 0 || matrices.has(index) || matrix.length !== 3 || matrix.some(row => row.length !== 3)) throw new Error('Invalid per-frame registration matrix.');
    const [a, b, c] = matrix;
    const determinant = a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0]);
    if (Math.abs(determinant) < 1e-10) throw new Error('Singular registration matrix.');
    matrices.set(index, matrix as Matrix);
  }
  return matrices;
}
