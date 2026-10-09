import type { FrameInput } from '../types/contracts';
import type { Size } from './geometry';

export const localLimits = { minFrames: 3, maxFrames: 30, fileBytes: 10 * 1024 * 1024,
  totalBytes: 50 * 1024 * 1024, pixels: 4_000_000 } as const;
export interface ImageHeader extends Size { format: 'image/png' | 'image/jpeg'; orientation: number }
// Local state is deliberately not a public SequenceInput: a blob URL is not a server image_ref.
export interface ViewerFrame extends Pick<FrameInput, 'width_px' | 'height_px' | 'timestamp_s'> {
  id: string; file?: Pick<File, 'name'>; label?: string; url: string; header: ImageHeader;
}
export interface LocalFrame extends ViewerFrame { file: File }
export interface ImageResources {
  createUrl: (file: File) => string;
  revokeUrl: (url: string) => void;
  decode: (url: string, signal: AbortSignal) => Promise<Size>;
}

function exifOrientation(bytes: Uint8Array): number {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (bytes.length < 8) return 1;
  const little = bytes[0] === 0x49 && bytes[1] === 0x49;
  if (!little && !(bytes[0] === 0x4d && bytes[1] === 0x4d)) return 1;
  if (view.getUint16(2, little) !== 42) return 1;
  const offset = view.getUint32(4, little);
  if (offset + 2 > bytes.length) throw new Error('Invalid EXIF metadata.');
  const count = view.getUint16(offset, little);
  if (offset + 2 + count * 12 > bytes.length) throw new Error('Truncated EXIF metadata.');
  for (let i = 0; i < count; i++) {
    const at = offset + 2 + i * 12;
    if (view.getUint16(at, little) === 0x112) {
      if (view.getUint16(at + 2, little) !== 3 || view.getUint32(at + 4, little) !== 1) throw new Error('Invalid image orientation.');
      const orientation = view.getUint16(at + 8, little);
      if (orientation < 1 || orientation > 8) throw new Error('Invalid image orientation.');
      return orientation;
    }
  }
  return 1;
}

export function readImageHeader(bytes: Uint8Array): ImageHeader {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let width = 0, height = 0, orientation = 1;
  let format: ImageHeader['format'];
  if ([137, 80, 78, 71, 13, 10, 26, 10].every((value, index) => bytes[index] === value)) {
    format = 'image/png';
    if (bytes.length < 33 || view.getUint32(8) !== 13 || String.fromCharCode(...bytes.subarray(12, 16)) !== 'IHDR') throw new Error('Invalid PNG header.');
    width = view.getUint32(16); height = view.getUint32(20);
    for (let at = 8; at + 12 <= bytes.length;) {
      const length = view.getUint32(at);
      if (length > bytes.length - at - 12) throw new Error('Truncated PNG image.');
      const tag = String.fromCharCode(...bytes.subarray(at + 4, at + 8));
      if (tag === 'eXIf') orientation = exifOrientation(bytes.subarray(at + 8, at + 8 + length));
      if (tag === 'IEND') break;
      at += length + 12;
    }
  } else if (bytes[0] === 0xff && bytes[1] === 0xd8) {
    format = 'image/jpeg';
    for (let at = 2; at < bytes.length;) {
      if (bytes[at++] !== 0xff) throw new Error('Invalid JPEG header.');
      while (bytes[at] === 0xff) at++;
      const marker = bytes[at++];
      if (marker === 0xda || marker === 0xd9) break;
      if (marker === 0xd8 || marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) continue;
      if (at + 2 > bytes.length) throw new Error('Truncated JPEG image.');
      const length = view.getUint16(at);
      if (length < 2 || at + length > bytes.length) throw new Error('Truncated JPEG image.');
      if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker)) {
        if (length < 8) throw new Error('Invalid JPEG dimensions.');
        height = view.getUint16(at + 3); width = view.getUint16(at + 5);
      }
      if (marker === 0xe1 && String.fromCharCode(...bytes.subarray(at + 2, at + 8)) === 'Exif\0\0') orientation = exifOrientation(bytes.subarray(at + 8, at + length));
      at += length;
    }
  } else throw new Error('Only JPEG and PNG images are supported.');
  if (!width || !height || width * height > localLimits.pixels) throw new Error('Each image must have valid dimensions and at most 4,000,000 pixels.');
  return { width, height, orientation, format };
}

