# OrbitTrace CV-T14 robustness modules

Internal CV utilities, separate from shared schema 0.1.0 and backend upload
handling. No changes to T03/CV-T04 algorithms, T13 registration or Member3 code.
See `docs/handoffs/CV-T14.md` for measured evidence and ownership boundaries.

## Suitability interface

```python
from astrotrace.preprocessing.suitability import validate_sequence_suitability
diagnostics = validate_sequence_suitability(frames)
# Exactly five same-size decoded grayscale NumPy arrays.
if diagnostics['status'] != 'supported':
    # Return/review diagnostics; do not emit an empty successful debris analysis.
    ...
```

`frames`: an ordered Python sequence, uint8/uint16 or finite float32/64 already
in [0,1]. Dimensions >=32 on both axes, <=4,000,000 pixels. No resizing,
min/max normalization, coordinate changes, encoded-file decoding or I/O occurs.
Color, signed integers, nonfinite values, invalid dimensions/count and mismatched
dimensions are unsupported. Existing bounded image decoders remain responsible
for encoded PNG/JPEG validity and resource limits; this is not an upload route.

Returns a JSON-finite dictionary with `status`, `inference_allowed`, `profile`,
`reason_codes`, human `explanations`, `action` and per-frame metrics. These are
proposed **internal** fields, not additions to AnalysisResult. `supported` permits
candidate inference for this profile; it does not establish target detectability.
`unsupported`/`uncertain` requires review or reacquisition, never "no debris".
Uncertain input defaults to blocked in the local runner's `process` callable.
Its judge stress CLI explicitly bypasses uncertainty for diagnostic experiments,
marks that bypass in reports and tracking warnings, and always blocks unsupported
inputs. Blocked detection JSON has `detections: null`, not `[]`.

Fixed rules for profile `telescope_grayscale_v1` (uncalibrated, source-versioned):

- Quantiles 1/10/50/90/99%, dynamic range q99-q01 and upper/lower clipping.
- Gaussian .8px smoothing, 8px background; robust MAD of high-frequency residual,
  floored by half a dtype quantum or 1e-6.
- Feature evidence: components of response > max(6*noise, 3*quantum), area 2..300.
  Fewer than eight features yields uncertainty; these features are not certified stars.
- Broad bright field: q10>.4 AND median>.6 AND q90>.7 AND >80% pixels above .5.
  This is a telescope-profile mismatch, not a semantic daylight classifier.
- >80% upper saturation is unsupported. Noise>.08 yields uncertainty.
- Laplacian/Sobel energy ratio of the smoothed image <.008 with >=8 features
  suggests blur. This is neither calibrated PSF nor optical blur measurement.
- Background median range >.25 across frames yields uncertainty.

All metrics use native pixels or normalized intensity, not photometry. Bright
astronomical backgrounds, clouds, city lights, unusual PSFs and adversarial images
can defeat these rules. Low-feature valid nighttime frames can be uncertain.
There is no independent real daylight/cloud validation set. The controlled
renderer and rules are not independently sampled; their label agreement is not
real-world accuracy. Member1 must approve any API mapping and enforce streamed
byte/decoded-image bounds before using this with uploads.

## Synthetic scenes

```python
from astrotrace.datasets.stress import CASES, create_stress_scene
scene = create_stress_scene('counts_change', seed=14)
frames = scene.frames       # inference input: five 320x240 uint8 arrays
truth = scene.truth         # evaluator only; NEVER passed to inference
```

Declared cases: counts_change, entry_exit, crossing, nearby, camera_motion,
artifacts, empty_targets, registration_failure, noise_only, daylight_like,
blurred. Fixed PCG64 seed, non-periodic elongated background features, Gaussian
targets, independent linear target motion and separate translations. Changing
visibility renders counts [5,3,4,5,5]; missed targets have visibility=False and
`simulated_miss` reason. Empty-target scene retains stars; registration_failure
has a truly blank frame 2. Daylight-like is a controlled bright gradient/cloud
pattern, not a daylight photograph. Noise-only uses iid Gaussian noise; artifacts
include a hot pixel and a persistent compact nuisance. Nearby 4px targets and
coincident crossings intentionally expose limitations. No PSF/CCD realism claim.

Truth includes object IDs, visible flags/reasons, raw/reference centers,
exclusive upper xyxy boxes and 3x3 raw-to-frame0 transforms. Raw centers are
top-left integer pixel centers (continuous subpixel values allowed); x right,
y down. Truth transforms subtract rendered camera shifts. Values for invisible
objects may be outside image bounds; invisible boxes are null. Truth is separate
from shared Detection and cannot be accepted by detector configuration.

## Post-inference evaluation

```python
from astrotrace.detection.stress_evaluation import evaluate_stress
metrics = evaluate_stress(detections, tracks, truth, radius_px=5.)
```

Uses maximum-cardinality, then minimum-distance one-to-one matching within an
inclusive **5px raw-coordinate** radius, independently per frame. Registered
Detection keeps identical raw fields, so both streams have the same detection
metrics. TP/FP/FN, precision/recall/F1, localization RMSE/mean and FP/frame come
from the existing evaluator; ratios without observations/denominators are null.
Processing times are recorded separately by the runner (evaluator timing is empty).

Identity switches: truth's next resolvable observed match changes predicted track
ID. Fragmentation: distinct matched track IDs per truth minus one. Correct-link
fraction counts consecutive identity-resolvable matches within a predicted track,
not all links including false observations. Truths within 1px of another truth
are excluded from identity scoring at that frame; excluded counts are reported.
An exact crossing cannot be certified by these metrics.

