import test from 'node:test';
import assert from 'node:assert/strict';
import fixture from '../../tests/contracts/fixtures/track-result.json';
import { getJobManifest } from '../src/api/client';
import { parseJobManifest } from '../src/api/frameManifest';
import type { JobManifest } from '../src/api/frameManifest';
import { ApiRequestError } from '../src/api/transport';
import { parseAnalysisResult, ResponseValidationError } from '../src/api/responseValidation';
import { createManifestController } from '../src/viewer/frameManifest';
import type { ManifestState } from '../src/viewer/frameManifest';
import { createDemoFrameController } from '../src/viewer/demoFrames';
import type { DemoFrameServices, DemoFrameState } from '../src/viewer/demoFrames';
import { scientificOverlay } from '../src/viewer/scientificOverlay';
import { imageTransform, pixelToViewport } from '../src/viewer/geometry';

// Authored boundary data, not a measured result or a substitute for the live demo.
function manifest(jobId = 'example-job', count = 7): JobManifest {
  return { job_id: jobId, frame_count: count, frames: Array.from({ length: count }, (_, frame_index) => ({
    frame_index, timestamp_s: frame_index / 7, width_px: 80, height_px: 60,
  })) };
}
function png(width = 80, height = 60) {
  const bytes = new Uint8Array(33); bytes.set([137, 80, 78, 71, 13, 10, 26, 10]);
  const view = new DataView(bytes.buffer); view.setUint32(8, 13); bytes.set([73, 72, 68, 82], 12);
  view.setUint32(16, width); view.setUint32(20, height);
  return new Blob([bytes], { type: 'image/png' });
}
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { resolve, promise }; }
async function usingFetch(stub: typeof fetch, check: () => Promise<void>) {
  const saved = globalThis.fetch; globalThis.fetch = stub; try { await check(); } finally { globalThis.fetch = saved; }
}
function frames(input = manifest(), overrides: Partial<DemoFrameServices> = {}) {
  const states: DemoFrameState[] = [], fetched: number[] = [], created: string[] = [], revoked: string[] = [];
  const resources: DemoFrameServices = { fetch: async (job, index) => { assert.equal(job, input.job_id); fetched.push(index); return png(); },
    createUrl: () => { const url = `blob:manifest-${created.length}`; created.push(url); return url; },
    revokeUrl: url => revoked.push(url), decode: async () => ({ width: 80, height: 60 }), ...overrides };
  return { controller: createDemoFrameController(input, state => states.push(state), resources),
    states, fetched, created, revoked, latest: () => states.at(-1)! };
}

