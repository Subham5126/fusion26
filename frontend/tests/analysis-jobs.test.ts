import test from 'node:test';
import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import emptyFixture from '../../tests/contracts/fixtures/empty-result.json';
import trackFixture from '../../tests/contracts/fixtures/track-result.json';
import { getJob, getJobResult, runSyntheticDemo } from '../src/api/client';
import { parseAnalysisResult, parseDemoSubmission } from '../src/api/responseValidation';
import { ApiRequestError, requestJson } from '../src/api/transport';
import { createAnalysisJobController, jobPollIntervalMs, waitForJobPoll } from '../src/state/analysisJob';
import { presentAnalysis } from '../src/state/analysis';
import { AnalysisResults } from '../src/components/workbench/AnalysisPanel';
import type { AnalysisState } from '../src/state/analysis';
import type { AnalysisJobServices } from '../src/state/analysisJob';
import type { JobState } from '../src/types/contracts';

// Authored fixtures are used only for tests, never for a live demo fallback.
const acceptedId = 'job-verified';
const result = (jobId = acceptedId) => ({ ...structuredClone(trackFixture), job_id: jobId });
const job = (status: JobState['status'], jobId = acceptedId, overrides: Partial<JobState> = {}): JobState => ({
  job_id: jobId, status, progress_stage: status, progress_fraction: null, warnings: [], error: null, ...overrides,
});
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

async function usingFetch(stub: typeof fetch, check: () => Promise<void>) {
  const original = globalThis.fetch; globalThis.fetch = stub;
  try { await check(); } finally { globalThis.fetch = original; }
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
}

function serviceHarness(overrides: Partial<AnalysisJobServices> = {}) {
  const states: AnalysisState[] = [], events: string[] = [], delays: number[] = [];
  const services: AnalysisJobServices = {
    submit: async () => { events.push('submit'); return { job_id: acceptedId, status: 'queued' }; },
    job: async id => { events.push(`job:${id}`); return job('succeeded', id); },
    result: async id => { events.push(`result:${id}`); return result(id); },
    wait: async ms => { delays.push(ms); }, ...overrides,
  };
  const controller = createAnalysisJobController(state => states.push(state), services);
  return { states, events, delays, controller, latest: () => states.at(-1)! };
}

test('demo uses the verified bodyless POST, exact HTTP 202 envelope and caller abort signal', async () => {
  const signal = new AbortController().signal;
  await usingFetch(async (url, options) => {
    assert.equal(url, '/api/analyze/demo'); assert.equal(options?.method, 'POST');
    assert.equal(options?.body, undefined); assert.strictEqual(options?.signal, signal);
    return json({ job_id: acceptedId, status: 'queued' }, 202);
  }, async () => { assert.deepEqual(await runSyntheticDemo(signal), { job_id: acceptedId, status: 'queued' }); });
});

test('submission rejects missing, malformed, extra or nonqueued fields and unexpected success status', async () => {
  for (const response of [{ status: 'queued' }, { job_id: '../other', status: 'queued' }, { job_id: '', status: 'queued' },
    { job_id: acceptedId, status: 'running' }, { job_id: acceptedId, status: 'queued', sequence: {} }]) {
    assert.throws(() => parseDemoSubmission(response), /incompatible/);
  }
  await usingFetch(async () => json({ job_id: acceptedId, status: 'queued' }, 200), async () => {
    await assert.rejects(runSyntheticDemo(), /expected 202/);
  });
});

test('demo HTTP failures preserve backend error codes and details without automatic retry', async () => {
  let posts = 0;
  await usingFetch(async () => { posts++; return json({ error: { code: 'http_error', message: 'Request failed', details: null } }, 429); }, async () => {
    const h = serviceHarness({ submit: runSyntheticDemo }); await h.controller.start();
    assert.equal(h.latest().phase, 'failed');
    if (h.latest().phase === 'failed') assert.equal((h.latest() as Extract<AnalysisState, { phase: 'failed' }>).error.code, 'http_error');
    assert.equal(posts, 1); assert.deepEqual(h.events, []); h.controller.dispose();
  });
});

test('job and result GETs retain the accepted ID, signal and schema validation', async () => {
  const signal = new AbortController().signal; const urls: unknown[] = [];
  await usingFetch(async (url, options) => {
    urls.push(url); assert.equal(options?.method, 'GET'); assert.strictEqual(options?.signal, signal);
    return json(String(url).endsWith('/result') ? result() : job('succeeded'));
  }, async () => {
    assert.equal((await getJob(acceptedId, signal)).job_id, acceptedId);
    assert.equal((await getJobResult(acceptedId, signal)).schema_version, '0.1.0');
    assert.deepEqual(urls, [`/api/jobs/${acceptedId}`, `/api/jobs/${acceptedId}/result`]);
  });
});

