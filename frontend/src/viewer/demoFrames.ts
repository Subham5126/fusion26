import { getJobFrame } from '../api/client';
import { parseJobId } from '../api/responseValidation';
import { parseJobManifest } from '../api/frameManifest';
import type { JobManifest } from '../api/frameManifest';
import { ApiRequestError } from '../api/transport';
import type { AnalysisResult } from '../types/contracts';
import { browserResources, readImageHeader } from './localSequence';
import type { ViewerFrame } from './localSequence';
import type { Size } from './geometry';

export const demoFrameCacheLimit = 3;
export function supportsDemoFrames(result: AnalysisResult) {
  return result.status === 'succeeded' && result.source_type === 'synthetic' && result.profile === 'synthetic_static_stars';
}
export interface DemoFrame extends ViewerFrame { source: 'analyzed_demo'; job_id: string; frame_index: number; manifest: JobManifest }
export type DemoFrameState = { jobId: string; index: number; phase: 'loading' | 'ready' | 'failed'; frame?: DemoFrame; error?: string; errorCode?: string; errorStatus?: number };
export interface DemoFrameServices {
  fetch: (jobId: string, index: number, signal: AbortSignal) => Promise<Blob>;
  createUrl: (blob: Blob) => string; revokeUrl: (url: string) => void;
  decode: (url: string, signal: AbortSignal) => Promise<Size>;
}
const services: DemoFrameServices = { fetch: getJobFrame, createUrl: blob => URL.createObjectURL(blob),
  revokeUrl: browserResources.revokeUrl, decode: browserResources.decode };

/** One active frame request per job; cache owns only validated, decoded PNG URLs. */
export function createDemoFrameController(input: JobManifest, publish: (state: DemoFrameState) => void, resources = services) {
  const jobId = parseJobId(input.job_id), manifest = parseJobManifest(input, jobId);
  const entries = new Map(manifest.frames.map(frame => [frame.frame_index, frame]));
  const cache = new Map<number, DemoFrame>();
  let active: AbortController | undefined, revision = 0, disposed = false;
  async function select(index: number, force = false) {
    if (disposed) return;
    active?.abort(); active = new AbortController();
    const request = active, version = ++revision;
    let pendingUrl: string | undefined;
    const current = () => !disposed && version === revision && !request.signal.aborted;
    try {
      const metadata = entries.get(index);
      if (!metadata) throw new Error('Frame index is not listed in the backend manifest');
      if (force && cache.has(index)) { resources.revokeUrl(cache.get(index)!.url); cache.delete(index); }
      const cached = cache.get(index);
      if (cached) { cache.delete(index); cache.set(index, cached); publish({ jobId, index, phase: 'ready', frame: cached }); return; }
      publish({ jobId, index, phase: 'loading' });
      const blob = await resources.fetch(jobId, index, request.signal);
      request.signal.throwIfAborted();
      const header = readImageHeader(new Uint8Array(await blob.arrayBuffer()));
      request.signal.throwIfAborted();
      if (header.format !== 'image/png' || header.orientation !== 1 || header.width !== metadata.width_px || header.height !== metadata.height_px)
        throw new Error('PNG dimensions do not match the backend manifest; image and overlays are suppressed');
      pendingUrl = resources.createUrl(blob);
      const decoded = await resources.decode(pendingUrl, request.signal);
      request.signal.throwIfAborted();
      if (decoded.width !== metadata.width_px || decoded.height !== metadata.height_px) throw new Error('Decoded PNG dimensions do not match the backend manifest; image and overlays are suppressed');
      if (!current()) return;
      const frame: DemoFrame = { id: `${jobId}/${index}`, source: 'analyzed_demo', job_id: jobId, frame_index: index, manifest,
        label: `Analyzed demo · frame ${index + 1} (index ${index})`, url: pendingUrl, header,
        width_px: decoded.width, height_px: decoded.height, timestamp_s: metadata.timestamp_s };
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
