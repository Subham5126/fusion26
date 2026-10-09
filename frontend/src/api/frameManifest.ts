import { parseJobId, ResponseValidationError } from './responseValidation';

// Frontend-owned metadata for the route verified at review/member-integration
// 026a0c8. AnalysisResult and the shared 0.1.0 schema are unchanged.
export interface ManifestFrame {
  frame_index: number;
  timestamp_s: number | null;
  width_px: number;
  height_px: number;
}
export interface JobManifest { job_id: string; frame_count: number; frames: ManifestFrame[] }

function requireValue(condition: boolean, field: string): asserts condition {
  if (!condition) throw new ResponseValidationError(`manifest.${field}`);
}
function record(value: unknown, required: string[], optional: string[] = []): Record<string, unknown> {
  requireValue(typeof value === 'object' && value !== null && !Array.isArray(value), 'object');
  const data = value as Record<string, unknown>;
  requireValue(required.every(key => Object.hasOwn(data, key)) && Object.keys(data).every(key => required.includes(key) || optional.includes(key)), 'fields');
  return data;
}
function dimension(value: unknown): number {
  requireValue(typeof value === 'number' && Number.isSafeInteger(value) && value > 0 && value <= 4_000_000, 'dimensions');
  return value;
}

/** SequenceInput supplies bounded, equal-size, contiguous zero-based frames. */
export function parseJobManifest(value: unknown, expectedJobId: string): JobManifest {
  const jobId = parseJobId(expectedJobId), data = record(value, ['job_id', 'frame_count', 'frames']);
  requireValue(parseJobId(data.job_id) === jobId, 'job_id');
  requireValue(typeof data.frame_count === 'number' && Number.isSafeInteger(data.frame_count) && data.frame_count > 0 && data.frame_count <= 30, 'frame_count');
  requireValue(Array.isArray(data.frames) && data.frames.length === data.frame_count, 'frame_count/frames');
  let lastTimestamp: number | undefined;
  const frames = data.frames.map((value, position) => {
    const entry = record(value, ['frame_index', 'width_px', 'height_px'], ['timestamp_s']);
    requireValue(entry.frame_index === position, 'ordered zero-based frame_index');
    const width = dimension(entry.width_px), height = dimension(entry.height_px);
    requireValue(width * height <= 4_000_000, 'decoded pixel limit');
    const timestamp = entry.timestamp_s ?? null;
    requireValue(timestamp === null || (typeof timestamp === 'number' && Number.isFinite(timestamp)), 'timestamp_s');
    if (timestamp !== null) {
      requireValue(lastTimestamp === undefined || timestamp > lastTimestamp, 'timestamp order');
      lastTimestamp = timestamp;
    }
    return { frame_index: position, width_px: width, height_px: height, timestamp_s: timestamp };
  });
  requireValue(frames.every(frame => frame.width_px === frames[0].width_px && frame.height_px === frames[0].height_px), 'equal P0 dimensions');
  return { job_id: jobId, frame_count: data.frame_count, frames };
}
