# spotGEO dataset exploration (T14)

This standalone worker module supports AstroTrace AI / SPACE-02 dataset
exploration. It uses the existing contract conventions while awaiting integration
with the repository's active `backend/orbittrace` package. Python namespace
packages let `astrotrace` import from `src` without editing integration-owned
package declarations. Do not treat this as an installed backend feature.

Implemented in T14: local ZIP inventory, five-frame PNG loading, official point-label
parsing, ground-truth visualization and deterministic tiny fixtures. The subsequent
[T03 detector milestone](../detection/README.md) adds local real-data validation,
image-only OpenCV proposals and separate held-out detection evaluation. No
registration, tracking, training, external acquisition or HTTP upload route is
implemented here. The extracted dataset is now present at `data/raw/SpotGEOv2/`;
the original archive checksum remains unverified. No dataset was downloaded by
this worker.

## Source format and provenance

Verified 9 October 2026 through the [ESA dataset page](https://kelvins.esa.int/spot-the-geo-satellites/dataset/),
[submission format](https://kelvins.esa.int/spot-the-geo-satellites/submission-details/)
and [official starter notebook](https://zenodo.org/records/3874368/files/spotGEO_starter_kit.ipynb?download=1).
These confirm grayscale 640x480 PNGs at `train/<sequence_id>/<frame>.png`,
frames 1 through 5, with an analogous test layout. The notebook confirms the
numeric folder/frame names. This implementation is original code; the starter
notebook was inspected as format evidence, not copied or executed.

The [v2 record](https://zenodo.org/records/4432143) was rate-limited through the
web reader; a bounded metadata-only request to its
[JSON API](https://zenodo.org/api/records/4432143) succeeded. It reports version
2.0.0, archive `SpotGEOv2.zip`, 4,230,495,720 bytes, MD5
`9a44895f17830247208230bc09c43f2d`, and CC BY 4.0. V2 adds test labels and
corrected missing train labels. Metadata license evidence does not certify the
contents of an uninspected local archive. Preserve attribution to Chen, Liu,
Chin, Rutten, Derksen, Maertens, von Looz, Lecuyer and Izzo and the dataset DOI
when using ESA data. No official sample is redistributed here.

The image loader defaults to this structure:

```text
<root>/
  train/1/1.png ... 5.png
  train/2/1.png ... 5.png
  test/<sequence_id>/1.png ... 5.png
  train_anno.json
  test_anno.json
```

Source roots and ZIP prefixes are explicit local exploration options. A ZIP can
have a wrapper folder, discovered only when unique; ambiguity fails and requires
`prefix`. Annotations must be selected explicitly. No train/test split is
invented, mixed or reselected. Whole sequences must stay together in any later
development/validation/held-out selection.

## Environment recommendation

Use a Python 3.12 virtual environment, CPU only. The current `.venv` already
provides Python 3.12.14, NumPy 2.5.3, Pillow 12.3.0 and pytest 9.1.1, verified
by importing/reading installed package metadata. OpenCV headless 4.14.0.94 is
available for the next task; this loader does not depend on it. No packages were
installed and no dependency declaration/lock was changed for this task.

Installed license metadata: NumPy BSD-3-Clause plus bundled licenses, Pillow
MIT-CMU, pytest MIT, OpenCV headless Apache 2.0. No new third-party code or weights
were adopted. Loading alone needs NumPy/Pillow; the subsequent detector/test suite
also needs existing OpenCV, SciPy, Pydantic and the shared backend models.
Matplotlib, Astropy, torch, Ultralytics, CUDA and scikit-image are unnecessary.

For a fresh teammate environment, follow the integration-owned
[setup](../../../docs/SETUP.md) and existing `backend/requirements.lock.txt`.
Use the existing integration-owned lock/package for the complete T03 test suite;
the old T14-only minimal NumPy/Pillow environment is insufficient for detection.
These fresh-install commands are recommendations, not a newly resolved lock:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e ./backend
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m pytest -q -c backend/pyproject.toml tests/detection
```

Use `.venv` commands below to reproduce in the existing workspace. The CLI and
worker tests set their source path locally. Library users add `src` to PYTHONPATH;
contract consumers additionally need the installed backend or `backend` on that
path. Packaging these modules belongs to integration, not this worker.

## Reproducible small example

Run from repository root. All output paths must be new; existing artifacts are
preserved. Full ESA data is unnecessary.

```powershell
.\.venv\Scripts\python.exe scripts/spotgeo.py fixture data/synthetic/spotgeo_fixture --seed 26 --zip data/synthetic/spotgeo_fixture.zip
.\.venv\Scripts\python.exe scripts/spotgeo.py inspect data/synthetic/spotgeo_fixture.zip --sha256
.\.venv\Scripts\python.exe scripts/spotgeo.py list data/synthetic/spotgeo_fixture.zip --fixture-size
.\.venv\Scripts\python.exe scripts/spotgeo.py view data/synthetic/spotgeo_fixture.zip --fixture-size --sequence 1 --annotations train_anno.json --output artifacts/reports/spotgeo_fixture_overlay.png
.\.venv\Scripts\python.exe -m pytest -q -c backend/pyproject.toml tests/detection
```

For an already acquired official ZIP (no download is performed):

```powershell
.\.venv\Scripts\python.exe scripts/spotgeo.py inspect data/external/SpotGEOv2.zip --limit 30
.\.venv\Scripts\python.exe scripts/spotgeo.py list data/external/SpotGEOv2.zip --split train
.\.venv\Scripts\python.exe scripts/spotgeo.py view data/external/SpotGEOv2.zip --sequence 1 --annotations train_anno.json --output artifacts/reports/spotgeo_train_1.png
```

`inspect` emits JSON with each member's name, kind, compressed and uncompressed
bytes plus counts and total bytes. Without `--limit`, it lists all entries;
truncated output explicitly records `omitted_entries`. `--sha256` separately
streams the full local ZIP on explicit request. Inventory alone does not read
payloads, validate CRC, verify published MD5 or inspect the actual JSON schema.
`list` outputs numeric sequence IDs without decoding images or reading labels.
`view` outputs a new PNG and JSON identifying its overlay as ground truth.
`fixture` creates two authored 64x48 sequences (moving point and empty scene),
separate annotations and provenance. Default seed is 26. These are adapter
fixtures, not telescope realism or a measured benchmark. Invalid inputs exit 2
with an actionable stderr message; successful commands exit 0.

## Module inputs, outputs and limits

| Module | Input | Output / behavior | Limitations |
|---|---|---|---|
| `archive.py` | Local ZIP + ArchiveLimits | Validated central-directory inventory; bounded explicit member read | No extraction, payload inspection or rights verification during listing |
| `spotgeo.py` | Root directory/ZIP, train/test, sequence ID | Sequence with five Frame objects; native read-only NumPy pixels and original frame numbers | Requires 1.png..5.png, positive decimal IDs, equal dimensions; default 640x480; no timestamps, color conversion, resizing or registration |
| `annotations.py` | Explicit UTF-8 JSON bytes/text + dimensions | Immutable AnnotationSet / AnnotationFrame preserving float x/y and original ID | No identity, bounding boxes, class, visibility or timing inferred |
| `visualization.py` | Sequence plus separate AnnotationSet | Five native-size panels as PIL image/new PNG, red crosses and GT caption | Display-only per-frame contrast; no predictions or detection metrics |
| `fixtures.py` | New directory, seed, optional new ZIP | Ten tiny PNGs and separate JSON labels/provenance | Authored synthetic samples; no ESA redistribution |
| `scripts/spotgeo.py` | inspect/list/view/fixture arguments | JSON inventory/status, explicit local artifacts, exit code | CLI only; not an API route or backend installation |

Archive defaults: 100,000 entries, 32 MiB central directory, 64 MiB/member,
16 GiB total uncompressed, compression ratio <=1000. Central directory bounds
are checked before ZipFile allocation. Single-disk conventional ZIP/ZIP64 with
stored/deflated members is supported; multi-disk, extended ZIP64 end records,
encrypted, special-file and unsafe/aliased names fail. Path traversal, absolute
paths, backslashes, Windows reserved names, duplicate/case aliases and symlinks
are rejected. Directory reads reject symlinks below the selected root and
resolved path escapes. Use trusted local data; concurrent malicious replacement
of directory files is outside this local CLI's threat model.

Selected PNG reads are capped at 16 MiB encoded PNG bytes and 4,000,000
decoded pixels/frame, before image allocation; the five frames are then resident
in memory. PNG grayscale uint8/uint16 values and axis order are preserved.
Corrupt, animated, RGB/palette or other image formats fail instead of being
converted silently. No full archive extraction occurs. Annotation reads are
capped at 32 MiB; parsing materializes that bounded JSON array in memory.
These local safeguards do not implement the project's absent HTTP upload quotas.

JSON must be an array with exactly `sequence_id`, `frame`, `num_objects`,
`object_coords` on each record. Frame IDs 1..5 map to internal indexes 0..4 while
retaining `official_frame`. Sequence IDs are canonical positive decimal ints or
strings, with original JSON type retained. Counts must match 0..30 finite pairs.
Duplicate records/fields, incomplete sequences and inconsistent per-sequence
ground-truth counts fail by default. `require_complete=False` explicitly allows
partial exploration; `for_sequence` still requires all five entries. Empty
arrays are valid; a missing annotation is an error, never an invented empty scene.

## Coordinates and tracking integration

ESA labels are `(x, y)` with top-left origin, x right and y down, in inclusive
`[-0.5, width-0.5]` and `[-0.5, height-0.5]`. NumPy uses `[y, x]`. The parser and
overlay never swap coordinates, round them or add 0.5. Raw images use integer
pixel centers; the half-pixel limits describe the image edges. Any later adapter
conversion must be explicit and justified against the official validation code.
Upper-edge ground truth is valid even though an integration Detection centroid
must be inside its exclusive-upper box; do not fabricate a Detection from a label.

```python
from astrotrace.datasets import SpotGeoDataset, parse_annotations

dataset = SpotGeoDataset("data/external/SpotGEOv2.zip", split="train")
sequence = dataset.load_sequence(1)   # reads five images only
for frame in sequence.frames:
    # Pass pixels + image-only metadata to the detector. No labels here.
    print(frame.frame_index, frame.width_px, frame.height_px, frame.timestamp_s)

# Evaluation / human inspection is a separate, explicit operation:
labels = parse_annotations(dataset.read_file("train_anno.json", max_bytes=32*1024*1024))
ground_truth = labels.for_sequence(1)
```

Tracking engineer: use detector outputs in native raw pixels; do not use these
label arrays as observations or stable object IDs. Their array order carries no
identity contract, and labels may describe an unobservable position. Timestamp
values remain None, so use frame units until actual timing is available. spotGEO
camera orientation changes: registration must be estimated from images, have
an explicit failure state, preserve raw-to-reference transforms and inverses,
and report the declared reference frame. Image loading performs no registration.

Integration owner: register image bytes in controlled storage and create opaque
image_ref tokens to produce existing SequenceInput v0.1.0. This internal Sequence
has no paths/labels/public transport schema and must not be serialized directly
as that contract. Resolve packaging or relocate modules into `orbittrace` through
review; coordinate adapters/pipeline imports belong to integration. The proposed
[detector boundary](../detection/README.md) refers to the existing Detection,
without redefining it. No backend/frontend/tracking/shared contract was edited.

## Verification and outstanding work

Tests in `tests/detection` generate fixtures in temporary directories and verify
image-only reads, unchanged pixels, strict five-frame order, official boundaries,
fractional coordinates, empty labels, malformed JSON, corrupt images, size bounds,
unsafe archives, and x/y overlay direction. Exact commands/results and changed
paths are recorded in [T14 handoff](../../../docs/handoffs/T14.md).

T14's handoff is historical. T03 now parses actual local train/test annotations,
validates decoding/order and creates GT panels, freezes whole-sequence membership,
and runs raw-coordinate detection evaluation. See its
[handoff](../../../docs/handoffs/T03.md) for final evidence and exact outcomes.
`validation.py` discovers extracted roots and annotation files by structure and
content, then reuses the existing loader/parser/overlay. Its inputs are a local
root (or None for missing data) and a new results directory; output is finite JSON,
per-image hashes and GT PNGs. See the detector guide's validation command.

Pending: original archive integrity/rights/readme inspection, registration and
pipeline/package integration. The folder is user-provided as spotGEO v2, but no
archive hash verification authenticates that version; reports preserve this limit.
