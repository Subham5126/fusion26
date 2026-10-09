"""Small deterministic rendered stress scenes; truth stays outside inference.

Synthetic image-plane examples are not telescope measurements or training data.
Returns frames and separate evaluation truth. See preprocessing/ROBUSTNESS.md.
"""

from dataclasses import dataclass

import cv2
import numpy as np


CASES = ('counts_change', 'entry_exit', 'crossing', 'nearby', 'camera_motion',
         'artifacts', 'empty_targets', 'registration_failure', 'noise_only', 'daylight_like', 'blurred')


@dataclass(frozen=True)
class StressScene:
    name: str
    frames: tuple[np.ndarray, ...]
    truth: dict


def create_stress_scene(name: str, *, seed: int = 14) -> StressScene:
    """Render five 320x240 uint8 frames with independent objects and translations.

    Truth centers use top-left integer pixel centers, exclusive upper bbox limits.
    Missing renders are explicit visibility=False, never predicted observations.
    """
    if name not in CASES or type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('Expected declared stress case and uint32 seed')
    rng = np.random.default_rng(seed)
    h, w = 240, 320
    yy, xx = np.mgrid[:h, :w]
    background = np.full((h, w), 18., dtype=np.float64)
    # Distributed elongated background stars, deliberately outside target corridor.
    for y in range(28, 220, 24):
        for x in range(156, 301, 24):
            # Non-periodic stars avoid a repeated-grid phase-correlation alias.
            sx, sy = x+rng.uniform(-3, 3), y+rng.uniform(-3, 3)
            background += rng.uniform(75, 125) * np.exp(-.5*((xx-sx)/3.0)**2-.5*((yy-sy)/.85)**2)
    objects = [(f'o{i}', np.array([38.+i*9, 35.+i*40]), np.array([3.+i*.3, .4*(-1)**i])) for i in range(5)]
    if name == 'crossing':
        objects = [('a', np.array([40., 110.]), np.array([18., 0.])),
                   ('b', np.array([112., 110.]), np.array([-18., 0.]))]
    if name == 'nearby':
        objects = [('a', np.array([55., 110.]), np.array([3., 0.])),
                   ('b', np.array([59., 110.]), np.array([3., 0.]))]
    if name == 'entry_exit':
        objects = [('enter', np.array([-10., 90.]), np.array([8., 0.])),
                   ('leave', np.array([309., 130.]), np.array([8., 0.])),
                   ('stay', np.array([60., 60.]), np.array([2., 1.]))]
    if name in ('empty_targets', 'noise_only', 'daylight_like'):
        objects = []
    shift_step = np.array([18., 8.]) if name == 'camera_motion' else np.array([1.5, -.5])
    frames, truth_frames = [], []
    for index in range(5):
        shift = shift_step * index
        image = cv2.warpAffine(background, np.array([[1., 0., shift[0]], [0., 1., shift[1]]]), (w, h),
                               flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=18)
        records = []
        for object_id, start, velocity in objects:
            reference = start + index * velocity
            raw = reference + shift
            inside = bool(0 <= raw[0] < w and 0 <= raw[1] < h)
            hidden = name == 'counts_change' and ((object_id == 'o3' and index == 1) or (object_id == 'o4' and index in (1, 2)))
            blank = name == 'registration_failure' and index == 2
            visible = inside and not hidden and not blank
            bbox = [max(0., float(raw[0]-4)), max(0., float(raw[1]-4)),
                    min(float(w), float(raw[0]+5)), min(float(h), float(raw[1]+5))] if visible else None
            records.append({'object_id': object_id, 'visible': visible,
                            'reason': 'visible' if visible else 'simulated_miss' if hidden or blank else 'out_of_field',
                            'raw_xy_px': raw.tolist(), 'reference_xy_px': reference.tolist(), 'bbox_raw_xyxy_px': bbox})
            if visible:
                image += 45 * np.exp(-.5*((xx-raw[0])/1.2)**2-.5*((yy-raw[1])/1.2)**2)
        if name == 'artifacts':
            # Unlabeled nuisance: compact persistent artifact can create false tracks.
            p = np.array([106., 213.])+shift
            image += 70 * np.exp(-.5*((xx-p[0])/1.2)**2-.5*((yy-p[1])/1.2)**2)
            image[15, 15] = 255  # isolated hot pixel
        image += rng.normal(0, .8, image.shape)
        if name == 'noise_only':
            image = rng.normal(30, 12, image.shape)
        if name == 'daylight_like':
            image = 185 + 25 * xx/w + 6*np.sin(yy/24) + rng.normal(0, 1, image.shape)
        if name == 'registration_failure' and index == 2:
            image.fill(0)
        if name == 'blurred':
            image = cv2.GaussianBlur(image, (0, 0), 4)
        frames.append(np.rint(np.clip(image, 0, 255)).astype(np.uint8))
        truth_frames.append({'frame_index': index, 'camera_shift_xy_px': shift.tolist(),
                             'raw_to_reference': [[1., 0., -float(shift[0])], [0., 1., -float(shift[1])], [0., 0., 1.]],
                             'objects': records})
    expected = 'unsupported' if name == 'daylight_like' else 'uncertain' if name in ('noise_only', 'registration_failure', 'blurred') else 'supported'
    return StressScene(name, tuple(frames), {'source_type': 'synthetic', 'seed': seed, 'width_px': w,
            'height_px': h, 'coordinate_system': 'top_left_xy_px_integer_centers',
            'bbox_limits': 'xyxy_exclusive_upper', 'expected_suitability': expected,
            'frames': truth_frames, 'truth_is_evaluation_only': True})
