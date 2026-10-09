"""T18 pixel fidelity, bounded decoding, origin and explicit invalid-data failures."""
import hashlib
from pathlib import Path

import numpy as np
import pytest

fits = pytest.importorskip('astropy.io.fits', reason='T18 uses the existing optional astronomy dependency')

from astrotrace.datasets.archive import DatasetError
from astrotrace.datasets.fits import inspect_fits, load_fits_cutout


def write(tmp_path, pixels, **metadata):
    path = tmp_path/'sample.fits'
    fits.PrimaryHDU(pixels, header=fits.Header(metadata)).writeto(path)
    return path


def test_uint16_signed_storage_offset_native_origin_and_source_preserved(tmp_path):
    pixels = np.arange(12*17, dtype=np.uint16).reshape(12,17)*300
    pixels[4,6] = 65535
    path = write(tmp_path, pixels, **{'DATE-OBS':'2024-04-02T02:55:24.3834903', 'EXPTIME':.5})
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    info = inspect_fits(path)
    assert (info['width_px'],info['height_px'],info['storage_bitpix']) == (17,12,16)
    assert info['bzero'] == 32768 and info['bscale'] == 1
    assert info['date_obs'] == '2024-04-02T02:55:24.3834903'
    assert info['timestamp_s'] is None and info['timesys'] is None
    cutout = load_fits_cutout(path,region=(5,3,11,8))
    np.testing.assert_array_equal(cutout.pixels,pixels[3:8,5:11])
    assert cutout.pixels.dtype == np.uint16 and not cutout.pixels.flags.writeable
    assert cutout.origin_xy == (5,3) and cutout.region_xyxy == (5,3,11,8)
    assert int(cutout.pixels[1,1]) == 65535
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


@pytest.mark.parametrize('dtype',[np.uint8,np.int16,np.int32,np.int64,np.float32,np.float64])
def test_native_unscaled_types_no_flip_or_resize(tmp_path,dtype):
    pixels = np.arange(35,dtype=dtype).reshape(5,7)
    image = load_fits_cutout(write(tmp_path,pixels))
    np.testing.assert_array_equal(image.pixels,pixels)
    assert image.pixels.dtype == pixels.dtype and image.origin_xy == (0,0)
    assert image.metadata['date_obs'] is None


def test_generic_scaling_follows_header_without_stretching(tmp_path):
    pixels = np.arange(35,dtype=np.int16).reshape(5,7)
    path = write(tmp_path,pixels)
    with fits.open(path,mode='update',do_not_scale_image_data=True) as hdus:
        hdus[0].header['BSCALE'] = .5
        hdus[0].header['BZERO'] = 100
    np.testing.assert_array_equal(load_fits_cutout(path).pixels,pixels*.5+100)


def test_header_inspection_and_oversize_rejection_never_open_pixel_decoder(tmp_path,monkeypatch):
    path = write(tmp_path,np.zeros((100,120),np.uint16))
    def forbidden(*args,**kwargs):
        pytest.fail('Decoder opened despite header-only inspection or rejected budget')
    monkeypatch.setattr(fits,'open',forbidden)
    assert inspect_fits(path)['pixel_count'] == 12000
    with pytest.raises(DatasetError,match='pixel budget'):
        load_fits_cutout(path,max_pixels=100)


@pytest.mark.parametrize('region',[(0,0,0,5),(-1,0,4,4),(0,0,8,6),(True,0,2,2),(0.,0,2,2),'auto',[0,0,1]])
def test_invalid_region_rejected(tmp_path,region):
    with pytest.raises(DatasetError):
        load_fits_cutout(write(tmp_path,np.zeros((5,7),np.uint8)),region=region)


@pytest.mark.parametrize('budget',[True,0,-1,4_000_001,float('inf')])
def test_invalid_pixel_budget_rejected(tmp_path,budget):
    with pytest.raises(DatasetError):
        load_fits_cutout(write(tmp_path,np.zeros((5,7),np.uint8)),max_pixels=budget)


def test_nonfinite_and_blank_pixels_fail_without_filling(tmp_path):
    pixels=np.ones((5,7),np.float32)
    pixels[2,3]=np.nan
    path=write(tmp_path,pixels)
    with pytest.raises(DatasetError,match='nonfinite'):
        load_fits_cutout(path)
    path.unlink()
    path=write(tmp_path,np.zeros((5,7),np.int16),BLANK=0)
    with pytest.raises(DatasetError,match='BLANK'):
        load_fits_cutout(path)


def test_truncated_missing_end_and_cube_rejected(tmp_path):
    path=write(tmp_path,np.zeros((5,7),np.uint16))
    payload=path.read_bytes()
    path.write_bytes(payload[:2900])
    with pytest.raises(DatasetError,match='Truncated'):
        inspect_fits(path)
    path.write_bytes(b'SIMPLE  =                    T'+b' '*(2880-30))
    with pytest.raises(DatasetError,match='budget|Truncated'):
        inspect_fits(path,max_header_bytes=2880)
    path.unlink()
    path=write(tmp_path,np.zeros((2,5,7),np.uint16))
    with pytest.raises(DatasetError,match='two-dimensional'):
        inspect_fits(path)


def test_ambiguous_structural_header_rejected(tmp_path):
    path=write(tmp_path,np.zeros((5,7),np.int16))
    with fits.open(path,mode='update') as hdus:
        hdus[0].header.append(('BSCALE',1))
        hdus[0].header.append(('BSCALE',2))
    with pytest.raises(DatasetError,match='duplicate'):
        inspect_fits(path)


@pytest.mark.parametrize('key,value',[('BSCALE',0),('EXPTIME',-1),('EXPTIME','unknown'),('DATE-OBS',123),('TIMESYS',False),('BLANK',0.5)])
def test_invalid_scaling_and_metadata_rejected(tmp_path,key,value):
    path=write(tmp_path,np.zeros((5,7),np.int16))
    # Write the malformed card after HDU construction; PrimaryHDU normalizes
    # some scaling cards supplied while constructing a new data-bearing HDU.
    with fits.open(path,mode='update',do_not_scale_image_data=True) as hdus:
        hdus[0].header[key]=value
    with pytest.raises(DatasetError):
        inspect_fits(path)


def test_missing_optional_dependency_has_actionable_error(monkeypatch):
    import builtins
    from astrotrace.datasets.fits import _astropy_fits
    original=builtins.__import__
    def guard(name,*args,**kwargs):
        if name=='astropy.io':
            raise ImportError('Astropy unavailable')
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',guard)
    with pytest.raises(DatasetError,match='optional Astropy'):
        _astropy_fits()
