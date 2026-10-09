"""Contact panels with explicit ground-truth/prediction colors; display only."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def panel(source, records, output, predictions=None, title="Streak candidates; identity unverified"):
    records = list(records)
    if not records:
        raise ValueError("No images selected for panel")
    size, columns = 320, 4
    canvas = Image.new("RGB", (columns*size, ((len(records)+columns-1)//columns)*(size+40)+36), "#141922")
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 8), title + " | RED labels, GREEN predictions", fill="white")
    for index, row in enumerate(records):
        with Image.open(Path(source)/row["image"]) as original:
            im = original.convert("RGB")
        marks = ImageDraw.Draw(im)
        w, h = im.size
        for _, x, y, bw, bh in row.get("boxes", []):
            marks.rectangle(((x-bw/2)*w, (y-bh/2)*h, (x+bw/2)*w, (y+bh/2)*h), outline="#ff4848", width=3)
        dets = predictions.get(row["image"], []) if predictions else []
        for detection in dets:
            marks.rectangle(detection["bbox_raw_px"], outline="#41ff70", width=3)
        left, top = (index%columns)*size, 36+(index//columns)*(size+40)
        canvas.paste(im.resize((size,size)), (left,top))
        draw.text((left+4,top+size+3), row["image"], fill="white")
        draw.text((left+4,top+size+18), f"GT:{len(row.get('boxes',[]))} Pred:{len(dets)} {row.get('label_status','')}", fill="white")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=("train","validation","test"), default="train")
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text())
    rows = [r for r in audit["records"] if r["split"] == args.split and r["label_status"] != "invalid"]
    # Display both positives and assumed negatives without selecting by metrics.
    positives = [r for r in rows if r["boxes"]][:args.limit//2]
    negatives = [r for r in rows if not r["boxes"]][:args.limit-len(positives)]
    preds = json.loads(args.predictions.read_text())["by_image"] if args.predictions else None
    panel(audit["source"], positives+negatives, args.output, preds)


if __name__ == "__main__":
    main()
