import type { AnalysisResult, ApiError, HealthResponse, JobState } from '../types/contracts';

const opaqueId = /^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$/;
const sha256 = /^[a-f0-9]{64}$/;

export class ResponseValidationError extends Error {
  constructor(field: string) {
    super(`Backend returned an incompatible response (${field})`);
    this.name = 'ResponseValidationError';
  }
}

function requireValue(condition: boolean, field: string): asserts condition {
  if (!condition) throw new ResponseValidationError(field);
}

function record(value: unknown, fields: string[], field: string): Record<string, unknown> {
  requireValue(typeof value === 'object' && value !== null && !Array.isArray(value), field);
  const data = value as Record<string, unknown>;
  requireValue(Object.keys(data).length === fields.length && fields.every(key => Object.hasOwn(data, key)), field);
  return data;
}

function text(value: unknown, field: string, pattern?: RegExp) {
  requireValue(typeof value === 'string' && (!pattern || pattern.test(value)), field);
}

function number(value: unknown, field: string, min = -Infinity, max = Infinity, integer = false) {
  requireValue(typeof value === 'number' && Number.isFinite(value) && value >= min && value <= max && (!integer || Number.isInteger(value)), field);
}

function nullableNumber(value: unknown, field: string, min = -Infinity, max = Infinity) {
  if (value !== null) number(value, field, min, max);
}

function choice(value: unknown, values: readonly unknown[], field: string) {
  requireValue(values.includes(value), field);
}

function array(value: unknown, field: string): unknown[] {
  requireValue(Array.isArray(value), field);
  return value;
}

function strings(value: unknown, field: string) {
  array(value, field).forEach(item => text(item, field));
}

function dictionary(value: unknown, field: string, validate: (value: unknown, field: string) => void) {
  requireValue(typeof value === 'object' && value !== null && !Array.isArray(value), field);
  Object.values(value).forEach(item => validate(item, field));
}

function pair(value: unknown, field: string) {
  const values = array(value, field);
  requireValue(values.length === 2, field);
  values.forEach(item => number(item, field));
}

function rawPair(data: Record<string, unknown>, x: string, y: string) {
  nullableNumber(data[x], x); nullableNumber(data[y], y);
  requireValue((data[x] === null) === (data[y] === null), `${x}/${y}`);
}

export function parseApiError(value: unknown): ApiError {
  const data = record(value, ['code', 'message', 'details'], 'error');
  text(data.code, 'error.code'); text(data.message, 'error.message');
  if (data.details !== null) dictionary(data.details, 'error.details', text);
  return value as ApiError;
}

export function parseHealthResponse(value: unknown): HealthResponse {
  const data = record(value, ['status', 'service', 'readiness', 'schema_version', 'capabilities'], 'health');
  choice(data.status, ['ok'], 'health.status'); choice(data.service, ['OrbitTrace'], 'health.service');
  choice(data.readiness, ['bootstrap_only'], 'health.readiness'); choice(data.schema_version, ['0.1.0'], 'schema_version');
  const flags = record(data.capabilities, ['schemas', 'synthetic_generation', 'detection', 'tracking', 'trajectory', 'evaluation', 'analysis_api', 'uploads', 'exports'], 'capabilities');
  Object.values(flags).forEach(flag => requireValue(typeof flag === 'boolean', 'capabilities'));
  return value as HealthResponse;
}

export function parseJobState(value: unknown): JobState {
  const data = record(value, ['job_id', 'status', 'progress_stage', 'warnings', 'error', 'progress_fraction'], 'job');
  text(data.job_id, 'job_id', opaqueId); choice(data.status, ['queued', 'running', 'succeeded', 'failed'], 'job.status');
  text(data.progress_stage, 'progress_stage'); strings(data.warnings, 'warnings');
  nullableNumber(data.progress_fraction, 'progress_fraction', 0, 1);
  if (data.error !== null) parseApiError(data.error);
  return value as JobState;
}

