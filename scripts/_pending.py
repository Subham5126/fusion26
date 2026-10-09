import argparse
import sys


def pending_cli(description: str, task: str, manifest: bool = False) -> None:
    parser = argparse.ArgumentParser(description=description + " (pending implementation)")
    parser.add_argument("--config", help="Trusted local YAML configuration (not processed yet)")
    if manifest:
        parser.add_argument("--manifest", help="Ordered local manifest (not read yet)")
    else:
        parser.add_argument("--seed", type=int, default=26, help="Future deterministic scene seed")
    parser.parse_args()
    print(f"not_implemented: {task}; no images, analysis or metrics were produced.", file=sys.stderr)
    raise SystemExit(2)