test('manifest GET uses a relative verified URL, HTTP 200, JSON Accept and caller cancellation', async () => {
  const signal = new AbortController().signal, body = manifest();
  await usingFetch(async (url, options) => {
    assert.equal(url, '/api/jobs/example-job/manifest'); assert.equal(options?.method, 'GET');
    assert.deepEqual(options?.headers, { Accept: 'application/json' }); assert.strictEqual(options?.signal, signal);
    return Response.json(body);
  }, async () => { assert.deepEqual(await getJobManifest('example-job', signal), body); });
});
test('manifest order and count are independent of detections and the former five-frame layout', () => {
  const parsed = parseJobManifest(manifest(), 'example-job');
  assert.equal(parsed.frame_count, 7); assert.deepEqual(parsed.frames.map(frame => frame.frame_index), [0, 1, 2, 3, 4, 5, 6]);
  assert.equal(parsed.frames[6].width_px, 80); assert.equal(parsed.frames[6].height_px, 60);
});
test('missing and nullable acquisition timestamps remain unknown while real precision is preserved', () => {
  const input = manifest(), first = 0.123456789012345;
  input.frames[0].timestamp_s = first; input.frames[1].timestamp_s = null;
  const body: unknown = { ...input, frames: input.frames.map((frame, index) => index === 2 ? {
    frame_index: frame.frame_index, width_px: frame.width_px, height_px: frame.height_px,
  } : frame) };
  const parsed = parseJobManifest(body, 'example-job');
  assert.strictEqual(parsed.frames[0].timestamp_s, first); assert.equal(parsed.frames[1].timestamp_s, null);
  assert.equal(parsed.frames[2].timestamp_s, null);
});
test('wrong job, unknown fields and malformed manifest envelopes are rejected', () => {
  for (const input of [null, [], {}, { ...manifest(), job_id: 'other-job' }, { ...manifest(), job_id: '../job' },
    { ...manifest(), truth: [] }, { ...manifest(), frames: {} }]) {
    assert.throws(() => parseJobManifest(input, 'example-job'), ResponseValidationError);
  }
});
test('manifest frame counts are bounded integers matching the returned entries', () => {
  for (const count of [0, -1, 6, 8, 31, 7.5, NaN, Infinity, '7'])
    assert.throws(() => parseJobManifest({ ...manifest(), frame_count: count }, 'example-job'), ResponseValidationError);
});
test('duplicate, skipped, reversed, noninteger and negative manifest indexes cannot create a guessed timeline', () => {
  for (const index of [-1, .5, 7, 0, '1']) {
    const input = manifest(); (input.frames[1] as unknown as Record<string, unknown>).frame_index = index;
    assert.throws(() => parseJobManifest(input, 'example-job'), ResponseValidationError);
  }
  const reversed = manifest(); reversed.frames.reverse();
  assert.throws(() => parseJobManifest(reversed, 'example-job'), ResponseValidationError);
});
test('invalid, oversized and unequal P0 dimensions are rejected before fetching any PNG', () => {
  for (const width of [0, -1, .5, null, '80', Infinity, 4_000_001]) {
    const input = manifest(); (input.frames[0] as unknown as Record<string, unknown>).width_px = width;
    assert.throws(() => parseJobManifest(input, 'example-job'), ResponseValidationError);
  }
  const oversized = manifest(); oversized.frames.forEach(frame => { frame.width_px = 4000; frame.height_px = 4000; });
  assert.throws(() => parseJobManifest(oversized, 'example-job'), ResponseValidationError);
  const unequal = manifest(); unequal.frames[1].height_px = 61;
  assert.throws(() => createDemoFrameController(unequal, () => {}), ResponseValidationError);
});
test('nonfinite, nonnumeric or backwards known timestamps are rejected', () => {
  for (const timestamp of [NaN, Infinity, '1', false, -.1]) {
    const input = manifest(); (input.frames[1] as unknown as Record<string, unknown>).timestamp_s = timestamp;
    assert.throws(() => parseJobManifest(input, 'example-job'), ResponseValidationError);
  }
});
test('malformed JSON and unexpected successful HTTP statuses cannot become a manifest', async () => {
  for (const response of [new Response('{invalid'), Response.json(manifest(), { status: 201 }), Response.json({ job_id: 'wrong-job' })])
    await usingFetch(async () => response, async () => { await assert.rejects(getJobManifest('example-job'), ResponseValidationError); });
});
test('expired manifest jobs retain the real FastAPI detail and HTTP 404', async () => {
  await usingFetch(async () => Response.json({ detail: 'Job not found or evicted' }, { status: 404 }), async () => {
    await assert.rejects(getJobManifest('example-job'), error => error instanceof ApiRequestError &&
      error.status === 404 && error.code === 'http_error' && error.message === 'Job not found or evicted');
  });
});
test('the verified app-wide manifest 404 envelope retains not_found and its actual message', async () => {
  await usingFetch(async () => Response.json({ error: { code: 'not_found', message: 'Route unavailable in bootstrap', details: null } }, { status: 404 }), async () => {
    await assert.rejects(getJobManifest('example-job'), error => error instanceof ApiRequestError &&
      error.status === 404 && error.code === 'not_found' && error.message === 'Route unavailable in bootstrap');
  });
});
test('manifest network failures cannot provide fallback metadata', async () => {
  await usingFetch(async () => { throw new TypeError('Backend disconnected'); }, async () => {
    await assert.rejects(getJobManifest('example-job'), /Backend disconnected/);
  });
});
test('unsafe manifest job IDs and pre-aborted callers make no network request', async () => {
  let requests = 0; const abort = new AbortController(); abort.abort();
  await usingFetch(async () => { requests++; return Response.json(manifest()); }, async () => {
    await assert.rejects(getJobManifest('../job')); await assert.rejects(getJobManifest('example-job', abort.signal), { name: 'AbortError' });
    assert.equal(requests, 0);
  });
});
test('abort during an ignored network cancellation still rejects the received manifest', async () => {
  const pending = deferred<Response>(), entered = deferred<void>(), abort = new AbortController();
  await usingFetch(async () => { entered.resolve(); return pending.promise; }, async () => {
    const request = getJobManifest('example-job', abort.signal); await entered.promise; abort.abort(); pending.resolve(Response.json(manifest()));
    await assert.rejects(request, { name: 'AbortError' });
  });
});
test('retried manifest requests abort and suppress stale earlier responses', async () => {
  const pending = deferred<JobManifest>(), states: ManifestState[] = []; let count = 0, oldSignal: AbortSignal | undefined;
  const controller = createManifestController('example-job', state => states.push(state), async (_job, signal) => {
    if (!count++) { oldSignal = signal; return pending.promise; } return manifest();
  });
  const old = controller.load(); await controller.load(); const published = states.length;
  pending.resolve(manifest('example-job', 3)); await old;
  assert.equal(oldSignal?.aborted, true); assert.equal(states.length, published); assert.equal(states.at(-1)?.manifest?.frame_count, 7);
  controller.dispose();
});
test('switching jobs disposes pending metadata so it cannot appear in the new viewer', async () => {
  const pending = deferred<JobManifest>(), oldStates: ManifestState[] = [], newStates: ManifestState[] = []; let signal: AbortSignal | undefined;
  const old = createManifestController('old-job', state => oldStates.push(state), async (_job, abort) => { signal = abort; return pending.promise; });
  const request = old.load(); old.dispose();
  const next = createManifestController('new-job', state => newStates.push(state), async () => manifest('new-job'));
  await next.load(); pending.resolve(manifest('old-job')); await request;
  assert.equal(signal?.aborted, true); assert.deepEqual(oldStates.map(state => state.phase), ['loading']);
  assert.equal(newStates.at(-1)?.manifest?.job_id, 'new-job'); next.dispose();
});
test('manifest controller preserves expired-job errors and clears them on a successful retry', async () => {
  const states: ManifestState[] = []; let count = 0;
  const controller = createManifestController('example-job', state => states.push(state), async () => {
    if (!count++) throw new ApiRequestError(404, { code: 'http_error', message: 'Job not found or evicted', details: null });
    return manifest();
  });
  await controller.load(); assert.equal(states.at(-1)?.phase, 'failed'); assert.equal(states.at(-1)?.errorStatus, 404);
  await controller.load(); assert.equal(states.at(-1)?.phase, 'ready'); assert.equal(states.at(-1)?.error, undefined); controller.dispose();
});
test('manifest controller network failures and job mismatch expose no frame metadata', async () => {
  for (const fetchManifest of [async () => { throw new TypeError('Offline'); }, async () => manifest('other-job')]) {
    const states: ManifestState[] = [], controller = createManifestController('example-job', state => states.push(state), fetchManifest);
    await controller.load(); assert.equal(states.at(-1)?.phase, 'failed'); assert.equal(states.at(-1)?.manifest, undefined); controller.dispose();
  }
});
test('ordered manifest PNG retrieval includes frames without detections and preserves timestamps', async () => {
  const input = manifest(), h = frames(input);
  for (const entry of input.frames) {
    await h.controller.select(entry.frame_index); assert.equal(h.latest().phase, 'ready');
    assert.equal(h.latest().frame?.timestamp_s, entry.timestamp_s); assert.equal(h.latest().frame?.width_px, entry.width_px);
  }
  assert.deepEqual(h.fetched, input.frames.map(frame => frame.frame_index));
  const payload = structuredClone(fixture); payload.coordinate_frame = 'raw_pixels'; payload.tracks[0].trajectory.coordinate_frame = 'raw_pixels';
  const overlay = scientificOverlay(parseAnalysisResult(payload), h.latest().frame!);
  assert.equal(overlay.detections.length, 0); assert.equal(overlay.tracks[0].observed.length, 3);
  h.controller.dispose();
});
test('manifest entries outside the former layout retain a three-frame LRU and exact cleanup', async () => {
  const h = frames(); for (const index of [6, 5, 4, 6, 3]) await h.controller.select(index);
  assert.deepEqual(h.fetched, [6, 5, 4, 3]); assert.equal(h.revoked.length, 1);
  h.controller.dispose(); h.controller.dispose(); assert.deepEqual([...h.revoked].sort(), [...h.created].sort());
  assert.equal(new Set(h.revoked).size, h.revoked.length);
});
test('PNG header versus manifest and actual decoder versus manifest mismatches never display images or overlays', async () => {
  for (const override of [{ fetch: async () => png(64, 48) }, { decode: async () => ({ width: 81, height: 60 }) }]) {
    const h = frames(manifest(), override); await h.controller.select(6);
    assert.equal(h.latest().phase, 'failed'); assert.match(h.latest().error!, /match the backend manifest/);
    assert.equal(h.latest().frame, undefined); h.controller.dispose(); assert.deepEqual(h.revoked, h.created);
  }
});
test('unlisted frame indexes do not fetch images even when detections might refer to them', async () => {
  const h = frames(); for (const index of [-1, 7, .5, NaN]) await h.controller.select(index);
  assert.deepEqual(h.fetched, []); assert.equal(h.latest().phase, 'failed'); h.controller.dispose();
});
test('overlay provenance and dimensions must match the exact manifest job and frame', async () => {
  const h = frames(); await h.controller.select(0); const frame = h.latest().frame!;
  const payload = structuredClone(fixture); payload.coordinate_frame = 'raw_pixels'; payload.tracks[0].trajectory.coordinate_frame = 'raw_pixels';
  const result = parseAnalysisResult(payload);
  assert.equal(scientificOverlay(result, frame).detections.length, 1);
  for (const changed of [{ ...frame, manifest: manifest('other-job') }, { ...frame, manifest: { ...manifest(), frames: [] } },
    { ...frame, width_px: 81 }]) assert.equal(scientificOverlay(result, changed).detections.length, 0);
  result.detections[0].frame_index = 7; assert.equal(scientificOverlay(result, frame).tracks.length, 0); h.controller.dispose();
});
test('manifest overlay centers and exclusive box edges retain alignment under DPR, letterboxing, zoom and pan', async () => {
  const h = frames(); await h.controller.select(0);
  const payload = structuredClone(fixture); payload.coordinate_frame = 'raw_pixels'; payload.tracks[0].trajectory.coordinate_frame = 'raw_pixels';
  const detection = scientificOverlay(parseAnalysisResult(payload), h.latest().frame!).detections[0];
  for (const width of [390, 1200]) for (const zoom of [1, 1.5, 4]) for (const dpr of [1, 2, 3]) {
    const image = { width: 80, height: 60 }, view = { zoom, pan: { x: 20, y: -15 } };
    const css = imageTransform(image, { width, height: 350 }, view);
    const physical = imageTransform(image, { width: width * dpr, height: 350 * dpr }, { zoom, pan: { x: 20 * dpr, y: -15 * dpr } });
    const cssCenter = pixelToViewport(detection.center, css), physicalCenter = pixelToViewport(detection.center, physical);
    assert.ok(Math.abs(physicalCenter.x / dpr - cssCenter.x) < 1e-9);
    assert.ok(Math.abs(physicalCenter.y / dpr - cssCenter.y) < 1e-9);
    const expectedLeft = css.left + payload.detections[0].bbox_raw_px[0] * css.scale;
    assert.ok(Math.abs((physical.left + (detection.box.x + .5) * physical.scale) / dpr - expectedLeft) < 1e-9);
  }
  h.controller.dispose();
});
