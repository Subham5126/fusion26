"""Evaluation-only five-panel PNG rendering; no detector imports or image mutation."""

from pathlib import Path

from PIL import Image, ImageDraw

from astrotrace.preprocessing.images import display_uint8
from .annotations import AnnotationSet
from .archive import DatasetError
from .spotgeo import Sequence


def overlay_sequence(sequence: Sequence, annotations: AnnotationSet, *,
                     marker_radius_px: float = 5.0) -> Image.Image:
    """Render five native-size panels with red x/y crosses; caller can save/show.

    Pixel centers map to integer image coordinates without shift or axis swap.
    Official boundary points at -.5 / size-.5 are drawn with normal edge clipping.
    Labels are ground truth, which may include positions unobservable in a frame.
    Display contrast is scaled independently per panel and never affects inference.
    """
    if not 0 < marker_radius_px <= 50:
        raise DatasetError("Marker radius must lie in (0,50] px")
    if len(sequence.frames) != 5:
        raise DatasetError("Visualization requires exactly five frames")
    labels = annotations.for_sequence(sequence.sequence_id)
    width, height = sequence.frames[0].width_px, sequence.frames[0].height_px
    if (width, height) != (annotations.width_px, annotations.height_px):
        raise DatasetError("Annotation/image dimensions differ")
    header, caption, gap = 32, 24, 8
    canvas = Image.new("RGB", (5 * width + 4 * gap, header + caption + height), "#151b24")
    draw = ImageDraw.Draw(canvas)
    draw.text((4, 8), f"{sequence.split}/{sequence.sequence_id} - GROUND TRUTH (not detections)", fill="white")
    for index, (frame, label) in enumerate(zip(sequence.frames, labels)):
        if frame.frame_index != index or frame.official_frame != label.official_frame or frame.pixels.shape != (height, width):
            raise DatasetError("Frame order or dimensions inconsistent with annotations")
        panel = Image.fromarray(display_uint8(frame.pixels)).convert("RGB")
        panel_draw = ImageDraw.Draw(panel)
        for x, y in label.object_coords:
            radius = marker_radius_px
            panel_draw.line((x - radius, y, x + radius, y), fill="#ff4545", width=1)
            panel_draw.line((x, y - radius, x, y + radius), fill="#ff4545", width=1)
        left = index * (width + gap)
        canvas.paste(panel, (left, header + caption))
        draw.text((left + 2, header + 4), f"Frame {frame.official_frame}: {label.num_objects} GT", fill="white")
    return canvas


def save_overlay(sequence: Sequence, annotations: AnnotationSet, output: str | Path) -> Path:
    """Save an explicit PNG path; refuse to overwrite an existing user artifact."""
    path = Path(output)
    if path.suffix.lower() != ".png":
        raise DatasetError("Overlay output must have a .png extension")
    canvas = overlay_sequence(sequence, annotations)
    with path.open("xb") as stream:
        canvas.save(stream, format="PNG")
    return path
