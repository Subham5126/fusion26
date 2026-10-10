import type { AnalysisResult, HealthResponse, JobState, SequenceInput } from '../types/contracts';
import { parseAnalysisResult, parseDemoSubmission, parseHealthResponse, parseJobId, parseJobState } from './responseValidation';
import { postDemoJson, requestJson, requestFrameBlob, throwHttpError } from './transport';
import type { DemoPreset } from './transport';
import { parseJobManifest } from './frameManifest';
import type { JobManifest } from './frameManifest';
import { apiUrl } from './baseUrl';

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return parseHealthResponse(await requestJson('/api/health', signal));
}

export async function runSyntheticDemo(signal?: AbortSignal, preset?: DemoPreset) {
  return parseDemoSubmission(await postDemoJson(signal, preset));
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

export async function runUpload(sequence: SequenceInput, files: File[], signal?: AbortSignal, mode: 'standard' | 'temporal' = 'standard') {
  const body = new FormData();
  body.append('manifest', JSON.stringify(sequence));
  body.append('analysis_mode', mode);
  for (const file of files) body.append('files', file, file.name);
  const response = await fetch(apiUrl('/api/analyze/upload'), { method: 'POST', body, signal });
  if (!response.ok) await throwHttpError(response, signal);
  if (response.status !== 202) throw new Error('Upload was not accepted as a job');
  return parseDemoSubmission(await response.json());
}

export async function getJobDiagnostics(jobId: string, signal?: AbortSignal): Promise<unknown> {
  const response = await fetch(apiUrl(`/api/jobs/${parseJobId(jobId)}/diagnostics`), { signal });
  if (!response.ok) await throwHttpError(response, signal);
  return response.json();
}
