import { getJobManifest } from '../api/client';
import { parseJobManifest } from '../api/frameManifest';
import type { JobManifest } from '../api/frameManifest';
import { parseJobId } from '../api/responseValidation';
import { ApiRequestError } from '../api/transport';

export type ManifestState = { jobId: string; phase: 'loading' | 'ready' | 'failed'; manifest?: JobManifest;
  error?: string; errorCode?: string; errorStatus?: number };

/** A retried, replaced or disposed request cannot publish metadata for an old job. */
export function createManifestController(jobId: string, publish: (state: ManifestState) => void,
  fetchManifest = getJobManifest) {
  parseJobId(jobId);
  let active: AbortController | undefined, revision = 0, disposed = false;
  async function load() {
    if (disposed) return;
    active?.abort(); active = new AbortController();
    const request = active, version = ++revision;
    const current = () => !disposed && version === revision && !request.signal.aborted;
    publish({ jobId, phase: 'loading' });
    try {
      const manifest = parseJobManifest(await fetchManifest(jobId, request.signal), jobId);
      if (current()) publish({ jobId, phase: 'ready', manifest });
    } catch (error) {
      if (current()) publish({ jobId, phase: 'failed', error: error instanceof Error ? error.message : 'Manifest request failed',
        ...(error instanceof ApiRequestError ? { errorCode: error.code, errorStatus: error.status } : {}) });
    }
  }
  return { load, dispose: () => { disposed = true; revision++; active?.abort(); } };
}
