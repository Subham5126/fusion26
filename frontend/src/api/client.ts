import type { HealthResponse } from '../types/contracts';
import { parseHealthResponse } from './responseValidation';
import { requestJson } from './transport';

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return parseHealthResponse(await requestJson('/api/health', signal));
}
