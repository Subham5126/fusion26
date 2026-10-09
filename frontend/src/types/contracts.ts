// Contract 0.1.0: integration owns changes; synchronize with backend/app/schemas.
export type SourceType = 'synthetic' | 'real' | 'user_upload';
export type Profile = 'synthetic_static_stars' | 'ground_static_star_streaks' | 'spotgeo';
export type TimeBasis = 'frame' | 'second';
export interface FrameInput {
  frame_index: number; image_ref: string; width_px: number; height_px: number;
  timestamp_s: number | null;
}
export interface SequenceInput {
  schema_version: '0.1.0'; sequence_id: string; source_type: SourceType;
  profile: Profile; frames: FrameInput[]; dataset_id: string | null;
  dataset_version: string | null; input_sha256: string | null;
}
export interface Detection {
  detection_id: string; frame_index: number; x_raw_px: number; y_raw_px: number;
  bbox_raw_px: [number, number, number, number]; kind: 'compact' | 'streak' | 'unknown';
  quality_score: number; detector_name: string;
  x_reference_px: number | null; y_reference_px: number | null;
  endpoints_raw_px: [[number, number], [number, number]] | null;
  evidence_statistics: Record<string, number | null> | null;
}
export interface TrackPoint {
  frame_index: number; timestamp_s: number | null;
  x_reference_px: number; y_reference_px: number;
  x_raw_px: number | null; y_raw_px: number | null;
  point_type: 'observed' | 'interpolated' | 'extrapolated';
  detection_id: string | null; out_of_field: boolean | null;
}
export interface Trajectory {
  model: 'constant_velocity'; coordinate_frame: string; time_basis: TimeBasis;
  vx: number; vy: number; speed: number; speed_unit: 'px/frame' | 'px/s';
  fit_rmse_px: number | null; observations_used: number;
  reference_epoch: number; x_at_epoch_px: number; y_at_epoch_px: number;
  predictions: TrackPoint[];
}
export interface Track {
  track_id: string; status: 'tentative' | 'confirmed' | 'ended';
  candidate_label: 'orbital-object candidate; identity unverified';
  points: TrackPoint[]; observed_count: number; quality_score: number;
  warnings: string[]; trajectory: Trajectory | null;
}
export interface BenchmarkMetrics {
  benchmark_id: string; split: 'development' | 'validation' | 'test';
  matching_gate_px: number; tp: number; fp: number; fn: number;
  precision: number | null; recall: number | null; localization_rmse_px: number | null;
  null_reasons: Record<string, string>;
}
export interface AnalysisResult {
  schema_version: '0.1.0'; job_id: string; sequence_id: string;
  source_type: SourceType; profile: Profile; status: 'succeeded';
  time_basis: TimeBasis; coordinate_frame: string;
  registration: {status: 'identity' | 'estimated' | 'failed' | 'not_required'; warnings: string[]};
  detections: Detection[]; tracks: Track[]; metrics: BenchmarkMetrics | null;
  runtime_ms: number | null; warnings: string[];
  provenance: {input_sha256: string | null; config_sha256: string | null;
    code_commit: string | null; dataset_version: string | null};
}
export interface Capabilities {
  schemas: boolean; synthetic_generation: boolean; detection: boolean;
  tracking: boolean; trajectory: boolean; evaluation: boolean;
  analysis_api: boolean; uploads: boolean; exports: boolean;
}
export interface HealthResponse {
  status: 'ok'; service: 'OrbitTrace'; readiness: 'bootstrap_only';
  schema_version: '0.1.0'; capabilities: Capabilities;
}
export interface ApiError {code: string; message: string; details: Record<string, string> | null}
export interface JobState {
  job_id: string; status: 'queued' | 'running' | 'succeeded' | 'failed';
  progress_stage: string; warnings: string[]; error: ApiError | null;
  progress_fraction: number | null;
}
