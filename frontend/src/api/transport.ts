import type { ApiError } from '../types/contracts';
import { parseApiError } from './responseValidation';

// Extend this allowlist only after the corresponding backend route is verified.
type VerifiedReadEndpoint = '/api/health';

export class ApiRequestError extends Error {
  readonly code: string;
  readonly details: ApiError['details'];
  constructor(readonly status: number, error: ApiError) {
    super(error.message);
    this.name = 'ApiRequestError'; this.code = error.code; this.details = error.details;
  }
}

export async function requestJson(endpoint: VerifiedReadEndpoint, signal?: AbortSignal): Promise<unknown> {
  if (endpoint !== '/api/health') throw new Error('This API route has not been verified in the current checkout');
  const response = await fetch(endpoint, { signal, headers: { Accept: 'application/json' } });
  if (!response.ok) {
    let error: ApiError = { code: 'http_error', message: `Health request failed (HTTP ${response.status})`, details: null };
    try {
      const body: unknown = await response.json();
      if (typeof body === 'object' && body !== null && 'error' in body) error = parseApiError(body.error);
    } catch (cause) {
      if (signal?.aborted) throw cause;
    }
    throw new ApiRequestError(response.status, error);
  }
  try { return await response.json(); }
  catch (cause) {
    if (signal?.aborted) throw cause;
    throw new Error('Backend returned invalid JSON');
  }
}
