import type { ApiError } from '../types/contracts';
import { parseApiError, parseJobId, ResponseValidationError } from './responseValidation';
import { apiUrl } from './baseUrl';

// Job/result routes were inspected at 9e292f9; manifest at 026a0c8
// on review/member-integration. No arbitrary API routes are enabled.
// Binary frames use a separate exchange; they are never parsed as JSON.
type VerifiedReadEndpoint = '/api/health' | `/api/jobs/${string}`;
const jobReadRoute = /^\/api\/jobs\/[A-Za-z0-9][A-Za-z0-9_-]{0,95}(?:\/(?:result|manifest))?$/;

export class ApiRequestError extends Error {
  readonly code: string;
  readonly details: ApiError['details'];
  constructor(readonly status: number, error: ApiError) {
    super(error.message);
    this.name = 'ApiRequestError'; this.code = error.code; this.details = error.details;
  }
}

export async function requestJson(endpoint: VerifiedReadEndpoint, signal?: AbortSignal): Promise<unknown> {
  if (endpoint !== '/api/health' && !jobReadRoute.test(endpoint)) throw new Error('This API route has not been verified in the current checkout');
  return exchangeJson(endpoint, 'GET', 200, signal);
}

/** The published demo route accepts a bodyless POST and returns HTTP 202. */
export type DemoPreset = '1' | '2' | '3' | '4';
export function postDemoJson(signal?: AbortSignal, preset?: DemoPreset): Promise<unknown> {
  if (preset !== undefined && !['1','2','3','4'].includes(preset)) throw new Error('Unknown demo preset');
  return exchangeJson('/api/analyze/demo', 'POST', 202, signal, preset ? `?preset=${preset}` : '');
}

async function exchangeJson(endpoint: string, method: 'GET' | 'POST', expectedStatus: number, signal?: AbortSignal, query = ''): Promise<unknown> {
  signal?.throwIfAborted();
  const response = await fetch(apiUrl(endpoint) + query, { method, signal, headers: { Accept: 'application/json' } });
  signal?.throwIfAborted();
  if (!response.ok) await throwHttpError(response, signal);
  if (response.status !== expectedStatus) throw new ResponseValidationError(`HTTP ${response.status}; expected ${expectedStatus}`);
  try { const body: unknown = await response.json(); signal?.throwIfAborted(); return body; }
  catch (cause) {
    if (signal?.aborted) throw cause;
    throw new ResponseValidationError('invalid JSON');
  }
}

export async function throwHttpError(response: Response, signal?: AbortSignal): Promise<never> {
  let error: ApiError = { code: 'http_error', message: `Backend request failed (HTTP ${response.status})`, details: null };
  try {
    const body: unknown = await response.json();
    if (typeof body === 'object' && body !== null && 'error' in body) error = parseApiError(body.error);
    else if (typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string')
      error = { code: 'http_error', message: body.detail, details: null };
  } catch (cause) {
    if (signal?.aborted) throw cause;
  }
  throw new ApiRequestError(response.status, error);
}

/** Verified PNG route in review/member-integration at 9e292f9; no upload support. */
export async function requestFrameBlob(jobId: string, frameIndex: number, signal?: AbortSignal): Promise<Blob> {
  const id = parseJobId(jobId);
  if (!Number.isInteger(frameIndex) || frameIndex < 0 || frameIndex >= 30) throw new Error('Invalid frame index');
  signal?.throwIfAborted();
  const response = await fetch(apiUrl(`/api/jobs/${id}/frames/${frameIndex}`), { method: 'GET', signal, headers: { Accept: 'image/png' } });
  if (!response.ok) await throwHttpError(response, signal);
  if (response.status !== 200) throw new ResponseValidationError(`HTTP ${response.status}; expected 200`);
  if (response.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase() !== 'image/png') throw new Error('Backend frame must be image/png');
  const declared = response.headers.get('Content-Length');
  if (declared && Number(declared) > 10 * 1024 * 1024) throw new Error('Backend frame exceeds 10 MiB');
  const blob = await response.blob();
  signal?.throwIfAborted();
  if (!blob.size || blob.size > 10 * 1024 * 1024) throw new Error('Backend frame must be nonempty and at most 10 MiB');
  return blob;
}
