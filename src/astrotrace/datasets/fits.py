"""T18 local primary-image inspection and bounded native FITS cutouts.

Optional Astropy is imported lazily. No downloads, resizing, intensity stretching,
WCS inference, filename-derived timing or public upload integration occur here.
"""

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import warnings

import numpy as np

from .archive import DatasetError

_BLOCK = 2880
_DTYPES = {8: 'u1', 16: '>i2', 32: '>i4', 64: '>i8', -32: '>f4', -64: '>f8'}
_UNIQUE = {'SIMPLE', 'BITPIX', 'NAXIS', 'NAXIS1', 'NAXIS2', 'BSCALE',
           'BZERO', 'BLANK', 'DATE-OBS', 'TIMESYS', 'EXPTIME', 'GROUPS', 'PCOUNT', 'GCOUNT'}


def _astropy_fits():
    try:
        from astropy.io import fits
    except ImportError as exc:
        raise DatasetError('FITS inspection requires the optional Astropy astronomy dependency') from exc
    return fits


def _header(stream, max_header_bytes):
    if type(max_header_bytes) is not int or not _BLOCK <= max_header_bytes <= 1024 * 1024:
        raise DatasetError('Header budget must be an integer in 2880..1048576 bytes')
    blocks = []
    for _ in range(max_header_bytes // _BLOCK):
        block = stream.read(_BLOCK)
        if len(block) != _BLOCK:
            raise DatasetError('Truncated FITS header')
        blocks.append(block)
        for offset in range(0, _BLOCK, 80):
            if block[offset:offset+80] == b'END' + b' ' * 77:
                encoded = b''.join(blocks)
                try:
                    text = encoded.decode('ascii')
                    with warnings.catch_warnings():
                        warnings.simplefilter('error')
                        header = _astropy_fits().Header.fromstring(text, sep='')
                        for card in header.cards:
                            _ = card.value
                except (ValueError, UnicodeError, Warning) as exc:
                    raise DatasetError(f'Invalid FITS header: {exc}') from exc
                for key in _UNIQUE:
                    if key in header and header.count(key) > 1:
                        raise DatasetError(f'Ambiguous duplicate FITS keyword: {key}')
                return header, encoded
    raise DatasetError('FITS header exceeds declared budget or has no END card')


def _inspect(stream, path, max_header_bytes):
    if path.suffix.lower() not in ('.fits', '.fit', '.fts'):
        raise DatasetError('Only local uncompressed .fits/.fit/.fts primary images are supported')
    header, encoded = _header(stream, max_header_bytes)
    if header.get('SIMPLE') is not True or header.get('GROUPS', False) is not False:
        raise DatasetError('Expected a standard primary image, not random groups')
    if type(header.get('NAXIS')) is not int or header['NAXIS'] != 2:
        raise DatasetError('Only two-dimensional primary FITS images are supported')
    if header.get('PCOUNT', 0) != 0 or header.get('GCOUNT', 1) != 1:
        raise DatasetError('Unsupported primary-image group parameters')
    bitpix = header.get('BITPIX')
    if type(bitpix) is not int or bitpix not in _DTYPES:
        raise DatasetError('Unsupported FITS BITPIX')
    width, height = header.get('NAXIS1'), header.get('NAXIS2')
    if any(type(n) is not int or not 1 <= n <= 1_000_000 for n in (width, height)):
        raise DatasetError('Invalid or excessive FITS axis dimensions')
    scale, zero = header.get('BSCALE', 1), header.get('BZERO', 0)
    for key, value in [('BSCALE', scale), ('BZERO', zero)]:
        if type(value) not in (int, float) or not math.isfinite(value):
            raise DatasetError(f'{key} must be finite numeric')
    if scale == 0:
        raise DatasetError('BSCALE must be nonzero')
    for key in ('DATE-OBS', 'TIMESYS', 'INSTRUME'):
        if key in header and not isinstance(header[key], str):
            raise DatasetError(f'{key} must be a string when supplied')
    if 'EXPTIME' in header and (type(header['EXPTIME']) not in (int, float)
            or not math.isfinite(header['EXPTIME']) or header['EXPTIME'] < 0):
        raise DatasetError('EXPTIME must be finite nonnegative seconds')
    if 'BLANK' in header and (bitpix < 0 or type(header['BLANK']) is not int
            or not np.iinfo(np.dtype(_DTYPES[bitpix])).min <= header['BLANK'] <= np.iinfo(np.dtype(_DTYPES[bitpix])).max):
        raise DatasetError('BLANK must be a valid storage integer')
    data_bytes = width * height * abs(bitpix) // 8
    size = path.stat().st_size
    if size < len(encoded) + ((_BLOCK-1+data_bytes)//_BLOCK)*_BLOCK:
        raise DatasetError('Truncated FITS primary data or missing block padding')
    return header, {
        'width_px': width, 'height_px': height, 'pixel_count': width*height,
        'storage_bitpix': bitpix, 'storage_dtype': _DTYPES[bitpix],
        'bscale': scale, 'bzero': zero, 'header_bytes': len(encoded),
        'primary_data_bytes': data_bytes, 'file_bytes': size,
        'header_sha256': hashlib.sha256(encoded).hexdigest(),
        'date_obs': header.get('DATE-OBS'), 'date_obs_comment': header.comments['DATE-OBS'] if 'DATE-OBS' in header else None,
        'timesys': header.get('TIMESYS'), 'exposure_s': header.get('EXPTIME'),
        'timestamp_s': None, 'timestamp_policy': 'header values preserved; absolute epoch/time scale not inferred',
        'instrument': header.get('INSTRUME'), 'coordinate_convention': 'array[y,x]; no flip or WCS transform',
        'supports_full_pipeline_frame': width*height <= 4_000_000,
    }


def inspect_fits(path, *, max_header_bytes=184320):
    """Read bounded primary header only; return native dimensions and timing metadata.

    Local path only. Reject invalid, ambiguous, compressed, truncated, cube or
    unsupported inputs. Payload pixels and extensions are not decoded.
    """
    path = Path(path)
    try:
        with path.open('rb') as stream:
            _, metadata = _inspect(stream, path, max_header_bytes)
        return metadata
    except OSError as exc:
        raise DatasetError(f'Cannot inspect local FITS file: {exc}') from exc


@dataclass(frozen=True)
class FitsCutout:
    pixels: np.ndarray
    region_xyxy: tuple[int, int, int, int]
    metadata: dict

    @property
    def origin_xy(self):
        """Add this offset to local cutout coordinates to recover native array pixels."""
        return self.region_xyxy[:2]


def load_fits_cutout(path, *, region=None, max_pixels=4_000_000, max_header_bytes=184320):
    """Return a read-only native/scaled NumPy image and explicit native ROI origin.

    region is integer (x0,y0,x1,y1), upper bounds exclusive, no automatic crop.
    Full image is allowed only within max_pixels. Astropy section reads avoid
    allocating the full image and honor FITS BSCALE/BZERO, including uint16.
    BLANK/nonfinite pixels are rejected, never silently filled. Generic signed
    or scaled FITS output may require an explicit downstream normalization policy.
    """
    if type(max_pixels) is not int or not 1 <= max_pixels <= 4_000_000:
        raise DatasetError('Pixel budget must be an integer in 1..4000000')
    path = Path(path)
    try:
        with path.open('rb') as stream:
            header, metadata = _inspect(stream, path, max_header_bytes)
            width, height = metadata['width_px'], metadata['height_px']
            if region is None:
                region = (0, 0, width, height)
            if (not isinstance(region, (tuple, list)) or len(region) != 4
                    or any(type(n) is not int for n in region)):
                raise DatasetError('Region must contain four integer pixel bounds')
            x0, y0, x1, y1 = region
            if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
                raise DatasetError('Cutout bounds lie outside the native image')
            if (x1-x0)*(y1-y0) > max_pixels:
                raise DatasetError('Requested FITS image/cutout exceeds declared pixel budget')
            stream.seek(0)
            with _astropy_fits().open(stream, mode='readonly', memmap=False,
                                     lazy_load_hdus=True, do_not_scale_image_data=True) as hdus:
                stored = hdus[0].section[y0:y1, x0:x1]
                if 'BLANK' in header and np.issubdtype(stored.dtype, np.integer):
                    if np.any(stored == header['BLANK']):
                        raise DatasetError('FITS cutout contains undefined BLANK pixels')
                # Convert only this bounded section; preserve ordinary unsigned16
                # exactly rather than floating normalization or contrast stretching.
                scale, zero = metadata['bscale'], metadata['bzero']
                if metadata['storage_bitpix'] == 16 and scale == 1 and zero == 32768:
                    pixels = (stored.astype(np.int32)+32768).astype(np.uint16)
                elif scale == 1 and zero == 0:
                    pixels = np.array(stored, dtype=stored.dtype.newbyteorder('='), copy=True)
                else:
                    with np.errstate(over='ignore', invalid='ignore'):
                        pixels = stored.astype(np.float64)*scale+zero
            if pixels.shape != (y1-y0, x1-x0) or not np.isfinite(pixels).all():
                raise DatasetError('FITS cutout has invalid dimensions or nonfinite pixels')
            pixels.setflags(write=False)
            return FitsCutout(pixels, tuple(region), metadata)
    except (OSError, ValueError, OverflowError) as exc:
        if isinstance(exc, DatasetError):
            raise
        raise DatasetError(f'Cannot decode bounded FITS cutout: {exc}') from exc