function detection(value: unknown): Record<string, unknown> {
  const data = record(value, ['detection_id', 'frame_index', 'x_raw_px', 'y_raw_px', 'bbox_raw_px', 'kind', 'quality_score', 'detector_name', 'x_reference_px', 'y_reference_px', 'endpoints_raw_px', 'evidence_statistics'], 'detection');
  text(data.detection_id, 'detection_id', opaqueId); number(data.frame_index, 'frame_index', 0, Infinity, true);
  number(data.x_raw_px, 'x_raw_px'); number(data.y_raw_px, 'y_raw_px');
  const box = array(data.bbox_raw_px, 'bbox_raw_px');
  requireValue(box.length === 4, 'bbox_raw_px'); box.forEach(item => number(item, 'bbox_raw_px', 0));
  const [x0, y0, x1, y1] = box as number[];
  requireValue(x0 <= (data.x_raw_px as number) && (data.x_raw_px as number) < x1 && y0 <= (data.y_raw_px as number) && (data.y_raw_px as number) < y1, 'detection centroid');
  choice(data.kind, ['compact', 'streak', 'unknown'], 'kind'); number(data.quality_score, 'quality_score', 0, 1);
  text(data.detector_name, 'detector_name'); rawPair(data, 'x_reference_px', 'y_reference_px');
  if (data.endpoints_raw_px !== null) {
    const endpoints = array(data.endpoints_raw_px, 'endpoints_raw_px');
    requireValue(endpoints.length === 2, 'endpoints_raw_px'); endpoints.forEach(item => pair(item, 'endpoints_raw_px'));
  }
  if (data.evidence_statistics !== null) dictionary(data.evidence_statistics, 'evidence_statistics', nullableNumber);
  return data;
}

function point(value: unknown, timeBasis: unknown): Record<string, unknown> {
  const data = record(value, ['frame_index', 'timestamp_s', 'x_reference_px', 'y_reference_px', 'x_raw_px', 'y_raw_px', 'point_type', 'detection_id', 'out_of_field'], 'track point');
  number(data.frame_index, 'frame_index', 0, Infinity, true); nullableNumber(data.timestamp_s, 'timestamp_s');
  requireValue((data.timestamp_s !== null) === (timeBasis === 'second'), 'point time basis');
  number(data.x_reference_px, 'x_reference_px'); number(data.y_reference_px, 'y_reference_px'); rawPair(data, 'x_raw_px', 'y_raw_px');
  choice(data.point_type, ['observed', 'interpolated', 'extrapolated'], 'point_type');
  if (data.detection_id !== null) text(data.detection_id, 'detection_id', opaqueId);
  requireValue((data.point_type === 'observed') === (data.detection_id !== null), 'observation identity');
  choice(data.out_of_field, [true, false, null], 'out_of_field');
  return data;
}

