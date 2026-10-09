"""Native image-grid prediction panels, with optional evaluation-only label comparison."""

from pathlib import Path

from PIL import Image, ImageDraw

from astrotrace.datasets.spotgeo import Sequence
from astrotrace.preprocessing.images import display_uint8
from .runner import SequenceDetections


def save_detection_panels(sequence: Sequence, predictions: SequenceDetections, output: str | Path,
                          annotations=None) -> Path:
    """Green candidate boxes/crosses; optional red GT crosses are a separate layer.

    No transform/resizing changes scientific coordinates. Per-panel contrast is
    display-only. Labels are accepted here for inspection, never by the detector.
    """
    if sequence.sequence_id != predictions.sequence_id or sequence.split != predictions.split:
        raise ValueError("Prediction and image sequence do not match")
    width, height = sequence.frames[0].width_px, sequence.frames[0].height_px
    if annotations is not None and (annotations.width_px, annotations.height_px) != (width, height):
        raise ValueError("Annotation dimensions do not match image")
    labels = annotations.for_sequence(sequence.sequence_id) if annotations is not None else [None] * 5
    canvas = Image.new("RGB", (5 * width + 32, height + 56), "#151b24")
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 8), f"{sequence.split}/{sequence.sequence_id}: GREEN candidates; RED ground truth (if supplied); no tracking", fill="white")
    for index, (frame, predicted, truth) in enumerate(zip(sequence.frames, predictions.frames, labels)):
        if frame.frame_index != index or predicted.frame_index != index:
            raise ValueError("Prediction frame order inconsistent")
        panel = Image.fromarray(display_uint8(frame.pixels)).convert("RGB")
        marks = ImageDraw.Draw(panel)
        for detection in predicted.detections:
            x, y = detection.x_raw_px, detection.y_raw_px
            left, top, right, bottom = detection.bbox_raw_px
            marks.rectangle((left, top, right - 1, bottom - 1), outline="#35ff70")
            marks.line((x - 3, y, x + 3, y), fill="#35ff70")
            marks.line((x, y - 3, x, y + 3), fill="#35ff70")
        if truth is not None:
            for x, y in truth.object_coords:
                marks.ellipse((x - 6, y - 6, x + 6, y + 6), outline="#ff4545")
        offset = index * (width + 8)
        canvas.paste(panel, (offset, 56))
        draw.text((offset + 4, 36), f"Frame {frame.official_frame}: {len(predicted.detections)} candidates", fill="white")
    output = Path(output)
    if output.suffix.lower() != ".png":
        raise ValueError("Prediction panel output must be a PNG")
    with output.open("xb") as stream:
        canvas.save(stream, format="PNG")
    return output
