import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { alignmentAvailable, currentDetections, displayPoint, trackColors, transformPoint, visibleTrack, zoomAt } from '../src/visualization/overlay.ts';
import { parseRegistration, parseResult } from '../src/visualization/input.ts';

const root = new URL('../../', import.meta.url);
const load = path => JSON.parse(readFileSync(new URL(path, root), 'utf8'));
const fixture = load('tests/contracts/fixtures/track-result.json');
const frame = (frameIndex, referenceToRaw) => ({ frameIndex, width: 640, height: 480, imageUrl: 'test.png', referenceToRaw });
const identity = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
const translate = [[1, 0, 25], [0, 1, -12], [0, 0, 1]];

test('uses actual Detection IDs to assign current boxes; no stale detections', () => {
  const current = currentDetections(fixture, 1);
  assert.equal(current.length, 1);
  assert.equal(current[0].track.track_id, fixture.tracks[0].track_id);
  assert.equal(current[0].detection.frame_index, 1);
  assert.deepEqual(currentDetections(fixture, 99), []);
});
test('unassociated detections stay candidates instead of fabricated tracks', () => {
  const result = structuredClone(fixture); result.tracks = [];
  assert.equal(currentDetections(result, 0)[0].track, undefined);
});
test('scrubbing the past never reveals later observations or fitted future', () => {
  const view = visibleTrack(fixture.tracks[0], fixture, frame(0));
  assert.equal(view.observed.length, 1); assert.deepEqual(view.forecast, []);
});
test('final frame exposes backend forecast strictly after the last actual observation', () => {
  const track = fixture.tracks[0];
  const view = visibleTrack(track, fixture, frame(2));
  assert.equal(view.observed.length, 3);
  assert.equal(view.forecast.length, track.trajectory.predictions.length);
  assert.ok(view.forecast.every(p => p.point.frame_index > 2));
  assert.deepEqual(view.forecast.map(p => p.xy.x), track.trajectory.predictions.map(p => p.x_reference_px));
});
test('interpolated points never become observed dots or forecast anchors', () => {
  const track = structuredClone(fixture.tracks[0]);
  track.points.splice(1, 0, { ...track.points[0], frame_index: 1, point_type: 'interpolated', detection_id: null });
  assert.equal(visibleTrack(track, fixture, frame(2)).observed.length, 3);
});
test('missed current frame has a path but no current bounding box', () => {
  const result = structuredClone(fixture);
  result.detections = result.detections.filter(d => d.frame_index !== 1);
  result.tracks[0].points = result.tracks[0].points.filter(p => p.frame_index !== 1);
  assert.deepEqual(currentDetections(result, 1), []);
  assert.equal(visibleTrack(result.tracks[0], result, frame(1)).observed.length, 1);
});
test('camera motion uses current reference-to-raw transform for the entire history and forecast', () => {
  const result = structuredClone(fixture); result.registration.status = 'estimated';
  const view = visibleTrack(result.tracks[0], result, frame(2, translate));
  assert.equal(view.observed[0].xy.x, result.tracks[0].points[0].x_reference_px + 25);
  assert.equal(view.forecast[0].xy.y, result.tracks[0].trajectory.predictions[0].y_reference_px - 12);
});
test('missing estimated transform hides unsafe reference overlays on native frames', () => {
  const result = structuredClone(fixture); result.registration.status = 'estimated';
  assert.equal(alignmentAvailable(result, frame(2)), false);
  assert.ok(visibleTrack(result.tracks[0], result, frame(2)).observed.every(p => p.xy === null));
  assert.equal(currentDetections(result, 2).length, 1);
  assert.equal(alignmentAvailable(result, frame(0)), true);
});
test('homogeneous transform supports translation, perspective and invalid denominator', () => {
  assert.deepEqual(transformPoint({ x: 639, y: 479 }, identity), { x: 639, y: 479 });
  assert.deepEqual(transformPoint({ x: 10, y: 20 }, translate), { x: 35, y: 8 });
  assert.deepEqual(transformPoint({ x: 10, y: 20 }, [[1,0,0],[0,1,0],[0,0,2]]), { x: 5, y: 10 });
  assert.equal(transformPoint({ x: 10, y: 20 }, [[1,0,0],[0,1,0],[0,0,0]]), null);
});
test('out-of-field coordinates stay geometrically true, for SVG clipping', () => {
  const point = { ...fixture.tracks[0].points[0], x_reference_px: 670, y_reference_px: -10 };
  assert.deepEqual(displayPoint(point, fixture, frame(0)), { x: 670, y: -10 });
});
test('raw coordinate results do not apply a reference transform a second time', () => {
  const result = structuredClone(fixture); result.coordinate_frame = 'raw';
  const point = fixture.tracks[0].points[0];
  assert.deepEqual(displayPoint(point, result, frame(0, translate)), { x: point.x_reference_px, y: point.y_reference_px });
});
test('a malformed forecast inside the observed interval is never drawn', () => {
  const track = structuredClone(fixture.tracks[0]);
  track.trajectory.predictions.push({ ...track.trajectory.predictions[0], frame_index: 1 });
  assert.ok(visibleTrack(track, fixture, frame(2)).forecast.every(p => p.point.frame_index > 2));
});
test('zoom preserves anchor screen position and clamps scale to 1–8', () => {
  const before = { x: 37, y: -12, zoom: 2 }, anchor = { x: 210, y: 170 };
  const after = zoomAt(before, anchor, 4);
  assert.equal((anchor.x - before.x) * before.zoom, (anchor.x - after.x) * after.zoom);
  assert.equal((anchor.y - before.y) * before.zoom, (anchor.y - after.y) * after.zoom);
  assert.equal(zoomAt(before, anchor, 50).zoom, 8);
  assert.equal(zoomAt(before, anchor, .01).zoom, 1);
});
test('track palette is persistent across result ordering, and forecast contrasts', () => {
  for (const id of ['track-0001', 'track-0002', 'track-0003', 'track-0004', 'track-0005']) {
    assert.deepEqual(trackColors(id), trackColors(id));
    assert.notEqual(trackColors(id).observed, trackColors(id).forecast);
  }
});
test('empty results and tracks without trajectories draw no invented geometry', () => {
  assert.deepEqual(currentDetections(load('tests/contracts/fixtures/empty-result.json'), 0), []);
  const track = structuredClone(fixture.tracks[0]); track.points = []; track.trajectory = null;
  assert.deepEqual(visibleTrack(track, fixture, frame(4)), { observed: [], forecast: [] });
});
test('local rendering guard accepts contract fixture and rejects nonfinite or invalid boxes', () => {
  assert.equal(parseResult(fixture), fixture);
  const result = structuredClone(fixture); result.detections[0].bbox_raw_px[2] = result.detections[0].bbox_raw_px[0];
  assert.throws(() => parseResult(result), /bounding box/);
  const nonfinite = structuredClone(fixture); nonfinite.tracks[0].points[0].x_reference_px = Infinity;
  assert.throws(() => parseResult(nonfinite), /finite/);
});
test('T13 report uses inverse direction, skips failed frames, rejects singular transforms', () => {
  const report = { coordinate_frame: 'reference_frame_0', transform_direction: 'raw_to_reference', frames: [
    { frame_index: 0, status: 'identity', reference_to_raw: identity },
    { frame_index: 1, status: 'estimated', reference_to_raw: translate },
    { frame_index: 2, status: 'failed', reference_to_raw: null },
  ] };
  assert.deepEqual(parseRegistration(report).get(1), translate); assert.equal(parseRegistration(report).size, 2);
  report.frames[1].reference_to_raw = [[0,0,0],[0,0,0],[0,0,0]];
  assert.throws(() => parseRegistration(report), /Singular/);
});