export function validateSelection(files: readonly File[]) {
  if (files.length < localLimits.minFrames || files.length > localLimits.maxFrames) throw new Error('Select 3–30 JPEG or PNG frames together.');
  if (files.reduce((sum, file) => sum + file.size, 0) > localLimits.totalBytes) throw new Error('The sequence exceeds the 50 MiB local preview limit.');
  for (const file of files) {
    if (!/\.(jpe?g|png)$/i.test(file.name) || (file.type && !['image/jpeg', 'image/png'].includes(file.type))) throw new Error(`${file.name}: choose a JPEG or PNG image.`);
    if (!file.size || file.size > localLimits.fileBytes) throw new Error(`${file.name}: files must be nonempty and at most 10 MiB.`);
  }
}

export function releaseFrames(frames: readonly LocalFrame[], resources: Pick<ImageResources, 'revokeUrl'> = browserResources) {
  frames.forEach(frame => resources.revokeUrl(frame.url));
}

export async function prepareLocalFrames(files: readonly File[], signal: AbortSignal,
  resources: ImageResources = browserResources): Promise<LocalFrame[]> {
  validateSelection(files);
  const frames: LocalFrame[] = [], urls: string[] = [];
  try {
    for (const file of files) {
      signal.throwIfAborted();
      try {
        const header = readImageHeader(new Uint8Array(await file.arrayBuffer()));
        signal.throwIfAborted();
        const extensionFormat = /\.png$/i.test(file.name) ? 'image/png' : 'image/jpeg';
        if (header.format !== extensionFormat || (file.type && header.format !== file.type)) throw new Error('File contents do not match its JPEG/PNG format.');
        if (frames.length && (header.width !== frames[0].header.width || header.height !== frames[0].header.height)) throw new Error('All frames must share their original dimensions.');
        const url = resources.createUrl(file); urls.push(url);
        const decoded = await resources.decode(url, signal);
        signal.throwIfAborted();
        const swapped = header.orientation >= 5;
        if (decoded.width !== (swapped ? header.height : header.width) || decoded.height !== (swapped ? header.width : header.height)) throw new Error('Decoded image geometry does not match its metadata.');
        if (frames.length && (decoded.width !== frames[0].width_px || decoded.height !== frames[0].height_px)) throw new Error('All decoded frames must share dimensions and orientation axes.');
        frames.push({ id: url, file, url, header, width_px: decoded.width, height_px: decoded.height, timestamp_s: null });
      } catch (error) {
        if (signal.aborted) throw error;
        throw new Error(`${file.name}: ${error instanceof Error ? error.message : 'Image could not be read.'}`);
      }
    }
    return frames;
  } catch (error) { urls.forEach(resources.revokeUrl); throw error; }
}

export function moveFrame<T>(frames: readonly T[], index: number, direction: -1 | 1): T[] {
  const result = [...frames], target = index + direction;
  if (index >= 0 && index < result.length && target >= 0 && target < result.length) [result[index], result[target]] = [result[target], result[index]];
  return result;
}

export const browserResources: ImageResources = {
  createUrl: file => URL.createObjectURL(file), revokeUrl: url => URL.revokeObjectURL(url),
  decode: (url, signal) => new Promise((resolve, reject) => {
    const image = new Image();
    const finish = (error?: Error) => {
      clearTimeout(timeout); signal.removeEventListener('abort', abort);
      image.onload = null; image.onerror = null;
      if (error) { image.src = ''; reject(error); } else resolve({ width: image.naturalWidth, height: image.naturalHeight });
    };
    const abort = () => finish(new DOMException('Image loading canceled.', 'AbortError'));
    const timeout = setTimeout(() => finish(new Error('Image decoding timed out. Choose a different file.')), 15_000);
    image.onload = () => finish(); image.onerror = () => finish(new Error('Image is corrupt or cannot be decoded by this browser.'));
    signal.addEventListener('abort', abort, { once: true });
    if (signal.aborted) abort(); else image.src = url;
  }),
};
