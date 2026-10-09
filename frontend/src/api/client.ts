import type { HealthResponse } from '../types/contracts';

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch('/api/health', { signal });
  if (!response.ok) throw new Error(`Health request failed (HTTP ${response.status})`);
  const data: unknown = await response.json();
  if (typeof data !== 'object' || data === null ||
      !('schema_version' in data) || data.schema_version !== '0.1.0' ||
      !('readiness' in data) || data.readiness !== 'bootstrap_only' ||
      !('service' in data) || data.service !== 'OrbitTrace' ||
      !('status' in data) || data.status !== 'ok' ||
      !('capabilities' in data) || typeof data.capabilities !== 'object' || data.capabilities === null) {
    throw new Error('Backend returned an incompatible health response');
  }
  const flags = ['schemas', 'synthetic_generation', 'detection', 'tracking', 'trajectory',
    'evaluation', 'analysis_api', 'uploads', 'exports'] as const;
  if (flags.some(flag => typeof (data.capabilities as Record<string, unknown>)[flag] !== 'boolean')) {
    throw new Error('Backend returned invalid capability flags');
  }
  return data as HealthResponse;
}
