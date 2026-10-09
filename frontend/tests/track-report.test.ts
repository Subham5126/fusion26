import test from 'node:test';
import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import fixture from '../../tests/contracts/fixtures/track-result.json';
import type { AnalysisResult, SequenceInput } from '../src/types/contracts';
import type { LocalFrame } from '../src/viewer/localSequence';
import { buildTrackReport, trackEvidence } from '../src/viewer/trackReport';
import { TrackQualityPanel } from '../src/components/workbench/TrackQualityPanel';
import { WorkbenchShell } from '../src/components/workbench/WorkbenchShell';
import { buildPdfReport } from '../src/viewer/pdfReport';
import { TrackPathDetail } from '../src/components/workbench/TrackPathDetail';
import { reviewTracks, reviewOverlay, isSupportedTrack } from '../src/viewer/resultReview';

const frames: LocalFrame[] = Array.from({ length: 5 }, (_, index) => ({ id: String(index), file: new File(['test'], `frame-${index}.png`),
  url: 'blob:private-preview', width_px: 640, height_px: 480, timestamp_s: null,
  header: { width: 640, height: 480, orientation: 1, format: 'image/png' } }));
const manifest: SequenceInput = { schema_version: '0.1.0', sequence_id: fixture.sequence_id, source_type: 'user_upload', profile: 'spotgeo',
  frames: frames.map((frame, frame_index) => ({ frame_index, image_ref: frame.file.name, width_px: 640, height_px: 480, timestamp_s: null })),
  dataset_id: null, dataset_version: null, input_sha256: null };
const result = () => structuredClone(fixture) as AnalysisResult;

