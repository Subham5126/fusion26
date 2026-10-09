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
