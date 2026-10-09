# Command-line entry points

All three entry points are placeholders with working `--help`. Executing them
prints `not_implemented`, names the task, and exits 2 without creating output.

| Script | Next owner / dependency |
|---|---|
| generate_demo.py | B, T02; images in data/synthetic, truth in data/ground_truth |
| analyze_sequence.py | A, T07 after T03/T04/T05; image-only inference |
| evaluate.py | C, T06 after T02; joins output with separate truth |

Use the same public pipeline for CLI/API once implemented. Local CLI paths are
trusted operator inputs; they must never become arbitrary-path HTTP inputs.
