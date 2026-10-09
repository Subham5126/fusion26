import test from 'node:test';
import assert from 'node:assert/strict';
import sequenceFixture from '../../tests/contracts/fixtures/sequence.json';
import emptyFixture from '../../tests/contracts/fixtures/empty-result.json';
import trackFixture from '../../tests/contracts/fixtures/track-result.json';
import { parseAnalysisResult, parseHealthResponse, parseJobState } from '../src/api/responseValidation';
import { ApiRequestError, requestJson } from '../src/api/transport';
import { getHealth } from '../src/api/client';
import { presentAnalysis, receiveJob, receiveResult, unavailableAnalysis } from '../src/state/analysis';
import type { AnalysisState } from '../src/state/analysis';
import type { JobState, SequenceInput } from '../src/types/contracts';
import { pointerVariables } from '../src/motion/pointerGeometry';
import { attachAmbientVisibility, attachPointerSurface } from '../src/motion/surfaceEffects';

// Contract fixtures are authored examples used only by this Node test bundle.
const sequence = sequenceFixture as SequenceInput;
const job = (overrides: Partial<JobState> = {}): JobState => ({ job_id: 'example-job', status: 'running', progress_stage: 'detecting', progress_fraction: null, warnings: [], error: null, ...overrides });
const submitting = (): AnalysisState => ({ phase: 'submitting', sequence });
const completedJob = () => receiveJob(submitting(), job({ status: 'succeeded' }));

test('unavailable and pending analysis never masquerade as zero-detection success', () => {
  assert.equal(presentAnalysis(unavailableAnalysis).detectionCount, null);
  const running = receiveJob(submitting(), job());
  assert.equal(presentAnalysis(running).progress, null);
  assert.equal(presentAnalysis(running).detectionCount, null);
  assert.equal(completedJob().phase, 'awaiting_result');
  assert.equal(presentAnalysis(completedJob()).detectionCount, null);
  assert.strictEqual(receiveResult(submitting(), emptyFixture).phase, 'submitting');
});

test('zero detections are reported only after a matching completed backend result', () => {
  const state = receiveResult(completedJob(), emptyFixture);
  assert.equal(state.phase, 'succeeded');
  assert.equal(presentAnalysis(state).title, 'No candidates found.');
  assert.equal(presentAnalysis(state).detectionCount, 0);
  assert.equal(presentAnalysis(state).trackCount, 0);
});

test('a failed job preserves the backend error and cannot fall back to a fixture', () => {
  const error = { code: 'registration_failed', message: 'No supported alignment', details: { stage: 'registration' } };
  const state = receiveJob(submitting(), job({ status: 'failed', error }));
  assert.equal(state.phase, 'failed');
  assert.equal(presentAnalysis(state).description, error.message);
  assert.equal(presentAnalysis(state).detectionCount, null);
  assert.strictEqual(receiveResult(state, emptyFixture), state);
});

test('late responses from another job and backwards queued updates are ignored', () => {
  const current = receiveJob(submitting(), job());
  assert.strictEqual(receiveJob(current, job({ job_id: 'old-job', status: 'succeeded' })), current);
  assert.strictEqual(receiveJob(current, job({ status: 'queued' })), current);
});

test('mismatched sequence, source, and input provenance cannot enter succeeded state', () => {
  assert.equal(receiveResult(completedJob(), { ...emptyFixture, sequence_id: 'wrong-sequence' }).phase, 'failed');
  assert.equal(receiveResult(completedJob(), { ...emptyFixture, source_type: 'real' }).phase, 'failed');
  const state = { ...completedJob(), sequence: { ...sequence, input_sha256: 'a'.repeat(64) } } as AnalysisState;
  assert.equal(receiveResult(state, { ...emptyFixture, provenance: { ...emptyFixture.provenance, input_sha256: 'b'.repeat(64) } }).phase, 'failed');
});

test('valid source labels, null timestamps, coordinates and provenance are preserved without mutation', () => {
  const payload = structuredClone(trackFixture);
  const snapshot = JSON.stringify(payload);
  assert.strictEqual(parseAnalysisResult(payload), payload);
  assert.equal(JSON.stringify(payload), snapshot);
  const state = receiveResult(completedJob(), payload);
  assert.equal(state.phase, 'succeeded');
  if (state.phase === 'succeeded') assert.strictEqual(state.result, payload);
});

test('unknown contract versions and truth-bearing extra fields are rejected', () => {
  assert.throws(() => parseAnalysisResult({ ...emptyFixture, schema_version: '0.2.0' }));
  assert.throws(() => parseAnalysisResult({ ...emptyFixture, ground_truth: [] }));
});

