# PNG preprocessing boundary

`images.py` contains strict image decoding and a separate display utility.
See [dataset guide](../datasets/README.md) for executable environment/CLI commands.

`decode_png(bytes, expected_size=(640,480), max_pixels=4_000_000)` returns a
read-only 2D uint8/uint16 NumPy array with shape `(height,width)`. It preserves
native intensities, checks dimensions before allocation and rejects corrupt,
non-PNG, animated, RGB/palette or oversized data with ValueError. Pass
`expected_size=None` only for deliberate bounded alternate data, or `(64,48)`
for the supplied authored fixtures. Upstream loading bounds file bytes.

`display_uint8(array)` returns a new viewing array after min/max contrast scaling;
constant images retain intensity (uint16 is scaled by 257). It does not mutate
source pixels. Do not feed these per-frame display values into a scientific
detector without a separately declared preprocessing configuration.

```python
from astrotrace.preprocessing.images import decode_png, display_uint8
pixels = decode_png(png_bytes)  # bytes from an explicitly bounded source
preview = display_uint8(pixels)
```

`candidates.py` adds separately declared scientific preprocessing for the
[T03 baseline](../detection/README.md): dtype-range float normalization, mild
Gaussian denoising, broad background subtraction and a compact-source difference
response with clipped local RMS/global MAD noise. It preserves the native grid;
there is no display min/max stretching or temporal median.

`normalize_grayscale(pixels)` returns a new float32 [0,1] array and quantization
step. uint8/uint16 or finite normalized float32/64 inputs are supported; other
types, empty/color/nonfinite/out-of-range or >4,000,000-pixel arrays raise ValueError.
`robust_sigma(values,floor)` returns a MAD scale with a zero-noise floor.
`enhance_compact(image, denoise_sigma=..., background_sigma=..., noise_sigma=...,
quantization=...)` returns CandidateImage(response,noise,global_noise). Parameters
come from validated BaselineConfig; formulas and limitations are in the detector
guide. Defaults can miss broader streaks or respond to star fragments.

No registration or geometric transform is implemented. Coordinates remain native
top-left `(x,y)`, with NumPy indexing `[y,x]`. Tracking receives actual detector
outputs with separately reviewed image-derived registration, not this display
image. Targeted verification:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -c backend/pyproject.toml tests/detection
```
