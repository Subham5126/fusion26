"""Authored registration scenes; known camera and independent target motion.

No ESA pixels, no benchmark realism claim. Truth is returned separately, never
passed to registration. Each frame is rendered analytically before quantization.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RegistrationFixture:
    frames: tuple[np.ndarray, ...]
    camera_shifts_xy: np.ndarray
    target_raw_xy: np.ndarray
    target_reference_xy: np.ndarray
    background_reference_xy: np.ndarray


def create_registration_fixture(*, seed=13, streaks=False, noise_sigma=1.0, isolated_target=False,
                                shifts=None, size=(256, 192)):
    """Five uint8 frames, top-left xy centers, independently moving compact target.

    size=(width,height); default camera shifts contain both axes/signs/subpixels.
    Positive shift means background content moves right/down in the raw image;
    the correct raw-to-reference matrix has the NEGATIVE shift. Optional streaks
    use a fixed 12px diagonal trail on every star; no rotating camera is simulated.
    """
    width, height = size
    rng = np.random.default_rng(seed)
    shifts = np.asarray([(0., 0.), (3.25, -2.5), (6., -4.), (-2.5, 3.75), (1.5, 6.25)]
                        if shifts is None else shifts, dtype=np.float64)
    if shifts.shape != (5, 2) or not np.isfinite(shifts).all() or np.any(shifts[0]):
        raise ValueError("Five finite shifts required, starting at zero")
    stars = np.column_stack((rng.uniform(28, width-28, 65), rng.uniform(28, height-28, 65)))
    target_ref = np.asarray([(48.25+3*i, 80.75+1.5*i) for i in range(5)])
    if isolated_target:
        # Controlled easy integration fixture, explicitly distinct from crowded
        # scenes: reserve a 22px corridor around the true target path at rendering.
        distances = np.linalg.norm(stars[:, None]-target_ref[None], axis=2)
        stars = stars[distances.min(axis=1) > 22]
    amplitudes = rng.uniform(50, 150, len(stars))
    yy, xx = np.mgrid[:height, :width]
    target_raw = target_ref + shifts
    frames = []
    for index, shift in enumerate(shifts):
        image = 22.+.015*xx+.008*yy+rng.normal(0, noise_sigma, (height, width))
        offsets = np.linspace(-6, 6, 13) if streaks else [0.]
        for (x, y), amplitude in zip(stars+shift, amplitudes):
            for offset in offsets:
                image += amplitude/len(offsets)*np.exp(-.5*((xx-x-offset)**2+(yy-y-offset*.35)**2)/1.3**2)
        tx, ty = target_raw[index]
        image += 160*np.exp(-.5*((xx-tx)**2+(yy-ty)**2)/1.15**2)
        pixels = np.rint(np.clip(image, 0, 255)).astype(np.uint8)
        pixels.setflags(write=False)
        frames.append(pixels)
    for points in (shifts, target_raw, target_ref, stars):
        points.setflags(write=False)
    return RegistrationFixture(tuple(frames), shifts, target_raw, target_ref, stars)