Gap recovery counts one/two `simulated_miss` frames bounded by visible endpoints:
both endpoints must match actual detections and retain the same track ID.
Absent matches are unscorable, not successful recoveries. False confirmed tracks
have >=3 observed points (including tracks later ended) but fewer than three
matches to any one true target; tracks containing ambiguous matches are reported
separately as unscorable for false confirmation. This criterion is tied to this
snapshot's actual three-observation confirmation default. Predicted trajectory
points never enter any score. Not official MOT/IDF1/HOTA or physical identity.

## Member3 integration (no new detector contract)

```python
from orbittrace.detection import detect_sequence
from astrotrace.preprocessing.registration import register_sequence, add_reference_coordinates

raw = detect_sequence(frames, sequence_id='demo', method='optimized')
registration = register_sequence(frames)
if registration.status == 'failed':
    # Strict registered mode: stop, expose diagnostics; never mix coordinate frames.
    ...
else:
    detections = add_reference_coordinates(raw, registration)
    tracks = Tracker().process_sequence(detections, frame_indices=range(5))
```

Existing signature: `detect_sequence(frames, *, sequence_id, profile='spotgeo',
timestamps_s=None, config=None, method='optimized') -> list[Detection]`.
CV-T04 default adapter: threshold_sigma=4.5, max_context_elongation=2.0; other
parameters unchanged. Quality is `(1-exp(-peak_snr/8))/max(1,elongation)`, an
uncalibrated heuristic, not class confidence or debris probability. IDs identify
per-frame candidates. Registration adds only reference x/y; native raw centers,
boxes, IDs, timestamps and scores are preserved. Reference coordinates may lie
outside image bounds; do not clip or relabel raw values.

Snapshot `a015cc949955d0438c8a16789b23746c3206f3d1` tracker prefers paired reference
coordinates and otherwise falls back to raw. Always pass all frame indices to
advance lifecycle on empty frames. Its constructor AND current PipelineConfig
defaults are **20px**, confirmation=3 observations, retirement after >2 misses.
CV-T13's 15px documentation statement is incorrect; preserved T13 files are not
rewritten. Snapshot hashing ensures the tested implementation is identifiable.
No gate, lifecycle, tracker, backend or shared schema was changed.

Sky-star alignment includes apparent sky drift plus camera motion. In GEO-staring
imagery target displacement after star compensation can exceed the tracker gate,
especially before velocity initialization. Synthetic improvement does not prove
improved ESA tracking. Raw comparator deliberately requests no registration in
its AnalysisResult (`not_required` plus explicit diagnostic warnings); registered
mode is blocked if any frame fails. No production automatic raw fallback is added.

## Commands and artifacts

From E:\Fusion in PowerShell, existing .venv (Python 3.12) with NumPy, OpenCV,
SciPy, Pillow, Pydantic and pytest; existing backend test dependencies retained.
No new dependency/package install or license adoption was required.

```powershell
Set-Location E:\Fusion
$env:PYTHONPATH = "$PWD\src;$PWD\backend"
# Only if the already tested commit is absent locally:
git fetch --no-tags origin feature/tracking-trajectory
& .\.venv\Scripts\python.exe scripts\spotgeo_robustness.py --output artifacts\reports\cv_t14\rerun --tracking-ref a015cc949955d0438c8a16789b23746c3206f3d1
$env:CV_T06_TRACKING_SNAPSHOT = "$PWD\artifacts\reports\cv_t14\rerun\tracking_snapshot"
& .\.venv\Scripts\python.exe -m pytest -q -rs
Start-Process "$PWD\artifacts\reports\cv_t14\rerun\index.html"
```

Use a **new** output directory each time; existing directories cause an explicit
FileExistsError. `--synthetic-only` skips ESA; missing ESA is reported without
downloads. No automatic Git fetch/commit/push occurs inside the evidence runner.
All generated images/truth/JSON/snapshots stay in gitignored reports.

Each case contains candidates.png, actual observed tracking_raw/registered.png
and schema JSON when run, suitability/registration/report JSON, original/aligned
panels, masks, before/after star overlays, correspondences and residuals. Synthetic
cases additionally contain five PNGs and separate truth.json. Blocked cases have
no tracking JSON. summary.json supplies parameters, source hashes, versions and
real input hashes. The offline index links to actual evidence, not mock output.

Wider audit command (all headers/labels, encoded hashes for non-ESA sources):

```powershell
& .\.venv\Scripts\python.exe scripts\spotgeo_inventory.py --output artifacts\reports\cv_t14\inventory_rerun.json
```

This can be slow on Windows disks with tens of thousands of files. It never
copies or repairs a dataset. Library callable
`astrotrace.datasets.inventory.inventory_datasets(project_root) -> dict` reports
dimensions/modes, split counts, label errors/missing labels, duplicate groups,
unverified meanings/rights and a training plan. `inspect_yolo_labels(paths, stems)`
accepts local class0 normalized cxcywh text; `inspect_csv(path, stems)` inspects
safe literals without assuming axis order. These local audit helpers are not
bounded upload parsers and must never enter inference. Full decoding, perceptual
duplicate matching and session grouping remain separate validation tasks.

Packaging still needs Member1: backend/pyproject.toml does not package src/astrotrace;
the root packaging proposal remains unapplied. The scripts bootstrap src+backend;
direct imports require those on Python's path. No clean wheel-install claim.
