import test from 'node:test';
import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import fixture from '../../tests/contracts/fixtures/track-result.json';
import { getJobFrame } from '../src/api/client';
import { ApiRequestError } from '../src/api/transport';
import { parseAnalysisResult } from '../src/api/responseValidation';
import { createDemoFrameController, supportsDemoFrames } from '../src/viewer/demoFrames';
import type { JobManifest } from '../src/api/frameManifest';
import type { DemoFrame, DemoFrameServices, DemoFrameState } from '../src/viewer/demoFrames';
import { scientificOverlay } from '../src/viewer/scientificOverlay';
import { imageTransform, pixelToViewport, rawToDecoded } from '../src/viewer/geometry';
import { ScientificOverlay } from '../src/components/workbench/ScientificOverlay';
import { LocalWorkbench } from '../src/components/workbench/LocalWorkbench';
import { DemoWorkbench } from '../src/components/workbench/DemoWorkbench';
import { WorkbenchShell } from '../src/components/workbench/WorkbenchShell';

// Authored headers and contract fixture exercise boundaries; none are live assets.
function png(width = 64, height = 48) {
  const bytes = new Uint8Array(33); bytes.set([137, 80, 78, 71, 13, 10, 26, 10]);
  const view = new DataView(bytes.buffer); view.setUint32(8, 13); bytes.set([73, 72, 68, 82], 12); view.setUint32(16, width); view.setUint32(20, height);
  return new Blob([bytes], { type: 'image/png' });
}
function result() {
  const input = structuredClone(fixture); input.coordinate_frame = 'raw_pixels'; input.tracks[0].trajectory.coordinate_frame = 'raw_pixels';
  return parseAnalysisResult(input);
}
function manifest(jobId = 'example-job'): JobManifest {
  return { job_id: jobId, frame_count: 5, frames: [0, 1, 2, 3, 4].map(frame_index => ({ frame_index, width_px: 64, height_px: 48, timestamp_s: null })) };
}
function frame(index = 0, overrides: Partial<DemoFrame> = {}): DemoFrame {
  return { id: `example-job/${index}`, source: 'analyzed_demo', job_id: 'example-job', frame_index: index, url: 'blob:test',
    manifest: manifest(), label: 'Test demo', width_px: 64, height_px: 48, timestamp_s: null, header: { width: 64, height: 48, orientation: 1, format: 'image/png' }, ...overrides };
}
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { resolve, promise }; }
function harness(overrides: Partial<DemoFrameServices> = {}, jobId = 'example-job') {
  const states: DemoFrameState[] = [], revoked: string[] = [], fetched: number[] = [], created: string[] = [];
  const resources: DemoFrameServices = { fetch: async (id, index) => { assert.equal(id, jobId); fetched.push(index); return png(); },
    createUrl: () => { const url = `blob:${jobId}/${created.length}`; created.push(url); return url; },
    revokeUrl: url => revoked.push(url), decode: async () => ({ width: 64, height: 48 }), ...overrides };
  const controller = createDemoFrameController(manifest(jobId), state => states.push(state), resources);
  return { controller, states, revoked, fetched, created, latest: () => states.at(-1)! };
}
async function usingFetch(stub: typeof fetch, check: () => Promise<void>) { const saved = globalThis.fetch; globalThis.fetch = stub; try { await check(); } finally { globalThis.fetch = saved; } }

