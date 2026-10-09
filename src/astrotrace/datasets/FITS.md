# T18 local FITS inspection and native cutouts

This optional internal helper inspects uncompressed two-dimensional **primary**
FITS images. It does not add an API route, acquisition profile or pipeline option.
Astropy is the existing optional `astronomy` dependency; this task tested 8.0.1
(BSD-3-Clause) in a separate Python 3.12 environment. Root locks and metadata are
unchanged. Astropy imports lazily; a missing dependency raises DatasetError with
an actionable message rather than breaking ordinary spotGEO imports.

```python
from astrotrace.datasets.fits import inspect_fits, load_fits_cutout

path = r'E:\Fusion\data\raw\frigate\raw\Capture_00001 02_55_24Z.fits'
metadata = inspect_fits(path)
image = load_fits_cutout(path, region=(4544, 2955, 5056, 3467))
assert image.pixels.shape == (512, 512)
assert image.pixels.dtype.name == 'uint16'
# Integer array coordinates, not a physical or sky-coordinate transformation:
x_native, y_native = 10.25 + image.origin_xy[0], 20.5 + image.origin_xy[1]
```

`inspect_fits(path, *, max_header_bytes=184320) -> dict` reads primary header
blocks only. Reports native dimensions, storage type, scaling, exposure,
DATE-OBS/TIMESYS strings, instrument, header SHA-256 and file/primary sizes.
Default header budget is 64 FITS blocks (2880 bytes each), maximum 1 MiB.
It rejects absent END, truncated header/data/padding, non-ASCII/invalid or
duplicate structural/timing cards, random groups, cubes and unsupported axes.
Metadata inspection does not claim all payload pixels decode or HDU extensions
validate. Supplied string metadata is preserved, not interpreted as calibration.

`load_fits_cutout(path, *, region=None, max_pixels=4000000,
max_header_bytes=184320) -> FitsCutout` returns a read-only NumPy array,
exclusive-upper native `(x0,y0,x1,y1)` region and source metadata. No automatic
crop, resize, vertical flip, contrast stretch or coordinate shift occurs. With
region=None it requests the full image and fails before pixel decoding if its
size exceeds the declared budget. An explicit crop is a separate coordinate
frame: add `origin_xy` to recover original array pixels; do not present local ROI
coordinates as full-frame measurements. NumPy indexing is `[y,x]`; no WCS or sky
orientation is asserted.

Uses a bounded Astropy `.section` read and applies the original BSCALE/BZERO to
that section only. BITPIX16 / BSCALE1 / BZERO32768 becomes **exact uint16**,
including 0 and 65535. Unscaled types retain native precision and host byte
order. Other linear scaling returns float64 and has ordinary float64 precision
limits. Signed/scaled data needs an explicitly reviewed normalization policy
before the existing normalized-grayscale detector can consume it. BLANK and
nonfinite cutout pixels raise DatasetError; they are never filled or declared
valid. Compressed files, tables/extensions and calibrated FITS/WCS processing
are outside this small helper's support.

Timing: the local files have DATE-OBS describing an **estimated system-clock
frame start** and EXPTIME0.5s; none declares TIMESYS. The original seven-digit
fraction is retained. `timestamp_s` stays null; no epoch, time scale, cadence,
timezone or physical velocity is fabricated from filenames or exposure alone.
Integration must verify acquisition timing before computing px/s or physical
motion. Optical-looking header values are insufficient to establish astrometry.

Actual local inspection: 2,000 raw 9600x6422 FITS headers, signed16 storage with
unsigned16 offset; three fixed512x512 cutouts decoded and checked against
Astropy's independently scaled sections. Full frames exceed schema0.1.0's
4,000,000-pixel limit. Their source files were SHA-256-identical before/after.
Local 1..99.9-percentile preview PNGs are labeled **display only**; saved `.npy`
and native16 PNG preserve decoded values. No image or dataset is in Git.

Frigate provenance/rights and label completeness are not established by the
local folder. The referenced DOI is
https://doi.org/10.6084/m9.figshare.29545667; do not infer authorization to
redistribute these files from their local availability. Member1 must review
source provenance, tiling/scaling, crop coordinate transport and supported
acquisition profile before API adoption. No shared-schema change is proposed.

Implementation references (original helper code, no borrowed implementation):
[NASA FITS standard](https://fits.gsfc.nasa.gov/fits_standard.html),
[Astropy image storage/scaling](https://docs.astropy.org/en/stable/io/fits/usage/image.html#scaled-data),
[bounded image sections](https://docs.astropy.org/en/stable/io/fits/usage/image.html#data-sections).
