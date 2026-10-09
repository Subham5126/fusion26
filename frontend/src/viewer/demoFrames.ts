import { getJobFrame } from '../api/client';
import { parseJobId } from '../api/responseValidation';
import { ApiRequestError } from '../api/transport';
import type { AnalysisResult } from '../types/contracts';
import { browserResources, readImageHeader } from './localSequence';
import type { ViewerFrame } from './localSequence';
import type { Size } from './geometry';

// Demo-specific source contract: backend/app/api/analyze.py at
// 9e292f94b00d6eecf24ea06b5c33ff2649d97c71 creates indexes 0–4, 64 × 48.
// This is NOT an API manifest. No frame timestamps or input hashes are invented.
export const verifiedDemoLayout = { width: 64, height: 48, indexes: [0, 1, 2, 3, 4] as readonly number[] } as const;
export const demoFrameCacheLimit = 3;
export function supportsDemoFrames(result: AnalysisResult) {
  return result.status === 'succeeded' && result.source_type === 'synthetic' && result.profile === 'synthetic_static_stars';
}
export interface DemoFrame extends ViewerFrame { source: 'analyzed_demo'; job_id: string; frame_index: number }
export type DemoFrameState = { jobId: string; index: number; phase: 'loading' | 'ready' | 'failed'; frame?: DemoFrame; error?: string; errorCode?: string; errorStatus?: number };
export interface DemoFrameServices {
  fetch: (jobId: string, index: number, signal: AbortSignal) => Promise<Blob>;
  createUrl: (blob: Blob) => string; revokeUrl: (url: string) => void;
  decode: (url: string, signal: AbortSignal) => Promise<Size>;
}
const services: DemoFrameServices = { fetch: getJobFrame, createUrl: blob => URL.createObjectURL(blob),
  revokeUrl: browserResources.revokeUrl, decode: browserResources.decode };

/** One active frame request per job; cache owns only validated, decoded PNG URLs. */
export function createDemoFrameController(jobId: string, publish: (state: DemoFrameState) => void, resources = services) {
  parseJobId(jobId);
  const cache = new Map<number, DemoFrame>();
  let active: AbortController | undefined, revision = 0, disposed = false;
  async function select(index: number, force = false) {
    if (disposed) return;
    active?.abort(); active = new AbortController();
    const request = active, version = ++revision;
    let pendingUrl: string | undefined;
    const current = () => !disposed && version === revision && !request.signal.aborted;
    try {
      if (!verifiedDemoLayout.indexes.includes(index)) throw new Error('Frame is outside the verified five-frame demo range');
      if (force && cache.has(index)) { resources.revokeUrl(cache.get(index)!.url); cache.delete(index); }
      const cached = cache.get(index);
      if (cached) { cache.delete(index); cache.set(index, cached); publish({ jobId, index, phase: 'ready', frame: cached }); return; }
      publish({ jobId, index, phase: 'loading' });
      const blob = await resources.fetch(jobId, index, request.signal);
      request.signal.throwIfAborted();
      const header = readImageHeader(new Uint8Array(await blob.arrayBuffer()));
      request.signal.throwIfAborted();
      if (header.format !== 'image/png' || header.orientation !== 1 || header.width !== verifiedDemoLayout.width || header.height !== verifiedDemoLayout.height)
        throw new Error('Frame geometry does not match the verified demo source; overlays are suppressed');
      pendingUrl = resources.createUrl(blob);
      const decoded = await resources.decode(pendingUrl, request.signal);
      request.signal.throwIfAborted();
      if (decoded.width !== header.width || decoded.height !== header.height) throw new Error('Decoded PNG dimensions do not match its metadata');
      if (!current()) return;
      const frame: DemoFrame = { id: `${jobId}/${index}`, source: 'analyzed_demo', job_id: jobId, frame_index: index,
        label: `Analyzed demo · frame ${index + 1} (index ${index})`, url: pendingUrl, header,
        width_px: decoded.width, height_px: decoded.height, timestamp_s: null };
      cache.set(index, frame); pendingUrl = undefined;
      while (cache.size > demoFrameCacheLimit) {
        const oldest = cache.keys().next().value!; resources.revokeUrl(cache.get(oldest)!.url); cache.delete(oldest);
      }
      publish({ jobId, index, phase: 'ready', frame });
    } catch (error) {
      if (current()) publish({ jobId, index, phase: 'failed', error: error instanceof Error ? error.message : 'Frame request failed',
        ...(error instanceof ApiRequestError ? { errorCode: error.code, errorStatus: error.status } : {}) });
    } finally { if (pendingUrl) resources.revokeUrl(pendingUrl); }
  }
  return { select, dispose: () => { disposed = true; revision++; active?.abort(); cache.forEach(frame => resources.revokeUrl(frame.url)); cache.clear(); } };
}