test('nonfinite numbers and unsupported physical units are rejected', () => {
  const bad = structuredClone(trackFixture);
  bad.detections[0].x_raw_px = NaN;
  assert.throws(() => parseAnalysisResult(bad));
  const units = structuredClone(trackFixture);
  units.tracks[0].trajectory.speed_unit = 'km/s';
  assert.throws(() => parseAnalysisResult(units));
  assert.throws(() => parseJobState(job({ progress_fraction: Infinity })));
});

test('prediction points cannot acquire detection IDs or count as observed support', () => {
  const predicted = structuredClone(trackFixture);
  predicted.tracks[0].trajectory.predictions[0].detection_id = 'd0';
  assert.throws(() => parseAnalysisResult(predicted));
  const support = structuredClone(trackFixture);
  support.tracks[0].observed_count = 4;
  assert.throws(() => parseAnalysisResult(support));
});

test('an observed point must reference its own frame and a detection cannot support multiple tracks', () => {
  const wrong = structuredClone(trackFixture);
  wrong.tracks[0].points[0].detection_id = 'd1';
  assert.throws(() => parseAnalysisResult(wrong));
  const duplicate = structuredClone(trackFixture);
  duplicate.tracks.push({ ...duplicate.tracks[0], track_id: 'another-track' });
  assert.throws(() => parseAnalysisResult(duplicate));
});

test('raw boxes use exclusive upper limits and incomplete coordinate pairs are rejected', () => {
  const box = structuredClone(trackFixture);
  box.detections[0].x_raw_px = box.detections[0].bbox_raw_px[2];
  assert.throws(() => parseAnalysisResult(box));
  const pair = structuredClone(trackFixture);
  pair.detections[0].x_reference_px = null;
  assert.throws(() => parseAnalysisResult(pair));
});

test('seconds are not fabricated from unknown acquisition timestamps', () => {
  const result = { ...emptyFixture, time_basis: 'second' };
  assert.equal(receiveResult(completedJob(), result).phase, 'failed');
});

test('transport preserves structured HTTP failure, including status and safe details', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({ error: { code: 'not_found', message: 'Route unavailable in bootstrap', details: { route: 'health' } } }), { status: 404 });
  try {
    await assert.rejects(requestJson('/api/health'), error => error instanceof ApiRequestError && error.status === 404 && error.code === 'not_found' && error.details?.route === 'health');
  } finally { globalThis.fetch = original; }
});

test('malformed JSON and incompatible health responses fail without invented connectivity', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => new Response('<html>error</html>', { status: 200 });
    await assert.rejects(getHealth(), /invalid JSON/);
    globalThis.fetch = async () => new Response(JSON.stringify({ status: 'ok' }), { status: 200 });
    await assert.rejects(getHealth(), /incompatible/);
    assert.throws(() => parseHealthResponse({ ...emptyFixture, status: 'ok' }));
  } finally { globalThis.fetch = original; }
});

test('aborted requests and unverified endpoints never resolve as success', async () => {
  const original = globalThis.fetch;
  const controller = new AbortController(); controller.abort();
  globalThis.fetch = async (_url, options) => { if (options?.signal?.aborted) throw new DOMException('Aborted', 'AbortError'); return new Response('{}'); };
  try {
    await assert.rejects(requestJson('/api/health', controller.signal), { name: 'AbortError' });
    await assert.rejects(requestJson('/api/analyze/upload' as '/api/health'), /not been verified/);
  } finally { globalThis.fetch = original; }
});

test('decorative motion remains bounded for edges, outside pointers and degenerate surfaces', () => {
  const bounds = { left: 10, top: 10, width: 200, height: 100 };
  assert.deepEqual(pointerVariables(110, 60, bounds, 'card'), { '--pointer-x': '100.00px', '--pointer-y': '50.00px', '--tilt-x': '0.00deg', '--tilt-y': '0.00deg' });
  const far = pointerVariables(10000, -10000, bounds, 'card');
  assert.equal(far?.['--tilt-x'], '3.00deg'); assert.equal(far?.['--tilt-y'], '3.00deg');
  assert.equal(pointerVariables(10000, 10000, bounds, 'hero')?.['--parallax-x'], '8.00px');
  assert.equal(pointerVariables(10000, 10000, bounds, 'button')?.['--magnet-x'], '3.00px');
  assert.equal(pointerVariables(1, 1, { ...bounds, width: 0 }, 'card'), null);
  assert.equal(pointerVariables(NaN, 1, bounds, 'card'), null);
});