test('unverified routes and unsafe job IDs are rejected before sending requests', async () => {
  let calls = 0;
  await usingFetch(async () => { calls++; return json({}); }, async () => {
    await assert.rejects(getJob('../other'), /incompatible/);
    await assert.rejects(getJob('job/result'), /incompatible/);
    await assert.rejects(getJobResult('job?token=value'), /incompatible/);
    await assert.rejects(requestJson(`/api/jobs/${acceptedId}/frames/0`), /not been verified/);
    assert.equal(calls, 0);
  });
});

test('queued, running and succeeded jobs retrieve exactly one validated result and stop polling', async () => {
  const statuses: JobState['status'][] = ['queued', 'running', 'succeeded']; let requests = 0, results = 0;
  const h = serviceHarness({ job: async id => { requests++; return job(statuses.shift()!, id); }, result: async id => { results++; return result(id); } });
  await h.controller.start();
  assert.deepEqual(h.states.map(state => state.phase), ['submitting', 'queued', 'processing', 'processing', 'awaiting_result', 'succeeded']);
  assert.deepEqual(h.delays, [750, 750, 750]); assert.equal(jobPollIntervalMs, 750);
  assert.equal(requests, 3); assert.equal(results, 1);
  assert.equal(presentAnalysis(h.latest()).detectionCount, 3);
  assert.equal('sequence' in h.latest(), false); // Submission supplies no manifest.
  assert.equal(presentAnalysis(h.states[1]).progress, null); h.controller.dispose();
});

test('polling waits for an in-flight job response before scheduling another poll', async () => {
  const inFlight = deferred<unknown>(), entered = deferred<void>(); let requests = 0;
  const h = serviceHarness({ job: async () => { requests++; entered.resolve(); return inFlight.promise; } });
  const running = h.controller.start(); await entered.promise;
  assert.equal(requests, 1); assert.equal(h.delays.length, 1);
  inFlight.resolve(job('succeeded')); await running;
  assert.equal(requests, 1); assert.equal(h.delays.length, 1); h.controller.dispose();
});

test('failed jobs preserve actual errors and warnings, stop polling and never retrieve a result', async () => {
  const error = { code: 'pipeline_error', message: 'RuntimeError: Registration (T13) not implemented', details: null };
  const h = serviceHarness({ job: async () => job('failed', acceptedId, { error, warnings: ['backend warning'] }) });
  await h.controller.start();
  const failed = h.latest(); assert.equal(failed.phase, 'failed');
  if (failed.phase === 'failed') { assert.deepEqual(failed.error, error); assert.deepEqual(failed.job?.warnings, ['backend warning']); }
  assert.deepEqual(h.events, ['submit']); assert.equal(h.delays.length, 1);
  assert.equal(presentAnalysis(failed).detectionCount, null); h.controller.dispose();
});

test('submission network failure has no invented job, counts or retry', async () => {
  let submissions = 0;
  const h = serviceHarness({ submit: async () => { submissions++; throw new TypeError('Failed to fetch'); } });
  await h.controller.start(); const state = h.latest();
  assert.equal(state.phase, 'failed');
  if (state.phase === 'failed') { assert.equal(state.error.code, 'network_error'); assert.equal(state.job, undefined); }
  assert.equal(submissions, 1); assert.equal(h.delays.length, 0); assert.equal(presentAnalysis(state).trackCount, null); h.controller.dispose();
});

test('polling network failure retains the last real job and does not fetch results', async () => {
  let polls = 0;
  const h = serviceHarness({ job: async () => { if (++polls === 1) return job('running', acceptedId, { warnings: ['actual warning'] }); throw new TypeError('Connection lost'); } });
  await h.controller.start(); const state = h.latest();
  assert.equal(state.phase, 'failed');
  if (state.phase === 'failed') { assert.equal(state.error.code, 'network_error'); assert.equal(state.job?.job_id, acceptedId); assert.deepEqual(state.job?.warnings, ['actual warning']); }
  assert.equal(polls, 2); assert.deepEqual(h.events, ['submit']); h.controller.dispose();
});

test('missing result after backend success remains a client failure, without success counts', async () => {
  const h = serviceHarness({ result: async () => { throw new ApiRequestError(404, { code: 'not_found', message: 'Result missing', details: null }); } });
  await h.controller.start(); const state = h.latest();
  assert.equal(state.phase, 'failed');
  if (state.phase === 'failed') { assert.equal(state.error.code, 'not_found'); assert.equal(state.job?.status, 'succeeded'); }
  assert.equal(presentAnalysis(state).detectionCount, null); h.controller.dispose();
});

