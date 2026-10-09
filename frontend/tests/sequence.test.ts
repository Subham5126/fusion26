import test from 'node:test';
import assert from 'node:assert/strict';
import { boundedView, fittedView, maxZoom, zoomAt, rawToDecoded, imageTransform } from '../src/viewer/geometry';
import { moveFrame, localLimits, readImageHeader, validateSelection } from '../src/viewer/localSequence';

test('geometry view is bounded correctly', () => {
  const image = { width: 640, height: 480 };
  const viewport = { width: 1280, height: 960 };
  const view = boundedView(image, viewport, { zoom: 20, pan: { x: 1000, y: 1000 } });
  assert.equal(view.zoom, maxZoom); // bounded to maxZoom
  // Pan is bounded within limitX
  assert.equal(view.pan.x, 1000);
});

test('moveFrame reorders sequence correctly', () => {
  const frames = [1, 2, 3];
  assert.deepEqual(moveFrame(frames, 0, 1), [2, 1, 3]);
  assert.deepEqual(moveFrame(frames, 2, -1), [1, 3, 2]);
  // Out of bounds
  assert.deepEqual(moveFrame(frames, 0, -1), [1, 2, 3]);
  assert.deepEqual(moveFrame(frames, 2, 1), [1, 2, 3]);
});

test('zoomAt retains anchor point correctly', () => {
  const image = { width: 100, height: 100 };
  const viewport = { width: 100, height: 100 };
  const anchor = { x: 50, y: 50 };
  const zoomed = zoomAt(image, viewport, fittedView, 2, anchor);
  assert.equal(zoomed.zoom, 2);
  assert.equal(zoomed.pan.x, 0); // anchored at center, pan is 0
});

test('rawToDecoded transforms point based on orientation', () => {
  const raw = { width: 640, height: 480 };
  const pt = { x: 10, y: 20 };
  assert.deepEqual(rawToDecoded(pt, raw, 1), pt);
  assert.deepEqual(rawToDecoded(pt, raw, 3), { x: 639 - 10, y: 479 - 20 });
});

test('readImageHeader parses valid PNG binary header', () => {
  const pngHex = '89504e470d0a1a0a0000000d4948445200000280000001e0080600000035d115250000000b49444154785e636000020000050001e38b30790000000049454e44ae426082';
  const bytes = new Uint8Array(Buffer.from(pngHex, 'hex'));
  const header = readImageHeader(bytes);
  assert.equal(header.format, 'image/png');
  assert.equal(header.width, 640);
  assert.equal(header.height, 480);
  assert.equal(header.orientation, 1);
});

test('readImageHeader rejects unsupported file types', () => {
  const badBytes = new Uint8Array([0x00, 0x01, 0x02, 0x03]);
  assert.throws(() => readImageHeader(badBytes), /Only JPEG and PNG images are supported/);
});

test('validateSelection enforces count limits and valid extensions', () => {
  const createFile = (name: string, size = 1000) => new File([new Uint8Array(size)], name, { type: 'image/png' });

  // Under min count
  const twoFiles = [createFile('1.png'), createFile('2.png')];
  assert.throws(() => validateSelection(twoFiles), /Select 3–30 JPEG or PNG frames together/);

  // Valid count (3 to 30)
  const validFiles = [createFile('1.png'), createFile('2.png'), createFile('3.png')];
  assert.doesNotThrow(() => validateSelection(validFiles));

  // Invalid extension
  const invalidExt = [createFile('1.png'), createFile('2.png'), createFile('3.txt')];
  assert.throws(() => validateSelection(invalidExt), /choose a JPEG or PNG image/);
});
