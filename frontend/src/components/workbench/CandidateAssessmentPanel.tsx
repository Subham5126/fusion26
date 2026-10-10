import type { AnalysisResult, Track } from '../../types/contracts';
import { candidateAssessment } from '../../viewer/candidateAssessment';

export function CandidateAssessmentPanel({ result, diagnostics, track, frame }: {
  result: AnalysisResult; diagnostics: unknown; track?: Track; frame: number;
}) {
  const assessment = candidateAssessment(result, diagnostics);
  const point = track?.points.find(p => p.point_type === 'observed' && p.frame_index === frame);
  const detection = result.detections.find(d => d.detection_id === point?.detection_id);
  const score = assessment.candidates.find(c => c.detection_id === detection?.detection_id);
  return <section className="track-quality-panel" aria-label="AI Candidate Assessment">
    <h4>AI Candidate Assessment</h4>
    <dl className="evidence-values"><div><dt>Detector heuristic</dt><dd>{detection ? detection.quality_score.toFixed(3) : 'No current observation'}</dd></div>
      <div><dt>Candidate ML score</dt><dd>{score ? `${score.score.toFixed(3)} · ${score.category}` : 'Unavailable'}</dd></div>
      <div><dt>Model</dt><dd>{assessment.model_name ?? 'Disabled / incompatible'}</dd></div>
      <div><dt>Validation status</dt><dd>{assessment.status}</dd></div></dl>
    <p className="quality-explanation">{assessment.interpretation}</p>
  </section>;
}