test('wrong job, version, source and malformed results cannot become a successful demo', async () => {
  for (const response of [{ ...result(), job_id: 'wrong-job' }, { ...result(), schema_version: '0.2.0' }, { ...result(), source_type: 'real' }, { ...result(), detections: null }]) {
    const h = serviceHarness({ result: async () => response }); await h.controller.start();
    const state = h.latest(); assert.equal(state.phase, 'failed');
    if (state.phase === 'failed') assert.equal(state.error.code, 'incompatible_response');
    assert.equal(presentAnalysis(state).detectionCount, null); h.controller.dispose();
  }
  const h = serviceHarness({ job: async () => job('succeeded', 'wrong-job') }); await h.controller.start();
  assert.equal(h.latest().phase, 'failed'); assert.deepEqual(h.events, ['submit']); h.controller.dispose();
});

test('cancelling during the poll delay aborts monitoring without cancelling or fabricating the backend job', async () => {
  const entered = deferred<void>(); let signal: AbortSignal | undefined;
  const h = serviceHarness({ wait: (ms, abortSignal) => { signal = abortSignal; entered.resolve(); return waitForJobPoll(ms, abortSignal); } });
  const running = h.controller.start(); await entered.promise; h.controller.cancel(); await running;
  assert.equal(signal?.aborted, true); assert.equal(h.latest().phase, 'cancelled');
  if (h.latest().phase === 'cancelled') assert.equal((h.latest() as Extract<AnalysisState, { phase: 'cancelled' }>).jobId, acceptedId);
  assert.deepEqual(h.events, ['submit']); assert.equal(presentAnalysis(h.latest()).detectionCount, null); h.controller.dispose();
});

test('unmount disposal aborts an in-flight submission and ignores its late response', async () => {
  const pending = deferred<unknown>(); let signal: AbortSignal | undefined;
  const h = serviceHarness({ submit: async abortSignal => { signal = abortSignal; return pending.promise; } });
  const running = h.controller.start(); h.controller.dispose(); pending.resolve({ job_id: acceptedId, status: 'queued' }); await running;
  assert.equal(signal?.aborted, true); assert.deepEqual(h.states.map(state => state.phase), ['submitting']);
  await h.controller.start(); assert.equal(h.states.length, 1);
});

test('a replaced run cannot publish stale job or result responses even when fetch ignores abort', async () => {
  for (const stage of ['job', 'result'] as const) {
    const pending = deferred<unknown>(), entered = deferred<void>(); let submissions = 0;
    const h = serviceHarness({
      submit: async () => ({ job_id: ++submissions === 1 ? 'old-job' : 'new-job', status: 'queued' }),
      job: async id => { if (id === 'old-job' && stage === 'job') { entered.resolve(); return pending.promise; } return job('succeeded', id); },
      result: async id => { if (id === 'old-job' && stage === 'result') { entered.resolve(); return pending.promise; } return result(id); },
    });
    const old = h.controller.start(); await entered.promise; await h.controller.start();
    const completed = h.latest(); assert.equal(completed.phase, 'succeeded');
    if (completed.phase === 'succeeded') assert.equal(completed.result.job_id, 'new-job');
    const count = h.states.length;
    pending.resolve(stage === 'job' ? job('succeeded', 'old-job') : result('old-job')); await old;
    assert.equal(h.states.length, count); assert.strictEqual(h.latest(), completed); h.controller.dispose();
  }
});

test('poll delay removes abort listeners on completion and cancellation', async () => {
  for (const cancel of [false, true]) {
    const controller = new AbortController(), signal = controller.signal; let listeners = 0;
    const add = signal.addEventListener.bind(signal), remove = signal.removeEventListener.bind(signal);
    signal.addEventListener = (...args) => { listeners++; return add(...args); };
    signal.removeEventListener = (...args) => { listeners--; return remove(...args); };
    const waiting = waitForJobPoll(cancel ? 30_000 : 1, signal);
    if (cancel) { controller.abort(); await assert.rejects(waiting, { name: 'AbortError' }); } else await waiting;
    assert.equal(listeners, 0);
  }
});

test('result rendering uses real supplied detections, tracks, predictions, units, warnings and nulls', () => {
  const payload = result(); payload.warnings = ['<script>unsafe</script>'];
  const html = renderToStaticMarkup(createElement(AnalysisResults, { result: parseAnalysisResult(payload) }));
  assert.match(html, /fixture-track-1/); assert.match(html, /3 observations/); assert.match(html, /5 px\/frame/);
  assert.match(html, /extrapolated/); assert.match(html, /observed/); assert.match(html, /Not provided/);
  assert.match(html, /&lt;script&gt;unsafe&lt;\/script&gt;/); assert.doesNotMatch(html, /<script>/);
  assert.match(html, /local telescope viewer below remains a separate sequence/);
});

test('a validated empty result renders zero counts and honest missing benchmark metrics', () => {
  const html = renderToStaticMarkup(createElement(AnalysisResults, { result: parseAnalysisResult(emptyFixture) }));
  assert.match(html, /No candidates found/); assert.match(html, /No tracks returned/);
  assert.equal((html.match(/<strong>0<\/strong>/g) ?? []).length, 3);
  assert.match(html, /Benchmark metrics were not provided/); assert.doesNotMatch(html, /accuracy/i);
});
