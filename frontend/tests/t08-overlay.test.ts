import test from 'node:test';
import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { T08Overlay } from '../src/components/workbench/T08Overlay';
import type { ScientificOverlayModel } from '../src/viewer/scientificOverlay';
import { trackColors } from '../src/viewer/trackColors';
import { buildUploadManifest, uploadOverlay } from '../src/viewer/uploadOverlay';
import type { LocalFrame } from '../src/viewer/localSequence';
import fixture from '../../tests/contracts/fixtures/track-result.json';
import type { AnalysisResult } from '../src/types/contracts';

const model: ScientificOverlayModel = {
  detections: [{ id: 'd2', trackId: 'track-A', center: { x: 639, y: 479 }, box: { x: 637.5, y: 477.5, width: 2, height: 2 } }],
  tracks: [{ id: 'track-A', observed: [{ x: 630, y: 470, frame: 0 }, { x: 639, y: 479, frame: 2 }], segments: [],
    predictions: [{ x: 648, y: 488, frame: 3 }], forecast: [{ x: 639, y: 479 }, { x: 648, y: 488 }] },
  { id: 'track-B', observed: [{ x: 20, y: 20, frame: 0 }], segments: [], predictions: [], forecast: [] }], warnings: [],
};
const render = (scale = 1, selected: string | null = 'track-A', visibility = { detections: true, tracks: true, predictions: true }) =>
  renderToStaticMarkup(createElement(T08Overlay, { model, scale, selected, select: () => {}, visibility, nativeSize: { width: 640, height: 480 } }));

test('T08 boxes retain real detection geometry through fit and 8x zoom, with readable ID labels', () => {
  for (const scale of [.4, 1, 4, 8]) {
    const html = render(scale);
    assert.match(html, /data-detection-id="d2"/);
    assert.match(html, /x="637.5" y="477.5" width="2" height="2"/);
    assert.match(html, /t08-neon-box/); assert.match(html, />track-A<\/text>/);
    assert.match(html, new RegExp(`stroke-width="${2.7 / scale}"`));
  }
});
test('actual observations stay filled, age fades, and a gap has no manufactured observed marker', () => {
  const html = render();
  assert.match(html, /data-from-frame="0" data-to-frame="2"/);
  assert.doesNotMatch(html, /data-observed-frame="1"/);
  assert.match(html, /opacity="0.625"/); assert.match(html, /opacity="1"/);
  assert.equal((html.match(/data-observed-frame=/g) ?? []).length, 3);
});
test('selected track and owning box match; forecast is contrasting, dashed and hollow', () => {
  const html = render(), colors = trackColors('track-A');
  assert.notEqual(colors.observed, colors.forecast);
  assert.match(html, /t08-track is-selected/);
  assert.match(html, /opacity:0.3/); assert.match(html, /opacity:1/);
  assert.ok(html.includes(`stroke:${colors.observed}`)); assert.ok(html.includes(`stroke:${colors.forecast}`));
  assert.match(html, /stroke-dasharray="5 4"/); assert.match(html, /class="predicted-point"[^>]*fill="none"/);
});
test('overlay toggles remain independent, and empty completed results have no fake geometry', () => {
  const forecastOnly = render(1, null, { detections: false, tracks: false, predictions: true });
  assert.doesNotMatch(forecastOnly, /data-detection-id|data-observed-frame/); assert.match(forecastOnly, /data-predicted-frame/);
  const observedOnly = render(1, null, { detections: false, tracks: true, predictions: false });
  assert.match(observedOnly, /data-observed-frame/); assert.doesNotMatch(observedOnly, /data-predicted-frame/);
  const empty = renderToStaticMarkup(createElement(T08Overlay, { model: { detections: [], tracks: [], warnings: [] }, scale: 1, selected: null,
    select: () => {}, visibility: { detections: true, tracks: true, predictions: true } }));
  assert.doesNotMatch(empty, /<rect|<circle|<line|<polyline/);
});
test('track colors do not change when frame results reorder tracks', () => {
  const before = ['track-A', 'track-B'].map(trackColors);
  const after = ['track-B', 'track-A'].map(trackColors).reverse();
  assert.deepEqual(before, after);
});

function uploaded() {
  const frames: LocalFrame[] = Array.from({ length: 5 }, (_, i) => ({ id: String(i), file: new File(['image'], `${i}.png`), url: 'blob:test',
    width_px: 640, height_px: 480, timestamp_s: null, header: { width: 640, height: 480, orientation: 1, format: 'image/png' } }));
  const manifest = buildUploadManifest(frames);
  const result = structuredClone(fixture) as AnalysisResult;
  result.sequence_id = manifest.sequence_id; result.source_type = 'user_upload'; result.profile = 'spotgeo'; result.registration.status = 'estimated';
  const diagnostics = { sequence: manifest, registration: { status: 'estimated', transform_direction: 'raw_to_reference',
    frames: frames.map(() => ({ reference_to_raw: [[1,0,10],[0,1,5],[0,0,1]] })) } };
  return { frames, manifest, result, diagnostics };
}
test('upload timeline limits past positions, and forecasts cannot overlap the last observation', () => {
  const s = uploaded();
  assert.equal(uploadOverlay(s.result, s.frames[0], 0, s.manifest, s.diagnostics).tracks[0].observed.length, 1);
  assert.equal(uploadOverlay(s.result, s.frames[0], 0, s.manifest, s.diagnostics).tracks[0].predictions.length, 0);
  s.result.tracks[0].trajectory!.predictions.push({ ...s.result.tracks[0].trajectory!.predictions[0], frame_index: 1 });
  const final = uploadOverlay(s.result, s.frames[4], 4, s.manifest, s.diagnostics);
  assert.ok(final.tracks[0].predictions.every(p => p.frame > 2));
});
test('wrong coordinate frame and failed registration cannot render plausible forecast geometry', () => {
  const s = uploaded(); s.result.coordinate_frame = 'raw_pixels';
  assert.equal(uploadOverlay(s.result, s.frames[4], 4, s.manifest, s.diagnostics).tracks.length, 0);
  s.result.coordinate_frame = 'reference_frame_0'; s.result.registration.status = 'failed';
  assert.equal(uploadOverlay(s.result, s.frames[4], 4, s.manifest, s.diagnostics).tracks.length, 0);
});
test('selected observed path accumulates and rewinds with the timeline, retaining native projected geometry', () => {
  const s = uploaded();
  for (const index of [0, 1, 2, 3, 4, 1, 0]) {
    const model = uploadOverlay(s.result, s.frames[index], index, s.manifest, s.diagnostics);
    const html = renderToStaticMarkup(createElement(T08Overlay, { model, scale: 2, selected: s.result.tracks[0].track_id,
      currentFrame: index, select: () => {}, visibility: { detections: true, tracks: true, predictions: true } }));
    assert.equal((html.match(/data-observed-frame=/g) ?? []).length, Math.min(index + 1, 3));
    assert.equal((html.match(/data-from-frame=/g) ?? []).length, Math.min(index, 2));
    assert.equal((html.match(/data-current-observed-frame=/g) ?? []).length, index < 3 ? 1 : 0);
    assert.match(html, /cx="20" cy="17"/); // reference (10,12) + current-frame inverse (10,5)
    assert.ok(model.tracks[0].observed.every(point => point.frame <= index));
  }
});
