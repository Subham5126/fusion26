import { getJob, getJobResult, runSyntheticDemo, runUpload } from '../api/client';
import { parseJobState, ResponseValidationError } from '../api/responseValidation';
import { ApiRequestError } from '../api/transport';
import { receiveDemoSubmission, receiveJob, receiveResult } from './analysis';
import type { AnalysisState } from './analysis';
import type { ApiError, JobState, SequenceInput } from '../types/contracts';

export const jobPollIntervalMs = 750;

export function waitForJobPoll(milliseconds: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const aborted = () => { clearTimeout(timer); signal.removeEventListener('abort', aborted); reject(signal.reason); };
    if (signal.aborted) { reject(signal.reason); return; }
    const timer = setTimeout(() => { signal.removeEventListener('abort', aborted); resolve(); }, milliseconds);
    signal.addEventListener('abort', aborted, { once: true });
  });
}

export interface AnalysisJobServices {
  submit: (signal: AbortSignal) => Promise<unknown>;
  job: (jobId: string, signal: AbortSignal) => Promise<unknown>;
  result: (jobId: string, signal: AbortSignal) => Promise<unknown>;
  wait: (milliseconds: number, signal: AbortSignal) => Promise<void>;
}

const backendServices: AnalysisJobServices = {
  submit: runSyntheticDemo, job: getJob, result: getJobResult, wait: waitForJobPoll,
};

function errorFrom(cause: unknown): ApiError {
  if (cause instanceof ApiRequestError) return { code: cause.code, message: cause.message, details: cause.details };
  return {
    code: cause instanceof ResponseValidationError ? 'incompatible_response' : 'network_error',
    message: cause instanceof Error ? cause.message : 'The backend request could not be completed.', details: null,
  };
}

/** One request at a time. Replaced runs and unmounted clients cannot publish results. */
export function createAnalysisJobController(publish: (state: AnalysisState) => void, services = backendServices) {
  let active: AbortController | null = null;
  let disposed = false;
  let state: AnalysisState = { phase: 'idle' };
  let jobId: string | null = null;
  const current = (request: AbortController) => !disposed && active === request && !request.signal.aborted;
  const update = (next: AnalysisState) => { state = next; publish(next); };

  async function start(sequence?: SequenceInput, files?: File[]) {
    if (disposed) return;
    active?.abort();
    const request = new AbortController(); active = request; jobId = null;
    update(sequence ? { phase: 'submitting', sequence } : { phase: 'submitting', demo: true });
    let lastJob: JobState | undefined;
    try {
      const submission = sequence ? await runUpload(sequence, files ?? [], request.signal) : await services.submit(request.signal);
      if (!current(request)) return;
      const accepted = receiveDemoSubmission(state, submission); update(accepted);
      if (accepted.phase !== 'queued') return;
      const acceptedId = accepted.submission.job_id; jobId = acceptedId;
      while (current(request)) {
        // Delay after the previous request finishes; never overlap polls.
        await services.wait(jobPollIntervalMs, request.signal);
        if (!current(request)) return;
        const response = await services.job(acceptedId, request.signal);
        if (!current(request)) return;
        const job = parseJobState(response);
        if (job.job_id !== acceptedId) throw new ResponseValidationError('job_id does not match the accepted demo');
        lastJob = job;
        const next = receiveJob(state, job); update(next);
        if (next.phase === 'failed') return;
        if (next.phase === 'awaiting_result') {
          const result = await services.result(acceptedId, request.signal);
          if (current(request)) update(receiveResult(next, result));
          return;
        }
      }
    } catch (cause) {
      if (current(request)) update({ phase: 'failed', error: errorFrom(cause), job: lastJob });
    } finally {
      if (active === request) active = null;
    }
  }

  function cancel() {
    if (disposed || !active) return;
    active.abort(); active = null;
    update({ phase: 'cancelled', jobId });
  }

  function dispose() { disposed = true; active?.abort(); active = null; }
  function reset() { active?.abort(); active = null; jobId = null; if (!disposed) update({ phase: 'idle' }); }
  return { start, cancel, reset, dispose };
}
