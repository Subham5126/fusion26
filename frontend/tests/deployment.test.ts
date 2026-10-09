import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveApiUrl } from '../src/api/baseUrl';

test('every deployed exchange and export uses the selected API origin; local proxy remains unchanged', () => {
  for (const endpoint of ['/api/health', '/api/analyze/demo', '/api/analyze/upload', '/api/jobs/job-1',
    '/api/jobs/job-1/result', '/api/jobs/job-1/manifest', '/api/jobs/job-1/frames/4', '/api/jobs/job-1/diagnostics',
    '/api/jobs/job-1/exports/json', '/api/jobs/job-1/exports/csv']) {
    assert.equal(resolveApiUrl(endpoint), endpoint);
    assert.equal(resolveApiUrl(endpoint, 'https://backend.example.test/'), `https://backend.example.test${endpoint}`);
    assert.equal(resolveApiUrl(endpoint, 'http://127.0.0.1:8030'), `http://127.0.0.1:8030${endpoint}`);
  }
});

test('production origin cannot leak credentials or select an insecure, nested or unrelated endpoint', () => {
  for (const base of ['http://backend.example.test', 'https://user:secret@example.test', 'https://example.test/private',
    'https://example.test?token=secret', 'https://example.test#fragment', 'javascript:alert(1)', 'not a URL']) {
    assert.throws(() => resolveApiUrl('/api/health', base));
  }
  for (const endpoint of ['https://other.test/api/health', '//other.test/api/health', '/api/../secret', '/api//health', '/secret']) {
    assert.throws(() => resolveApiUrl(endpoint, 'https://backend.example.test'));
  }
});
