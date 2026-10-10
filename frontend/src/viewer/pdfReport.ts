import type { buildTrackReport } from './trackReport';

type Report = ReturnType<typeof buildTrackReport>;
// Dependency-free, text-only PDF 1.4 using standard Helvetica fonts. No HTML,
// scripts, external resources or server request. Strings are escaped as PDF
// literals; all object/stream offsets are computed from the final ASCII bytes.
const ascii = (value: string) => value.normalize('NFKD').replace(/[^\x20-\x7e]/g, '?');
const literal = (value: string) => ascii(value).replace(/[\\()]/g, '\\$&');
const wrap = (value: string, width = 88): string[] => {
  const text = ascii(value), lines: string[] = [];
  for (let offset = 0; offset < text.length;) {
    let end = offset, advance = 0;
    // Conservative Helvetica advances prevent very wide filenames from spilling
    // past the page margin, without assuming fixed-width characters.
    while (end < text.length && end - offset < width) {
      const character = text[end], next = character === ' ' ? 3 : /[WMwm@%]/.test(character) ? 10 : /[A-Z&]/.test(character) ? 8 : 6;
      if (advance + next > 500) break;
      advance += next; end++;
    }
    if (end < text.length) { const space = text.lastIndexOf(' ', end); if (space > offset) end = space; }
    lines.push(text.slice(offset, end).trim()); offset = end;
    while (text[offset] === ' ') offset++;
  }
  return lines.length ? lines : [''];
};

