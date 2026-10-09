import type { AnalysisResult, HealthResponse, JobState } from '../types/contracts';
import { parseAnalysisResult, parseDemoSubmission, parseHealthResponse, parseJobId, parseJobState } from './responseValidation';
import { postDemoJson, requestJson, requestFrameBlob } from './transport';
import { parseJobManifest } from './frameManifest';
import type { JobManifest } from './frameManifest';

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return parseHealthResponse(await requestJson('/api/health', signal));
}

export async function runSyntheticDemo(signal?: AbortSignal) {
  return parseDemoSubmission(await postDemoJson(signal));
}

export async function getJob(jobId: string, signal?: AbortSignal): Promise<JobState> {
  return parseJobState(await requestJson(`/api/jobs/${parseJobId(jobId)}`, signal));
}

export async function getJobResult(jobId: string, signal?: AbortSignal): Promise<AnalysisResult> {
  return parseAnalysisResult(await requestJson(`/api/jobs/${parseJobId(jobId)}/result`, signal));
}

export const getJobFrame = requestFrameBlob;

export async function getJobManifest(jobId: string, signal?: AbortSignal): Promise<JobManifest> {
  const id = parseJobId(jobId);
  return parseJobManifest(await requestJson(`/api/jobs/${id}/manifest`, signal), id);
}
