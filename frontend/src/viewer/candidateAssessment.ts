import type { AnalysisResult } from '../types/contracts';

export interface CandidateScore { detection_id: string; frame_index: number; score: number; category: string }
const record = (value: unknown): Record<string, unknown> | null => value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null;

// Diagnostics are optional and outside schema 0.1.0. Never borrow scores from
// another job/sequence, or attach an assessment to an unrelated detection.
export function candidateAssessment(result: AnalysisResult, diagnostics: unknown) {
  const data = record(diagnostics), sequence = record(data?.sequence);
  const fallback = { status: 'unavailable', model_name: null as string | null, candidates: [] as CandidateScore[],
    interpretation: 'No compatible supervised model is enabled for this detector.', automatic_filtering: false };
  if (sequence?.sequence_id !== result.sequence_id) return fallback;
  const assessment = record(data?.candidate_assessment);
  if (assessment?.status !== 'experimental' || typeof assessment.model_name !== 'string' || !Array.isArray(assessment.candidates)) return fallback;
  const byId = new Map(result.detections.map(d => [d.detection_id, d]));
  const seen = new Set<string>(), candidates: CandidateScore[] = [];
  for (const value of assessment.candidates) {
    const row = record(value), id = row?.detection_id;
    if (typeof id !== 'string' || seen.has(id) || byId.get(id)?.frame_index !== row?.frame_index ||
      typeof row?.score !== 'number' || !Number.isFinite(row.score) || row.score < 0 || row.score > 1) return fallback;
    seen.add(id);
    candidates.push({ detection_id: id, frame_index: row.frame_index as number, score: row.score,
      category: row.score >= .7 ? 'high' : row.score >= .4 ? 'medium' : 'low' });
  }
  return { ...fallback, status: 'experimental', model_name: assessment.model_name.slice(0, 100), candidates,
    interpretation: 'Uncalibrated annotation-match score. Not debris probability; no automatic filtering.' };
}

export function originalCandidates(result: AnalysisResult, diagnostics: unknown): unknown[] {
  const data = record(diagnostics);
  return record(data?.sequence)?.sequence_id === result.sequence_id && Array.isArray(data?.original_detections)
    ? data.original_detections : [];
}