export function buildPdfReport(report: Report): Uint8Array<ArrayBuffer> {
  const pages: string[][] = []; let commands: string[] = [], y = 750;
  const text = (value: string, x: number, top: number, size = 10, bold = false, color = '0.12 0.18 0.23') =>
    commands.push(`BT /${bold ? 'F2' : 'F1'} ${size} Tf ${color} rg 1 0 0 1 ${x} ${top} Tm (${literal(value)}) Tj ET`);
  const page = () => {
    if (commands.length) pages.push(commands);
    commands = []; y = 748;
    commands.push('0.02 0.09 0.12 rg 0 778 595 64 re f');
    text('OrbitTrace | Observation report', 42, 802, 18, true, '1 1 1');
    text('Image-plane candidate evidence - identity unverified', 42, 785, 9, false, '0.4 0.92 0.84');
  };
  const ensure = (height: number) => { if (y - height < 56) page(); };
  const paragraph = (value: string) => { for (const line of wrap(value)) { ensure(15); text(line, 42, y); y -= 15; } y -= 4; };
  const heading = (value: string) => { ensure(48); y -= 9; text(value, 42, y, 13, true, '0.02 0.4 0.36'); y -= 22; };
  const number = (value: number | null) => value === null ? 'unknown' : value.toFixed(3);
  page();
  paragraph(`Job: ${report.source.job_id}`);
  paragraph(`Sequence: ${report.source.sequence_id}`);
  paragraph(`Generated: ${report.generated_at} | Source: ${report.source.source_type}`);
  paragraph(`${report.source.frame_count} frames | ${report.counts.detections} detections | ${report.counts.tracks} tracks | ${report.counts.observations} actual observations`);
  paragraph(`Detections by frame: ${report.detection_summary.per_frame.map(f => `${f.frame_index + 1}: ${f.count}`).join('; ')}.`);
  paragraph(`Association confirmed: ${report.detection_summary.association_confirmed}; tentative: ${report.detection_summary.tentative}; ended: ${report.detection_summary.ended}. Supported motion tracks: ${report.detection_summary.supported_motion_tracks}; uncertain candidate tracks: ${report.detection_summary.uncertain_candidate_tracks}. These do not establish identity.`);
  heading('Uploaded frames');
  for (const frame of report.source.frames) paragraph(`Frame ${frame.frame_index + 1}: ${frame.filename} | ${frame.width_px} x ${frame.height_px} px | timestamp: ${frame.timestamp_s ?? 'unknown'}`);
  const track = report.selected_track;
  heading('Selected track evidence');
  if (track) {
    paragraph(`${track.track_id} | ${track.status} | ${track.observed_count} observations | ${track.predictions.length} future predictions`);
    paragraph(`Heuristic quality: ${track.heuristic_quality.toFixed(3)} / 1 (${(track.heuristic_quality * 100).toFixed(1)}%, ${track.quality_band} support). Not a debris probability.`);
    ensure(28);
    commands.push(`0.88 0.92 0.93 rg 42 ${y - 5} 510 8 re f`);
    const qualityColor = track.quality_band === 'high' ? '0.02 0.65 0.5' : track.quality_band === 'medium' ? '0.72 0.59 0.05' : '0.85 0.38 0.05';
    commands.push(`${qualityColor} rg 42 ${y - 5} ${510 * track.heuristic_quality} 8 re f`); y -= 26;
    paragraph(track.summary);
    paragraph(`Observed frame: ${track.observed_coordinate_frame}; predicted frame: ${track.predicted_coordinate_frame ?? 'no fit'}. Units: px. Raw positions belong to their individual source frames.`);
    heading('Observed coordinates');
    paragraph('Frame | reference x, y (px) | raw x, y (px) | timestamp (s)');
    for (const point of track.observations) paragraph(`${point.frame_index + 1} | ${number(point.x_reference_px)}, ${number(point.y_reference_px)} | ${number(point.x_raw_px)}, ${number(point.y_raw_px)} | ${number(point.timestamp_s)}`);
    paragraph(`Missing observations (one-based frames): ${track.missing_observation_frames.map(i => i + 1).join(', ') || 'none'}. No invented points.`);
    heading('Linked detections');
    for (const d of track.detections) paragraph(`Frame ${d.frame_index + 1} | ${d.detector_name} | raw box [${d.bbox_raw_px.map(v => number(v)).join(', ')}] | heuristic ${number(d.quality_score)}. Upper box limits exclusive.`);
    heading('Predicted coordinates (not observations)');
    paragraph(`Model: ${track.prediction_model ?? 'unavailable'}. Prediction uncertainty: unavailable. The viewer shows at most the next frame; this report retains all backend forecasts.`);
    if (!track.predictions.length) paragraph('No backend forecasts available for this track.');
    for (const point of track.predictions) paragraph(`Frame ${point.frame_index + 1} | ${number(point.x_reference_px)}, ${number(point.y_reference_px)} px | out of field: ${point.out_of_field ?? 'unknown'}`);
  } else paragraph('No selected track. Empty completed results have no invented confidence or forecasts.');
  heading('AI candidate assessment');
  paragraph(`${report.candidate_assessment.status} | ${report.candidate_assessment.model_name ?? 'No compatible model enabled'}`);
  paragraph(report.candidate_assessment.interpretation);
  for (const score of report.candidate_assessment.candidates.filter(s => track?.detections.some(d => d.detection_id === s.detection_id)))
    paragraph(`Frame ${score.frame_index + 1} | ${score.detection_id} | ML score ${number(score.score)} (${score.category}).`);
  if (report.original_candidates_before_motion_mode.length) paragraph(`${report.original_candidates_before_motion_mode.length} original Standard candidates retained in Report JSON for comparison with experimental Motion mode.`);
  heading('Analysis warnings and limitations');
  for (const warning of [...report.analysis_result.warnings, ...report.analysis_result.registration.warnings,
    ...(track ? report.analysis_result.tracks.find(item => item.track_id === track.track_id)?.warnings ?? [] : []), ...report.limitations]) paragraph(warning);
  paragraph('PDF tables round coordinates to 3 decimals. Report JSON retains exact numeric values and the full backend result. Non-ASCII characters in PDF text are transliterated when possible, otherwise shown as ?.');
  pages.push(commands);
  pages.forEach((content, index) => content.push(`BT /F1 9 Tf 0.4 0.48 0.52 rg 1 0 0 1 42 30 Tm (OrbitTrace - Page ${index + 1} of ${pages.length}) Tj ET`));
  const objects: string[] = ['', '', '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>', '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>'];
  const children: string[] = [];
  for (const content of pages) {
    const pageId = objects.length + 1, streamId = pageId + 1, stream = content.join('\n') + '\n';
    children.push(`${pageId} 0 R`);
    objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents ${streamId} 0 R >>`);
    objects.push(`<< /Length ${stream.length} >>\nstream\n${stream}endstream`);
  }
  objects[0] = '<< /Type /Catalog /Pages 2 0 R >>';
  objects[1] = `<< /Type /Pages /Count ${pages.length} /Kids [${children.join(' ')}] >>`;
  let pdf = '%PDF-1.4\n', offsets = [0];
  objects.forEach((object, index) => { offsets.push(pdf.length); pdf += `${index + 1} 0 obj\n${object}\nendobj\n`; });
  const xref = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  pdf += offsets.slice(1).map(offset => `${String(offset).padStart(10, '0')} 00000 n \n`).join('');
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return new TextEncoder().encode(pdf);
}

export function downloadPdfReport(report: Report) {
  const url = URL.createObjectURL(new Blob([buildPdfReport(report)], { type: 'application/pdf' }));
  const link = document.createElement('a'); link.href = url;
  link.download = `orbittrace-${report.source.job_id}-${report.selected_track?.track_id ?? 'analysis'}.pdf`.replace(/[^\w.-]/g, '_');
  document.body.append(link); link.click(); link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