test('binary PNG transport uses the verified job, frame, Accept header and abort signal', async () => {
  const signal = new AbortController().signal;
  await usingFetch(async (url, options) => { assert.equal(url, '/api/jobs/example-job/frames/4'); assert.equal(options?.method, 'GET');
    assert.equal((options?.headers as Record<string, string>).Accept, 'image/png'); assert.strictEqual(options?.signal, signal);
    return new Response(png(), { headers: { 'Content-Type': 'image/png; charset=binary' } });
  }, async () => { assert.equal((await getJobFrame('example-job', 4, signal)).type.split(';')[0], 'image/png'); });
});
test('PNG transport rejects wrong MIME, empty bytes, oversized content and unexpected status', async () => {
  for (const response of [new Response('{}', { headers: { 'Content-Type': 'application/json' } }), new Response('', { headers: { 'Content-Type': 'image/png' } }),
    new Response(png(), { headers: { 'Content-Type': 'image/png', 'Content-Length': String(11 * 1024 * 1024) } }),
    new Response(png(), { status: 202, headers: { 'Content-Type': 'image/png' } })]) {
    await usingFetch(async () => response, async () => { await assert.rejects(getJobFrame('example-job', 0)); });
  }
});
test('PNG transport preserves real 404 errors and propagates network failure', async () => {
  await usingFetch(async () => new Response(JSON.stringify({ error: { code: 'not_found', message: 'Frames evicted', details: null } }), { status: 404 }), async () => {
    await assert.rejects(getJobFrame('example-job', 0), error => error instanceof ApiRequestError && error.status === 404 && error.code === 'not_found' && error.message === 'Frames evicted');
  });
  await usingFetch(async () => { throw new TypeError('Offline'); }, async () => { await assert.rejects(getJobFrame('example-job', 0), /Offline/); });
});
test('unsafe job IDs, invalid frame indexes and an aborted caller never send a frame request', async () => {
  let requests = 0; const abort = new AbortController(); abort.abort();
  await usingFetch(async () => { requests++; return new Response(png()); }, async () => {
    for (const index of [-1, .5, 30, NaN]) await assert.rejects(getJobFrame('example-job', index));
    await assert.rejects(getJobFrame('../job', 0)); await assert.rejects(getJobFrame('example-job', 0, abort.signal), { name: 'AbortError' }); assert.equal(requests, 0);
  });
});
test('decoded demo frames use manifest-confirmed order and geometry, without manufactured timestamps', async () => {
  const h = harness(); await h.controller.select(4);
  assert.deepEqual(h.latest().frame?.manifest.frames.map(frame => frame.frame_index), [0, 1, 2, 3, 4]); assert.equal(h.latest().phase, 'ready');
  assert.equal(h.latest().frame?.frame_index, 4); assert.equal(h.latest().frame?.timestamp_s, null); assert.equal(h.latest().frame?.source, 'analyzed_demo'); h.controller.dispose();
});
test('three-frame LRU cache reuses URLs, evicts old frames and revokes every owned URL once', async () => {
  const h = harness(); for (const index of [0, 1, 2, 0, 3, 4]) await h.controller.select(index);
  assert.deepEqual(h.fetched, [0, 1, 2, 3, 4]); assert.equal(h.revoked.length, 2); h.controller.dispose(); h.controller.dispose();
  assert.deepEqual([...h.revoked].sort(), [...h.created].sort()); assert.equal(new Set(h.revoked).size, h.revoked.length);
});
test('bad PNG header, incorrect dimensions and decoder failures never reach a ready frame', async () => {
  for (const overrides of [{ fetch: async () => new Blob(['corrupt']) }, { fetch: async () => png(640, 480) },
    { decode: async () => ({ width: 48, height: 64 }) }, { decode: async () => { throw new Error('Corrupt PNG decoder failure'); } }]) {
    const h = harness(overrides); await h.controller.select(0); assert.equal(h.latest().phase, 'failed'); assert.equal(h.latest().frame, undefined);
    h.controller.dispose(); assert.deepEqual(h.revoked, h.created);
  }
});
test('frame retry fetches new data and clears a previous network error', async () => {
  let count = 0; const h = harness({ fetch: async () => { if (!count++) throw new TypeError('Connection lost'); return png(); } });
  await h.controller.select(0); assert.match(h.latest().error!, /Connection lost/); await h.controller.select(0, true);
  assert.equal(h.latest().phase, 'ready'); assert.equal(h.latest().error, undefined); assert.equal(count, 2); h.controller.dispose();
});
test('expired frame errors retain backend code and status for recovery guidance', async () => {
  const h = harness({ fetch: async () => { throw new ApiRequestError(404, { code: 'not_found', message: 'Job frames evicted', details: null }); } });
  await h.controller.select(0); assert.equal(h.latest().errorStatus, 404); assert.equal(h.latest().errorCode, 'not_found'); assert.equal(h.latest().frame, undefined); h.controller.dispose();
});
test('frame indexes absent from the manifest do not trigger guessed endpoint scans', async () => {
  const h = harness(); await h.controller.select(5); assert.equal(h.latest().phase, 'failed'); assert.deepEqual(h.fetched, []); h.controller.dispose();
});
test('rapid seeking aborts and ignores stale network responses even when a transport ignores abort', async () => {
  const pending = deferred<Blob>(); let oldSignal: AbortSignal | undefined;
  const h = harness({ fetch: async (_job, index, signal) => { if (index === 0) { oldSignal = signal; return pending.promise; } return png(); } });
  const old = h.controller.select(0); await h.controller.select(4); const count = h.states.length;
  pending.resolve(png()); await old; assert.equal(oldSignal?.aborted, true); assert.equal(h.states.length, count); assert.equal(h.latest().frame?.frame_index, 4); h.controller.dispose();
});
test('job disposal during decoding releases the late URL and cannot publish an old job frame', async () => {
  const pending = deferred<{ width: number; height: number }>(), entered = deferred<void>(); let signal: AbortSignal | undefined;
  const old = harness({ decode: async (_url, abort) => { signal = abort; entered.resolve(); return pending.promise; } }, 'old-job');
  const loading = old.controller.select(0); await entered.promise; old.controller.dispose();
  const next = harness({}, 'new-job'); await next.controller.select(0); pending.resolve({ width: 64, height: 48 }); await loading;
  assert.equal(signal?.aborted, true); assert.deepEqual(old.states.map(state => state.phase), ['loading']); assert.deepEqual(old.revoked, old.created);
  assert.equal(next.latest().frame?.job_id, 'new-job'); next.controller.dispose();
});
test('overlays match the selected frame, integer centroids and exclusive upper box edges', () => {
  const model = scientificOverlay(result(), frame(1)); assert.equal(model.detections.length, 1); assert.equal(model.detections[0].id, 'd1');
  assert.deepEqual(model.detections[0].center, { x: 14, y: 15 }); assert.deepEqual(model.detections[0].box, { x: 12.5, y: 13.5, width: 3, height: 3 });
  assert.deepEqual(model.tracks[0].observed.map(point => point.frame), [0, 1]); assert.equal(model.tracks[0].predictions.length, 0);
});
test('forecasts use only returned future points and are never counted as observations', () => {
  const model = scientificOverlay(result(), frame(2)); assert.equal(model.tracks[0].observed.length, 3); assert.equal(model.tracks[0].predictions.length, 1);
  assert.deepEqual(model.tracks[0].predictions[0], { x: 22, y: 21, frame: 3 }); assert.equal(model.tracks[0].forecast.length, 2);
  const html = renderToStaticMarkup(createElement(ScientificOverlay, { model, scale: 4, selected: 'fixture-track-1', select: () => {}, visibility: { detections: true, tracks: true, predictions: true } }));
  assert.match(html, /stroke-dasharray="1.25 1"/); assert.match(html, /class="predicted-point"[^>]*fill="none"/); assert.match(html, /data-observed-frame/); assert.match(html, /not observed/);
});
test('missing observations are not interpolated into a solid observed track', () => {
  const payload = result(); payload.tracks[0].points.splice(1, 1); payload.tracks[0].observed_count = 2;
  const model = scientificOverlay(payload, frame(2)); assert.equal(model.tracks[0].observed.length, 2); assert.equal(model.tracks[0].segments.length, 0);
});
test('empty frames keep honest empty detection sets while preserving actual history', () => {
  const model = scientificOverlay(result(), frame(4)); assert.equal(model.detections.length, 0); assert.equal(model.tracks[0].observed.length, 3);
  const payload = result(); payload.detections = []; payload.tracks = []; assert.deepEqual(scientificOverlay(payload, frame()).detections, []);
});
test('wrong job, local source, raw geometry, dimensions and failed registration suppress overlays', () => {
  for (const changed of [frame(0, { job_id: 'other-job' }), frame(0, { source: 'local_preview' as DemoFrame['source'] }), frame(0, { width_px: 32 })]) {
    const model = scientificOverlay(result(), changed); assert.equal(model.detections.length, 0); assert.equal(model.tracks.length, 0); assert.equal(model.warnings.length, 1);
  }
  const payload = result(); payload.registration.status = 'failed'; assert.equal(scientificOverlay(payload, frame()).tracks.length, 0);
  payload.registration.status = 'identity'; payload.detections[0].bbox_raw_px[2] = 100; assert.equal(scientificOverlay(payload, frame()).detections.length, 0);
});
test('mismatched observation coordinates cannot draw a plausible but incorrect track', () => {
  const payload = result(); payload.tracks[0].points[0].x_raw_px = 40;
  const model = scientificOverlay(payload, frame(2)); assert.equal(model.tracks[0].observed.length, 0); assert.match(model.warnings[0], /do not match/);
});
test('raster center and box geometry stay aligned through fit, zoom, pan, orientation and viewport sizes', () => {
  for (const width of [240, 390, 768, 1200]) for (const zoom of [1, 1.5, 4]) {
    const transform = imageTransform({ width: 64, height: 48 }, { width, height: 350 }, { zoom, pan: { x: 20, y: -15 } });
    const model = scientificOverlay(result(), frame()); const box = model.detections[0].box, center = pixelToViewport(model.detections[0].center, transform);
    const left = transform.left + (box.x + .5) * transform.scale;
    assert.ok(center.x > left && center.x < left + box.width * transform.scale);
    assert.equal(left, transform.left + 9 * transform.scale);
  }
  const oriented = frame(0, { width_px: 48, height_px: 64, header: { width: 64, height: 48, orientation: 6, format: 'image/png' } });
  const model = scientificOverlay(result(), oriented); assert.deepEqual(model.detections[0].center, rawToDecoded({ x: 10, y: 12 }, { width: 64, height: 48 }, 6));
  assert.deepEqual(model.detections[0].box, { x: 33.5, y: 8.5, width: 3, height: 3 });
});
test('selection, visibility and non-color forecast distinctions appear in the SVG', () => {
  const model = scientificOverlay(result(), frame(2));
  const render = (tracks: boolean, predictions: boolean) => renderToStaticMarkup(createElement(ScientificOverlay, { model, scale: 1, selected: 'fixture-track-1', select: () => {}, visibility: { detections: false, tracks, predictions } }));
  assert.match(render(true, true), /is-selected/); assert.match(render(true, true), /role="button"/); assert.match(render(true, true), /aria-pressed="true"/);
  assert.doesNotMatch(render(false, false), /data-observed-frame|data-predicted-frame|data-detection-id/);
  assert.doesNotMatch(render(true, false), /predicted-point/); assert.match(render(false, true), /predicted-point/);
});
test('local and analyzed sources stay separate and arbitrary analysis remains disabled', () => {
  const local = renderToStaticMarkup(createElement(LocalWorkbench)); const demo = renderToStaticMarkup(createElement(DemoWorkbench, { result: result() }));
  assert.match(local, /Local Image Preview/); assert.match(local, /Analyze local images/); assert.match(local, /disabled/);
  assert.doesNotMatch(local, /data-job-id|Scientific image overlays|scientific-detection/);
  assert.match(demo, /data-source="analyzed_demo"/); assert.match(demo, /Local Image Preview has independent images and no synthetic overlays/);
  const unsupported = result(); unsupported.source_type = 'real'; assert.equal(supportsDemoFrames(unsupported), false);
  assert.match(renderToStaticMarkup(createElement(DemoWorkbench, { result: unsupported })), /No images or overlays are substituted/);
});

test('observation workspace precedes explicitly synthetic controls and contains no synthetic result', () => {
  const html = renderToStaticMarkup(createElement(WorkbenchShell));
  assert.ok(html.indexOf('id="observations"') < html.indexOf('id="synthetic-analysis"'));
  assert.match(html, /data-source="local_preview"/);
  assert.match(html, /data-source="synthetic"/);
  assert.match(html, /Simulated source/);
  assert.doesNotMatch(html, /data-job-id|scientific-detection|data-observed-frame/);
  assert.match(html, /Not performed/);
});