test('report preserves backend result, exact raw/reference positions, upload metadata and null timestamps', () => {
  const input = result(), before = structuredClone(input);
  input.tracks[0].points[1].x_raw_px = 100; before.tracks[0].points[1].x_raw_px = 100;
  const report = buildTrackReport(input, manifest, frames, input.tracks[0].track_id);
  assert.deepEqual(report.analysis_result, before); assert.deepEqual(input, before);
  assert.equal(report.source.frame_count, 5); assert.equal(report.source.frames[0].width_px, 640);
  assert.equal(report.source.frames[0].timestamp_s, null);
  assert.equal(report.selected_track?.observations[1].x_raw_px, 100);
  assert.equal(report.selected_track?.observations[1].x_reference_px, 14);
  assert.equal(report.selected_track?.observed_coordinate_frame, 'reference_frame_0');
  assert.equal(report.selected_track?.predicted_coordinate_frame, 'reference_frame_0');
  assert.equal(report.selected_track?.direction, 'lower right');
  assert.equal(report.selected_track?.heuristic_quality, .5);
  assert.equal(report.selected_track?.observed_count, 3); assert.equal(report.selected_track?.predictions.length, 1);
  assert.match(report.selected_track!.summary, /frames 1, 2, 3/);
  assert.doesNotMatch(JSON.stringify(report), /blob:private-preview/);
});
test('report never fills missed detections or counts interpolated/predicted points as observations', () => {
  const input = result(), track = input.tracks[0];
  track.points[1].point_type = 'interpolated';
  track.points.reverse();
  track.trajectory!.predictions.push({ ...track.trajectory!.predictions[0], frame_index: 2 });
  const evidence = trackEvidence(track);
  assert.deepEqual(evidence.observations.map(point => point.frame_index), [0, 2]);
  assert.deepEqual(evidence.predictions.map(point => point.frame_index), [3]);
  const report = buildTrackReport(input, manifest, frames, track.track_id);
  assert.equal(report.counts.observations, 2); assert.equal(report.selected_track?.observed_count, 2);
});
test('empty/ESA-style no-fit results have no fabricated forecast or confidence', () => {
  const input = result(); input.tracks[0].trajectory = null;
  assert.deepEqual(buildTrackReport(input, manifest, frames, input.tracks[0].track_id).selected_track?.predictions, []);
  input.tracks = []; input.detections = [];
  const report = buildTrackReport(input, manifest, frames, null);
  assert.equal(report.selected_track, null); assert.deepEqual(report.counts, { detections: 0, tracks: 0, observations: 0 });
});
test('report refuses stale sequence or stale selected track', () => {
  assert.throws(() => buildTrackReport(result(), { ...manifest, sequence_id: 'different' }, frames, null), /does not match/);
  assert.throws(() => buildTrackReport(result(), manifest, frames, 'absent'), /absent/);
});
test('quality bar uses actual normalized score at low/medium/high boundaries; labels remain heuristic', () => {
  for (const [score, band] of [[0, 'low'], [.399, 'low'], [.4, 'medium'], [.699, 'medium'], [.7, 'high'], [1, 'high']] as const) {
    const track = result().tracks[0]; track.quality_score = score;
    const html = renderToStaticMarkup(createElement(TrackQualityPanel, { track, coordinateFrame: 'reference_frame_0' }));
    assert.match(html, new RegExp(`quality-${band}`)); assert.ok(html.includes(`aria-valuenow="${score}"`));
    assert.ok(html.includes(`width:${score * 100}%`)); assert.match(html, /Not a debris probability/);
    assert.match(html, /Actual observations/); assert.match(html, /fixture-track-1/);
  }
});
test('single observation and stationary tracks have honest direction descriptions', () => {
  const track = result().tracks[0]; track.points = [track.points[0]];
  assert.equal(trackEvidence(track).direction, 'Insufficient observations');
  track.points.push({ ...track.points[0], frame_index: 1 });
  assert.equal(trackEvidence(track).direction, 'No net displacement');
});
test('main workbench has uploads without synthetic runner; landing preview remains explicitly conceptual', () => {
  const live = renderToStaticMarkup(createElement(WorkbenchShell));
  assert.match(live, /Choose images/); assert.doesNotMatch(live, /id="synthetic-analysis"|CONCEPTUAL ILLUSTRATION/);
  assert.match(renderToStaticMarkup(createElement(WorkbenchShell, { preview: true })), /CONCEPTUAL ILLUSTRATION/);
});
test('PDF report contains actual quality, coordinate labels, source metadata, predictions and valid byte offsets', () => {
  const input = result();
  const bytes = buildPdfReport(buildTrackReport(input, manifest, frames, input.tracks[0].track_id));
  const pdf = new TextDecoder().decode(bytes);
  assert.ok(pdf.startsWith('%PDF-1.4')); assert.ok(pdf.endsWith('%%EOF\n'));
  assert.match(pdf, /fixture-track-1/); assert.match(pdf, /50.0%/); assert.match(pdf, /reference_frame_0/);
  assert.match(pdf, /frame-0.png/); assert.match(pdf, /22.000, 21.000 px/);
  assert.ok(pdf.includes('Predicted coordinates \\(not observations\\)'));
  const start = Number(pdf.match(/startxref\n(\d+)/)![1]);
  assert.equal(pdf.slice(start, start + 4), 'xref');
  for (const row of pdf.matchAll(/(\d{10}) 00000 n /g)) assert.match(pdf.slice(Number(row[1]), Number(row[1]) + 20), /^\d+ 0 obj/);
});
test('PDF paginates long metadata, escapes PDF literals and handles empty results', () => {
  const input = result(); input.tracks = []; input.detections = [];
  const report = buildTrackReport(input, manifest, frames, null);
  report.source.frames[0].filename = 'image (draft) \\ endstream\ntrailer.png';
  report.analysis_result.warnings = Array.from({ length: 90 }, (_, i) => `Warning ${i}: ${'long warning '.repeat(10)}`);
  const pdf = new TextDecoder().decode(buildPdfReport(report));
  assert.ok(pdf.includes('image \\(draft\\)'));
  assert.match(pdf, /No selected track/); assert.doesNotMatch(pdf, /Heuristic quality:/);
  const count = Number(pdf.match(/\/Type \/Pages \/Count (\d+)/)![1]);
  assert.ok(count > 2); assert.match(pdf, new RegExp(`Page ${count} of ${count}`));
  assert.match(pdf, /Warning 89/);
});
test('enlarged path connects only actual past observations and keeps future forecasts separate', () => {
  const track = result().tracks[0];
  const render = (frameIndex: number, coordinateFrame = 'reference_frame_0') => renderToStaticMarkup(createElement(TrackPathDetail,
    { track, frameIndex, coordinateFrame, visibility: { tracks: true, predictions: true } }));
  assert.doesNotMatch(render(0), /detail-observed-path|detail-predicted-path/);
  assert.match(render(1), /points="10,12 14,15"/); assert.doesNotMatch(render(1), /detail-predicted-path/);
  assert.match(render(4), /points="10,12 14,15 18,18"/);
  assert.match(render(2), /detail-predicted-path/);
  assert.doesNotMatch(render(4), /detail-predicted-path/);
  assert.doesNotMatch(render(4, 'raw_pixels'), /detail-predicted-path/);
});
test('supported review excludes short/weak/unstable candidates without changing scores or raw exports', () => {
  const input = result(), supported = input.tracks[0];
  assert.equal(isSupportedTrack(supported), true);
  const short = { ...supported, track_id: 'short', points: supported.points.slice(0, 2) };
  const weak = { ...supported, track_id: 'weak', quality_score: .49 };
  const unstable = { ...supported, track_id: 'unstable', trajectory: { ...supported.trajectory!, fit_rmse_px: 4 } };
  input.tracks.push(short, weak, unstable);
  const before = structuredClone(input);
  assert.deepEqual(reviewTracks(input, false).map(track => track.track_id), ['fixture-track-1']);
  assert.equal(reviewTracks(input, true).length, 4); assert.deepEqual(input, before);
});
test('review overlays hide unverified raw candidates and show only the next future frame', () => {
  const input = result(), id = input.tracks[0].track_id;
  const model = { warnings: [], detections: [{ id: 'd0', trackId: id, center: { x: 10, y: 12 }, box: { x: 9, y: 11, width: 3, height: 3 } },
    { id: 'unverified', center: { x: 40, y: 30 }, box: { x: 39, y: 29, width: 3, height: 3 } }],
    tracks: [{ id, observed: [{ x: 18, y: 18, frame: 2 }], segments: [], predictions: [{ x: 22, y: 21, frame: 3 }, { x: 26, y: 24, frame: 4 }], forecast: [] }] };
  const limited = reviewOverlay(model, input, false, 2);
  assert.equal(limited.detections.length, 1); assert.equal(limited.tracks[0].predictions.length, 1);
  assert.equal(limited.tracks[0].predictions[0].frame, 3); assert.equal(limited.tracks[0].forecast.length, 2);
  assert.equal(reviewOverlay(model, input, true, 2).detections.length, 2);
  assert.equal(reviewOverlay(model, input, false, 4).tracks[0].predictions.length, 0);
});
