"""Actual native-image registration previews/correspondences; no inferred truth."""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .candidates import normalize_grayscale
from .registration import warp_to_reference


def save_registration_panels(frames, registration, output):
    """Write original/aligned/overlay/match/residual PNGs; never overwrite files.

    Uses one shared 99.8th-percentile intensity scale solely for display. Matrices
    remain scientific float values. Black warped borders are accompanied by saved
    validity masks; failed frames show a failure label and are never fake-aligned.
    """
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    arrays = [normalize_grayscale(p)[0] for p in frames]
    ceiling = max(max(float(np.percentile(a, 99.8)) for a in arrays), 1/255)
    def view(a):
        return np.rint(np.clip(a/ceiling, 0, 1)*255).astype(np.uint8)
    width, height = registration.width_px, registration.height_px
    row_height = height+50
    panels = {key: Image.new('RGB', (width*len(frames), row_height), (16, 22, 30))
              for key in ('original', 'aligned', 'star_overlay_before', 'star_overlay', 'residuals')}
    correspondence = Image.new('RGB', (2*width, row_height*len(frames)), (16, 22, 30))
    reference_view = view(arrays[0])
    reference_rgb = np.repeat(reference_view[..., None], 3, axis=2)
    for index, (pixels, frame) in enumerate(zip(frames, registration.frames)):
        left = index*width
        raw_view = view(arrays[index])
        panels['original'].paste(Image.fromarray(raw_view).convert('RGB'), (left, 50))
        before_rgb = np.zeros((height, width, 3), np.uint8)
        before_rgb[..., 0] = reference_view
        before_rgb[..., 1] = raw_view
        panels['star_overlay_before'].paste(Image.fromarray(before_rgb), (left, 50))
        if frame.status != 'failed':
            aligned, valid = warp_to_reference(pixels, frame)
            panels['aligned'].paste(Image.fromarray(view(aligned)).convert('RGB'), (left, 50))
            rgb = np.zeros((height, width, 3), np.uint8)
            rgb[..., 0] = reference_view
            rgb[..., 1] = view(aligned)
            rgb[~valid] = (30, 30, 80)
            panels['star_overlay'].paste(Image.fromarray(rgb), (left, 50))
            mask_path = output / f'valid_mask_{index}.png'
            if mask_path.exists():
                raise FileExistsError(mask_path)
            Image.fromarray(valid.astype(np.uint8)*255).save(mask_path)
        else:
            panels['aligned'].paste(Image.new('RGB', (width, height), (35, 10, 10)), (left, 50))
        panels['residuals'].paste(Image.fromarray(reference_rgb), (left, 50))
        title = f'frame {index}: {frame.status}'
        shift = None if frame.raw_to_reference is None else [frame.raw_to_reference[0][2], frame.raw_to_reference[1][2]]
        detail = 'no usable transform' if shift is None else f'raw->ref ({shift[0]:.3f}, {shift[1]:.3f}) px'
        for key, panel in panels.items():
            draw = ImageDraw.Draw(panel)
            draw.text((left+6, 5), title, fill='white')
            draw.text((left+6, 20), detail if key != 'original' else 'Original native image; display scale only', fill='white')
            draw.text((left+6, 35), ('red=reference green=raw BEFORE alignment' if key == 'star_overlay_before' else
                      'red=reference green=aligned blue=invalid') if key.startswith('star_overlay') else
                      f'fit {frame.fit_inliers} / matches {frame.matched_features}; val RMSE {frame.validation_rmse_px}', fill='white')
        top = index*row_height
        correspondence.paste(Image.fromarray(reference_view).convert('RGB'), (0, top+50))
        correspondence.paste(Image.fromarray(raw_view).convert('RGB'), (width, top+50))
        cd = ImageDraw.Draw(correspondence)
        cd.text((6, top+5), f'Reference 0 -> raw frame {index}: {frame.status}; green=fit cyan=validation red=outlier', fill='white')
        cd.text((6, top+25), 'Warnings: '+', '.join(frame.warnings), fill='white')
        rd = ImageDraw.Draw(panels['residuals'])
        for ref, raw, inlier, validation in zip(frame.reference_points, frame.raw_points, frame.inlier_flags, frame.validation_flags):
            color = '#22ee99' if inlier else '#ff4444'
            if validation and inlier:
                color = '#22ccff'
            cd.line((ref[0], top+50+ref[1], width+raw[0], top+50+raw[1]), fill=color, width=1)
            if shift is not None:
                endpoint = np.asarray(raw)+np.asarray(shift)
                # 10x residual vectors are explicitly labelled; coordinates not changed.
                end = np.asarray(ref)+10*(endpoint-np.asarray(ref))
                rd.ellipse((left+ref[0]-2, 50+ref[1]-2, left+ref[0]+2, 50+ref[1]+2), outline=color)
                rd.line((left+ref[0], 50+ref[1], left+end[0], 50+end[1]), fill=color)
        rd.text((left+6, 35), 'Residual arrows x10; cyan=validation, red=rejected', fill='white')
    panels['correspondences'] = correspondence
    for key, panel in panels.items():
        path = output / f'{key}.png'
        if path.exists():
            raise FileExistsError(path)
        panel.save(path)
