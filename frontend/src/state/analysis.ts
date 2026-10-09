import type { AnalysisResult, ApiError, JobState, SequenceInput } from '../types/contracts';
import { parseAnalysisResult, parseJobState } from '../api/responseValidation';

/** Local UI state, separate from the Integration-owned transport contracts. */
export type AnalysisState =
  | { phase: 'unavailable'; reason: string }
  | { phase: 'idle' }
  | { phase: 'validating' | 'submitting'; sequence: SequenceInput }
  | { phase: 'processing' | 'awaiting_result'; sequence: SequenceInput; job: JobState }
  | { phase: 'succeeded'; sequence: SequenceInput; result: AnalysisResult }
  | { phase: 'failed'; error: ApiError };

// Health is the only installed API. Flags alone cannot verify missing job routes.
export const unavailableAnalysis: AnalysisState = {
  phase: 'unavailable', reason: 'Sequence loading and analysis are pending backend integration.',
};

function failed(cause: unknown): AnalysisState {
  return { phase: 'failed', error: { code: 'incompatible_response', message: cause instanceof Error ? cause.message : 'Backend response could not be verified', details: null } };
}

/** No polling/submission is installed here. A future verified service supplies responses. */
export function receiveJob(state: AnalysisState, response: unknown): AnalysisState {
  if (state.phase !== 'submitting' && state.phase !== 'processing') return state;
  try {
    const job = parseJobState(response);
    if (state.phase === 'processing') {
      if (job.job_id !== state.job.job_id || (state.job.status === 'running' && job.status === 'queued')) return state;
    }
    if (job.status === 'failed') return { phase: 'failed', error: job.error ?? { code: 'analysis_failed', message: 'The backend reported a failed analysis without further details.', details: null } };
    return { phase: job.status === 'succeeded' ? 'awaiting_result' : 'processing', sequence: state.sequence, job };
  } catch (cause) { return failed(cause); }
}

export function receiveResult(state: AnalysisState, response: unknown): AnalysisState {
  if (state.phase !== 'awaiting_result') return state;
  try {
    const result = parseAnalysisResult(response);
    if (result.job_id !== state.job.job_id || result.sequence_id !== state.sequence.sequence_id ||
      result.source_type !== state.sequence.source_type || result.profile !== state.sequence.profile) {
      throw new Error('Backend result does not belong to the selected job and sequence');
    }
    if ((result.provenance.input_sha256 !== null && state.sequence.input_sha256 !== null && result.provenance.input_sha256 !== state.sequence.input_sha256) ||
      (result.time_basis === 'second' && state.sequence.frames.some(frame => frame.timestamp_s === null))) {
      throw new Error('Backend result has incompatible source provenance or timestamps');
    }
    return { phase: 'succeeded', sequence: state.sequence, result };
  } catch (cause) { return failed(cause); }
}

export function presentAnalysis(state: AnalysisState) {
  switch (state.phase) {
    case 'unavailable': return { label: 'Integration pending', title: 'Your observations belong here.', description: `${state.reason} No telescope frames or analysis results are loaded.`, progress: null, detectionCount: null, trackCount: null };
    case 'idle': return { label: 'Awaiting sequence', title: 'Choose an observation sequence.', description: 'No analysis has been submitted.', progress: null, detectionCount: null, trackCount: null };
    case 'validating': case 'submitting': return { label: state.phase === 'validating' ? 'Validating sequence' : 'Submitting sequence', title: 'Preparing your observations.', description: 'Results will appear after the backend completes the analysis.', progress: null, detectionCount: null, trackCount: null };
    case 'processing': return { label: state.job.status === 'queued' ? 'Queued' : 'Analyzing', title: state.job.progress_stage || 'Analysis is in progress.', description: 'Waiting for completed backend results.', progress: state.job.progress_fraction, detectionCount: null, trackCount: null };
    case 'awaiting_result': return { label: 'Retrieving results', title: 'Verifying the completed result.', description: 'The job has finished. Scientific output is not available until its response is verified.', progress: null, detectionCount: null, trackCount: null };
    case 'failed': return { label: 'Analysis failed', title: 'Analysis could not be completed.', description: state.error.message, progress: null, detectionCount: null, trackCount: null };
    case 'succeeded': return { label: 'Analysis complete', title: state.result.detections.length === 0 ? 'No candidates found.' : 'Candidate evidence is available.', description: state.result.registration.status === 'failed' ? 'Registration failed. Cross-frame trajectory evidence requires review.' : 'Completed backend results are ready for inspection.', progress: null, detectionCount: state.result.detections.length, trackCount: state.result.tracks.length };
  }
}
