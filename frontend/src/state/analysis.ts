import type { AnalysisResult, ApiError, JobState, SequenceInput } from '../types/contracts';
import { parseAnalysisResult, parseDemoSubmission, parseJobState } from '../api/responseValidation';
import type { DemoSubmission } from '../api/responseValidation';

// Demo submission does not return a manifest. Never invent one for the UI.
type AnalysisContext = { sequence: SequenceInput } | { demo: true };

/** Local UI state, separate from the Integration-owned transport contracts. */
export type AnalysisState =
  | { phase: 'unavailable'; reason: string }
  | { phase: 'idle' }
  | { phase: 'validating'; sequence: SequenceInput }
  | ({ phase: 'submitting' } & AnalysisContext)
  | { phase: 'queued'; demo: true; submission: DemoSubmission }
  | ({ phase: 'processing' | 'awaiting_result'; job: JobState } & AnalysisContext)
  | ({ phase: 'succeeded'; result: AnalysisResult; job?: JobState } & AnalysisContext)
  | { phase: 'failed'; error: ApiError; job?: JobState }
  | { phase: 'cancelled'; jobId: string | null };

// Used only by the preserved conceptual landing-page preview.
export const unavailableAnalysis: AnalysisState = {
  phase: 'unavailable', reason: 'Sequence loading and analysis are pending backend integration.',
};

function failed(cause: unknown, job?: JobState): AnalysisState {
  return { phase: 'failed', job, error: { code: 'incompatible_response', message: cause instanceof Error ? cause.message : 'Backend response could not be verified', details: null } };
}

export function receiveDemoSubmission(state: AnalysisState, response: unknown): AnalysisState {
  if (state.phase !== 'submitting' || !('demo' in state)) return state;
  try { return { phase: 'queued', demo: true, submission: parseDemoSubmission(response) }; }
  catch (cause) { return failed(cause); }
}

export function receiveJob(state: AnalysisState, response: unknown): AnalysisState {
  if (state.phase !== 'submitting' && state.phase !== 'processing' && state.phase !== 'queued') return state;
  try {
    const job = parseJobState(response);
    if (state.phase === 'queued' && job.job_id !== state.submission.job_id) throw new Error('Backend job does not match the accepted demo');
    if (state.phase === 'processing') {
      if (job.job_id !== state.job.job_id || (state.job.status === 'running' && job.status === 'queued')) return state;
    }
    if (job.status === 'failed') return { phase: 'failed', job, error: job.error ?? { code: 'analysis_failed', message: 'The backend reported a failed analysis without further details.', details: null } };
    const context: AnalysisContext = 'sequence' in state ? { sequence: state.sequence } : { demo: true };
    return { phase: job.status === 'succeeded' ? 'awaiting_result' : 'processing', ...context, job };
  } catch (cause) { return failed(cause); }
}

export function receiveResult(state: AnalysisState, response: unknown): AnalysisState {
  if (state.phase !== 'awaiting_result') return state;
  try {
    const result = parseAnalysisResult(response);
    if (result.job_id !== state.job.job_id) throw new Error('Backend result does not belong to the selected job');
    if ('sequence' in state && (result.sequence_id !== state.sequence.sequence_id ||
      result.source_type !== state.sequence.source_type || result.profile !== state.sequence.profile)) {
      throw new Error('Backend result does not belong to the selected job and sequence');
    }
    if ('sequence' in state && ((result.provenance.input_sha256 !== null && state.sequence.input_sha256 !== null && result.provenance.input_sha256 !== state.sequence.input_sha256) ||
      (result.time_basis === 'second' && state.sequence.frames.some(frame => frame.timestamp_s === null)))) {
      throw new Error('Backend result has incompatible source provenance or timestamps');
    }
    if ('demo' in state && (result.source_type !== 'synthetic' || result.profile !== 'synthetic_static_stars')) throw new Error('Backend demo result has an incompatible source or profile');
    const context: AnalysisContext = 'sequence' in state ? { sequence: state.sequence } : { demo: true };
    return { phase: 'succeeded', ...context, result, job: state.job };
  } catch (cause) { return failed(cause, state.job); }
}

export function presentAnalysis(state: AnalysisState) {
  switch (state.phase) {
    case 'unavailable': return { label: 'Integration pending', title: 'Your observations belong here.', description: `${state.reason} No telescope frames or analysis results are loaded.`, progress: null, detectionCount: null, trackCount: null };
    case 'idle': return { label: 'Awaiting sequence', title: 'Choose an observation sequence.', description: 'No analysis has been submitted.', progress: null, detectionCount: null, trackCount: null };
    case 'validating': return { label: 'Validating sequence', title: 'Preparing your observations.', description: 'Results will appear after the backend completes the analysis.', progress: null, detectionCount: null, trackCount: null };
    case 'submitting': return { label: 'demo' in state ? 'Submitting demo' : 'Submitting sequence', title: 'Preparing the backend job.', description: 'Waiting for the backend to accept the request.', progress: null, detectionCount: null, trackCount: null };
    case 'queued': return { label: 'Queued', title: 'Synthetic demo accepted.', description: 'Waiting for the backend job status.', progress: null, detectionCount: null, trackCount: null };
    case 'processing': return { label: state.job.status === 'queued' ? 'Queued' : 'Running', title: state.job.progress_stage || 'Analysis is in progress.', description: 'Waiting for completed backend results.', progress: state.job.progress_fraction, detectionCount: null, trackCount: null };
    case 'awaiting_result': return { label: 'Retrieving results', title: 'Verifying the completed result.', description: 'The job has finished. Scientific output is not available until its response is verified.', progress: null, detectionCount: null, trackCount: null };
    case 'failed': return { label: 'Analysis failed', title: 'Analysis could not be completed.', description: state.error.message, progress: null, detectionCount: null, trackCount: null };
    case 'cancelled': return { label: 'Monitoring stopped', title: 'Stopped watching this job.', description: 'The backend may continue processing. Run Synthetic Demo starts a new job.', progress: null, detectionCount: null, trackCount: null };
    case 'succeeded': return { label: 'Analysis complete', title: state.result.detections.length === 0 ? 'No candidates found.' : 'Candidate evidence is available.', description: state.result.registration.status === 'failed' ? 'Registration failed. Cross-frame trajectory evidence requires review.' : 'Completed backend results are ready for inspection.', progress: null, detectionCount: state.result.detections.length, trackCount: state.result.tracks.length };
  }
}