for (const sequence of ['counts_change', 'train_84']) {
  const folder = `artifacts/reports/cv_readiness/final/${sequence}/`;
  const path = new URL(`${folder}tracking_registered.json`, root);
  test(`actual saved backend result: ${sequence} (optional local artifacts)`, { skip: !existsSync(fileURLToPath(path)) }, () => {
    const result = parseResult(load(`${folder}tracking_registered.json`));
    const report = load(`${folder}registration.json`);
    const transforms = parseRegistration(report);
    for (let frameIndex = 0; frameIndex < 5; frameIndex++) {
      const current = { ...frame(frameIndex, transforms.get(frameIndex)), width: report.width_px, height: report.height_px };
      assert.ok(alignmentAvailable(result, current));
      assert.equal(currentDetections(result, frameIndex).length, result.detections.filter(d => d.frame_index === frameIndex).length);
      for (const track of result.tracks) {
        const view = visibleTrack(track, result, current);
        for (const item of [...view.observed, ...view.forecast]) {
          assert.ok(item.xy && Number.isFinite(item.xy.x) && Number.isFinite(item.xy.y));
          if (item.point.point_type === 'observed' && item.point.frame_index === frameIndex) {
            const detection = result.detections.find(d => d.detection_id === item.point.detection_id);
            assert.ok(detection);
            assert.ok(Math.abs(item.xy.x - detection.x_raw_px) < 1e-6, 'current observed dot matches native detection x');
            assert.ok(Math.abs(item.xy.y - detection.y_raw_px) < 1e-6, 'current observed dot matches native detection y');
          }
        }
      }
    }
  });
}
