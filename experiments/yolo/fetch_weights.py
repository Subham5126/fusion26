"""Explicit small official YOLO26n checkpoint fetch with provenance; no dataset IO."""
import argparse
import json
from pathlib import Path
import urllib.request

from .common import sha256, write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    url="https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt"
    if args.output.exists():
        raise ValueError("Refusing to overwrite checkpoint")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen(url,timeout=30) as response:
        payload=response.read(32*1024*1024+1)
    if len(payload)>32*1024*1024:
        raise ValueError("Nano checkpoint exceeded 32MiB download limit")
    args.output.write_bytes(payload)
    write_json(args.output.with_suffix(".provenance.json"),{"url":url,"bytes":len(payload),"sha256":sha256(args.output),
                "model":"Ultralytics YOLO26n Detect, COCO-pretrained", "license":"AGPL-3.0 / optional Enterprise", "training_completed":False})
    print(json.dumps({"weights":str(args.output),"bytes":len(payload),"sha256":sha256(args.output)},indent=2))


if __name__ == "__main__":
    main()