/** Validates the existing 0.1.0 emitted payload; it does not create or normalize results. */
export function parseAnalysisResult(value: unknown): AnalysisResult {
  const data = record(value, ['schema_version', 'job_id', 'sequence_id', 'source_type', 'profile', 'status', 'time_basis', 'coordinate_frame', 'registration', 'detections', 'tracks', 'metrics', 'runtime_ms', 'warnings', 'provenance'], 'result');
  choice(data.schema_version, ['0.1.0'], 'schema_version'); choice(data.status, ['succeeded'], 'result.status');
  text(data.job_id, 'job_id', opaqueId); text(data.sequence_id, 'sequence_id', opaqueId); text(data.coordinate_frame, 'coordinate_frame', opaqueId);
  choice(data.source_type, ['synthetic', 'real', 'user_upload'], 'source_type');
  choice(data.profile, ['synthetic_static_stars', 'ground_static_star_streaks', 'spotgeo'], 'profile'); choice(data.time_basis, ['frame', 'second'], 'time_basis');
  const registration = record(data.registration, ['status', 'warnings'], 'registration');
  choice(registration.status, ['identity', 'estimated', 'failed', 'not_required'], 'registration.status'); strings(registration.warnings, 'registration.warnings');
  nullableNumber(data.runtime_ms, 'runtime_ms', 0); strings(data.warnings, 'warnings');
  const provenance = record(data.provenance, ['input_sha256', 'config_sha256', 'code_commit', 'dataset_version'], 'provenance');
  for (const key of ['input_sha256', 'config_sha256']) if (provenance[key] !== null) text(provenance[key], key, sha256);
  for (const key of ['code_commit', 'dataset_version']) if (provenance[key] !== null) text(provenance[key], key);
  const detections = array(data.detections, 'detections').map(detection);
  const byId = new Map(detections.map(item => [item.detection_id, item]));
  requireValue(byId.size === detections.length, 'unique detection IDs');
  const trackIds = new Set(); const assigned = new Set();
  for (const value of array(data.tracks, 'tracks')) {
    const track = record(value, ['track_id', 'status', 'candidate_label', 'points', 'observed_count', 'quality_score', 'warnings', 'trajectory'], 'track');
    text(track.track_id, 'track_id', opaqueId); requireValue(!trackIds.has(track.track_id), 'unique track IDs'); trackIds.add(track.track_id);
    choice(track.status, ['tentative', 'confirmed', 'ended'], 'track.status'); choice(track.candidate_label, ['orbital-object candidate; identity unverified'], 'candidate_label');
    number(track.observed_count, 'observed_count', 0, Infinity, true); number(track.quality_score, 'quality_score', 0, 1); strings(track.warnings, 'track.warnings');
    const points = array(track.points, 'points').map(item => point(item, data.time_basis));
    requireValue(points.every((item, index) => index === 0 || (item.frame_index as number) > (points[index - 1].frame_index as number)), 'ordered track points');
    const observed = points.filter(item => item.point_type === 'observed');
    requireValue(observed.length === track.observed_count && (track.status !== 'confirmed' || observed.length >= 3), 'observed support');
    for (const item of observed) {
      requireValue(byId.get(item.detection_id)?.frame_index === item.frame_index && !assigned.has(item.detection_id), 'same-frame unique detection reference');
      assigned.add(item.detection_id);
    }
    if (track.trajectory !== null) {
      const fit = record(track.trajectory, ['model', 'coordinate_frame', 'time_basis', 'vx', 'vy', 'speed', 'speed_unit', 'fit_rmse_px', 'observations_used', 'reference_epoch', 'x_at_epoch_px', 'y_at_epoch_px', 'predictions'], 'trajectory');
      choice(fit.model, ['constant_velocity'], 'trajectory.model'); requireValue(fit.coordinate_frame === data.coordinate_frame && fit.time_basis === data.time_basis, 'trajectory reference');
      requireValue(fit.speed_unit === (data.time_basis === 'frame' ? 'px/frame' : 'px/s'), 'trajectory units');
      for (const key of ['vx', 'vy', 'reference_epoch', 'x_at_epoch_px', 'y_at_epoch_px']) number(fit[key], key);
      number(fit.speed, 'speed', 0); nullableNumber(fit.fit_rmse_px, 'fit_rmse_px', 0); number(fit.observations_used, 'observations_used', 3, observed.length, true);
      array(fit.predictions, 'predictions').forEach(item => requireValue(point(item, data.time_basis).point_type === 'extrapolated', 'prediction type'));
    }
  }
  if (data.metrics !== null) {
    const metrics = record(data.metrics, ['benchmark_id', 'split', 'matching_gate_px', 'tp', 'fp', 'fn', 'precision', 'recall', 'localization_rmse_px', 'null_reasons'], 'metrics');
    text(metrics.benchmark_id, 'benchmark_id', opaqueId); choice(metrics.split, ['development', 'validation', 'test'], 'split');
    number(metrics.matching_gate_px, 'matching_gate_px', 0);
    for (const key of ['tp', 'fp', 'fn']) number(metrics[key], key, 0, Infinity, true);
    for (const key of ['precision', 'recall']) nullableNumber(metrics[key], key, 0, 1);
    nullableNumber(metrics.localization_rmse_px, 'localization_rmse_px', 0); dictionary(metrics.null_reasons, 'null_reasons', text);
  }
  return value as AnalysisResult;
}
