// Uses esbuild already installed by Vite; adds no test framework or dependency.
import { build } from 'esbuild';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { join } from 'node:path';

const directory = await mkdtemp(join(tmpdir(), 'orbittrace-frontend-tests-'));
try {
  const outfile = join(directory, 'data-boundaries.test.mjs');
  await build({ entryPoints: [fileURLToPath(new URL('./data-boundaries.test.ts', import.meta.url))], outfile,
    bundle: true, platform: 'node', format: 'esm', target: 'node24', packages: 'external', logLevel: 'silent' });
  await import(pathToFileURL(outfile).href);
} finally {
  await rm(directory, { recursive: true, force: true });
}
