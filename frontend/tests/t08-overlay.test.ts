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
  for (const scale of [.4, 1, 2, 4, 8]) {
    const html = render(scale);
    assert.match(html, /data-detection-id="d2"/);
    assert.match(html, /x="637.5" y="477.5" width="2" height="2"/);
    assert.match(html, /t08-neon-box/); assert.match(html, />track-A<\/text>/);
    assert.match(html, new RegExp(`stroke-width="${2.7 / scale}"`));
  }
});

test('selected-only paths hide other histories while retaining all current detections', () => {
  const html = renderToStaticMarkup(createElement(T08Overlay, {model,scale:1,selected:'track-A',select:()=>{},
    visibility:{detections:true,tracks:true,predictions:true},showAllTracks:false,uncertainTrackIds:new Set(['track-B'])}));
  assert.match(html,/data-track-id="track-A"/); assert.doesNotMatch(html,/data-track-id="track-B"/);
  assert.match(html,/data-detection-id="d2"/); assert.match(html,/>Predicted<\/text>/);
});
test('actual observations stay filled, age fades, and a gap has no manufactured observed marker', () => {
  const html = render();
  assert.match(html, /data-from-frame="0" data-to-frame="2"/);
  assert.doesNotMatch(html, /data-observed-frame="1"/);
  assert.match(html, /opacity="0.825"/); assert.match(html, /opacity="1"/);
  assert.equal((html.match(/data-observed-frame=/g) ?? []).length, 3);
});

test('a selected sparse track retains its labeled history across missed frames and links only actual observations', () => {
  const s = uploaded();
  const first = s.result.tracks[0].points[0];
  const later = s.result.tracks[0].points[2];
  later.frame_index = 3;
  s.result.detections.find(d=>d.detection_id===later.detection_id)!.frame_index=3;
  s.result.tracks[0].points=[first,later];
  s.result.tracks[0].trajectory=null;
  for (const index of [0,1,2,3,4,1]) {
    const m=uploadOverlay(s.result,s.frames[index],index,s.manifest,s.diagnostics);
    const html=renderToStaticMarkup(createElement(T08Overlay,{model:m,scale:1,selected:s.result.tracks[0].track_id,
      currentFrame:index,select:()=>{},showAllTracks:false,visibility:{detections:true,tracks:true,predictions:true}}));
    assert.match(html,/data-observed-frame="0"/);
    assert.match(html,/data-history-label-frame="0"/);
    assert.equal(m.tracks[0].observed.length,index>=3?2:1);
    assert.equal(m.tracks[0].segments.length,index>=3?1:0);
    assert.equal((html.match(/data-from-frame=/g)??[]).length,index>=3?1:0);
    assert.doesNotMatch(html,/data-observed-frame="[124]"/);
    if ([1,2,4].includes(index)) assert.match(html,/data-last-seen-track=/);
  }
});

test('gap markers use preceding observations and camera shifts without becoming detections or future forecasts', () => {
  const s=uploaded(), track=s.result.tracks[0];
  const later={...track.points[2],frame_index:3};
  s.result.detections.find(d=>d.detection_id===later.detection_id)!.frame_index=3;
  track.points=[track.points[0],later]; track.trajectory=null;
  s.diagnostics.registration.frames.forEach((f,i)=>{ f.reference_to_raw[0][2]=30*i; f.reference_to_raw[1][2]=20*i; });
  const before=structuredClone(s.result);
  for (const index of [0,1,2,3,4,1]) {
    const m=uploadOverlay(s.result,s.frames[index],index,s.manifest,s.diagnostics,'original',true);
    assert.deepEqual(m.tracks[0].estimated!.map(p=>p.frame),Array.from({length:Math.min(index,2)},(_,i)=>i+1));
    m.tracks[0].estimated!.forEach(p=>{
      assert.equal(p.x,track.points[0].x_reference_px+30*p.frame);
      assert.equal(p.y,track.points[0].y_reference_px+20*p.frame);
    });
    assert.equal(m.tracks[0].observed.length,index>=3?2:1);
    assert.equal(m.tracks[0].predictions.length,0);
    const html=renderToStaticMarkup(createElement(T08Overlay,{model:m,scale:1,selected:track.track_id,currentFrame:index,
      select:()=>{},showAllTracks:false,visibility:{detections:true,tracks:true,predictions:true}}));
    assert.equal((html.match(/data-estimated-frame=/g)??[]).length,Math.min(index,2));
    if (index>=3) {
      assert.doesNotMatch(html,/class="t08-observed-segment"/);
      assert.equal((html.match(/data-estimated-from-frame=/g)??[]).length,3);
      assert.match(html,/F2 est\./); assert.match(html,/F3 est\./);
    }
  }
  assert.deepEqual(s.result,before);
  const estimates=uploadOverlay(s.result,s.frames[2],2,s.manifest,s.diagnostics,'original',true).tracks[0].estimated;
  later.x_reference_px+=100; later.y_reference_px+=100;
  assert.deepEqual(uploadOverlay(s.result,s.frames[2],2,s.manifest,s.diagnostics,'original',true).tracks[0].estimated,estimates);
  assert.deepEqual(uploadOverlay(s.result,s.frames[4],4,s.manifest,s.diagnostics,'original',false).tracks[0].estimated,[]);
  assert.deepEqual(uploadOverlay(s.result,s.frames[4],4,s.manifest,s.diagnostics,'registered',true).tracks[0].estimated,[]);
});
test('selected track and owning box match; forecast is contrasting, dashed and hollow', () => {
  const html = render(), colors = trackColors('track-A');
  assert.notEqual(colors.observed, colors.forecast);
  assert.match(html, /t08-track is-selected/);
  assert.match(html, /opacity:0.5/); assert.match(html, /opacity:1/);
  assert.ok(html.includes(`stroke:${colors.observed}`)); assert.ok(html.includes(`stroke:${colors.forecast}`));
  assert.match(html, /stroke-dasharray="5 4"/); assert.match(html, /class="predicted-point"[^>]*fill="none"/);
  assert.match(html, new RegExp(`data-observed-frame="0" style="fill:${colors.observed}`));
  assert.match(html, new RegExp(`class="predicted-point"[^>]*stroke:${colors.forecast}`));
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