function effectHarness() {
  const saved = { window: globalThis.window, document: globalThis.document };
  const preference = Object.assign(new EventTarget(), { matches: true });
  const environment = Object.assign(new EventTarget(), { hidden: false });
  const pending = new Map<number, FrameRequestCallback>(); let next = 0;
  const style = new Map<string, string>(); let writes = 0; let measurements = 0;
  const surface = Object.assign(new EventTarget(), {
    dataset: {} as Record<string, string>,
    style: { setProperty: (key: string, value: string) => { style.set(key, value); writes++; }, removeProperty: (key: string) => style.delete(key) },
    removeAttribute: (name: string) => { if (name === 'data-pointer-active') delete surface.dataset.pointerActive; if (name === 'data-ambient-running') delete surface.dataset.ambientRunning; },
    getBoundingClientRect: () => { measurements++; return { left: 0, top: 0, width: 200, height: 100 }; },
  });
  globalThis.window = Object.assign(new EventTarget(), { matchMedia: () => preference, scrollX: 0, scrollY: 0,
    requestAnimationFrame: (callback: FrameRequestCallback) => { pending.set(++next, callback); return next; }, cancelAnimationFrame: (id: number) => pending.delete(id) }) as unknown as Window & typeof globalThis;
  globalThis.document = environment as unknown as Document;
  const pointer = (pointerType = 'mouse') => surface.dispatchEvent(Object.assign(new Event('pointermove'), { pointerType, pageX: 170, pageY: 40 }));
  return { surface, preference, environment, style, pending, pointer, counts: () => ({ writes, measurements }), flush: () => { const callbacks = [...pending.values()]; pending.clear(); callbacks.forEach(callback => callback(0)); }, restore: () => { globalThis.window = saved.window; globalThis.document = saved.document; } };
}

test('100 pointer events coalesce into one frame; leaving and cleanup cancel subsequent writes', () => {
  const harness = effectHarness();
  const cleanup = attachPointerSurface(harness.surface as unknown as HTMLElement, 'card');
  try {
    for (let index = 0; index < 100; index++) harness.pointer();
    assert.equal(harness.pending.size, 1);
    harness.flush(); assert.equal(harness.counts().writes, 4); assert.equal(harness.counts().measurements, 1);
    harness.pointer(); harness.surface.dispatchEvent(new Event('pointerleave'));
    assert.equal(harness.pending.size, 0); assert.equal(harness.style.size, 0);
    cleanup(); harness.pointer(); assert.equal(harness.pending.size, 0);
  } finally { cleanup(); harness.restore(); }
});

test('touch, reduced-motion/coarse preference and hidden pages cannot keep cursor effects running', () => {
  const harness = effectHarness();
  const cleanup = attachPointerSurface(harness.surface as unknown as HTMLElement, 'card');
  try {
    harness.pointer('touch'); assert.equal(harness.pending.size, 0);
    harness.pointer(); harness.flush(); assert.equal(harness.surface.dataset.pointerActive, 'true');
    harness.preference.matches = false; harness.preference.dispatchEvent(new Event('change'));
    assert.equal(harness.style.size, 0); harness.pointer(); assert.equal(harness.pending.size, 0);
    harness.preference.matches = true; harness.pointer(); harness.environment.hidden = true;
    harness.environment.dispatchEvent(new Event('visibilitychange')); assert.equal(harness.pending.size, 0);
    harness.pointer(); assert.equal(harness.pending.size, 0);
  } finally { cleanup(); harness.restore(); }
});

test('ambient visibility follows reduced-motion and page visibility; cleanup removes its listeners', () => {
  const harness = effectHarness(); harness.preference.matches = false;
  const cleanup = attachAmbientVisibility(harness.surface as unknown as HTMLElement);
  try {
    assert.equal(harness.surface.dataset.ambientRunning, 'true');
    harness.preference.matches = true; harness.preference.dispatchEvent(new Event('change'));
    assert.equal(harness.surface.dataset.ambientRunning, 'false');
    harness.preference.matches = false; harness.environment.hidden = true; harness.environment.dispatchEvent(new Event('visibilitychange'));
    assert.equal(harness.surface.dataset.ambientRunning, 'false');
    harness.environment.hidden = false; harness.environment.dispatchEvent(new Event('visibilitychange'));
    assert.equal(harness.surface.dataset.ambientRunning, 'true');
    cleanup(); harness.environment.dispatchEvent(new Event('visibilitychange'));
    assert.equal(harness.surface.dataset.ambientRunning, undefined);
  } finally { cleanup(); harness.restore(); }
});
