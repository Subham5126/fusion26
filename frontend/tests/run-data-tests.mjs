// Uses esbuild already installed by Vite; adds no test framework or dependency.
import { build } from 'esbuild';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { join } from 'node:path';

const directory = await mkdtemp(join(tmpdir(), 'orbittrace-frontend-tests-'));
try {
  const outfile = join(directory, 'frontend.test.cjs');
  await build({ stdin: { contents: "import './data-boundaries.test';\nimport './sequence.test';\nimport './analysis-jobs.test';\nimport './live-visualization.test';\nimport './frame-manifest.test';",
    resolveDir: fileURLToPath(new URL('.', import.meta.url)), loader: 'ts' }, outfile,
    bundle: true, platform: 'node', format: 'cjs', target: 'node24', jsx: 'automatic', logLevel: 'silent' });
  await import(pathToFileURL(outfile).href);
} finally {
  await rm(directory, { recursive: true, force: true });
}
