"""Strict grayscale PNG decoding and display-only scaling; no scientific normalization."""

from io import BytesIO
import warnings

import numpy as np
from PIL import Image, UnidentifiedImageError


def decode_png(payload: bytes, *, max_pixels: int = 4_000_000,
               expected_size: tuple[int, int] | None = (640, 480)) -> np.ndarray:
    """Return untouched read-only uint8/uint16 [row=y, column=x] grayscale pixels.

    Check decoded dimensions before allocation. RGB, palette, animated, non-PNG
    and corrupt files fail. expected_size is (width, height); None permits any
    bounded dimensions for authored fixtures. This is not an HTTP upload guard.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(payload)) as image:
                if image.format != "PNG" or image.mode not in ("L", "I", "I;16", "I;16B", "I;16L"):
                    raise ValueError("Expected a grayscale PNG")
                if getattr(image, "n_frames", 1) != 1:
                    raise ValueError("Animated PNGs are unsupported")
                width, height = image.size
                if width * height > max_pixels:
                    raise ValueError("Decoded image exceeds pixel limit")
                if expected_size is not None and image.size != expected_size:
                    raise ValueError(f"Expected image size {expected_size}, got {image.size}")
                image.load()
                pixels = np.array(image)
                if pixels.dtype != np.uint8:
                    if pixels.min() < 0 or pixels.max() > 65535:
                        raise ValueError("PNG grayscale values exceed uint16 range")
                    pixels = pixels.astype(np.uint16)
                pixels.setflags(write=False)
                return pixels
    except (UnidentifiedImageError, OSError, EOFError, SyntaxError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError(f"Cannot decode PNG: {exc}") from exc


def display_uint8(pixels: np.ndarray) -> np.ndarray:
    """Min/max contrast for viewing only; constant images keep scaled intensity."""
    if pixels.ndim != 2 or pixels.dtype not in (np.dtype("uint8"), np.dtype("uint16")):
        raise ValueError("Expected a 2D uint8/uint16 image")
    lo, hi = int(pixels.min()), int(pixels.max())
    if lo == hi:
        return (pixels / (257 if pixels.dtype == np.uint16 else 1)).astype(np.uint8)
    return np.rint((pixels.astype(np.float64) - lo) * (255.0 / (hi - lo))).astype(np.uint8)
