# Handoff: CV-T05 — final detection package and Member 3 readiness

Owner: Computer Vision and Dataset Engineer, explicitly assigned by user.
Backlog ownership: continuation of T03 / Data-CV; CV-T05 is the user milestone,
not the tracking/trajectory BACKLOG T05 task.
Base commit: `fa593cf5052f96d311d049f2b84949f588a99407`, active checkout main.
Date: 9 October 2026, Asia/Calcutta.
State: **ready_for_review**. Standalone detector verified, five real sample
packages generated/reproduced, fixed-config supplemental evaluation completed,
and read-only consumption by actual fetched Member 3 source tested. Backend API
integration and scientifically valid ESA tracking remain blocked, as below.

## Exact files added or modified by CV-T05

Added:

- `scripts/spotgeo_handoff.py`
- `tests/detection/test_handoff.py`
- `src/astrotrace/detection/MEMBER3.md`
- `docs/handoffs/CV-T05.md`

Modified: `src/astrotrace/detection/README.md` (links to Member 3 guide/report).

T03/CV-T04 detectors, preprocessing, loader, shared interface/schema and historical
evidence remain byte-identical. No backend, tracking, frontend, root config,
dependency/lock, STATUS or BACKLOG edits were made **by this milestone**. No
commit, push, branch/checkout/merge, installation, training, dataset download or
Git fetch was performed by CV-T05. The pre-existing PROBLEM_STATEMENT edit and
prior uncommitted T14/T03/CV-T04 work were retained.

Concurrent external CV-T06 work appeared while these checks ran: detection
adapter/example, package initializer, adapter/compatibility tests and
`docs/handoffs/CV_TO_TRACKING.md`. Those files were inspected/consumed, not edited
or reverted by CV-T05. Its bounded Git fetch made the existing Member 3 branch
available locally; CV-T05 reused that already fetched ref without network access.
The final full-suite count includes those independently authored tests.

Generated outputs, all already gitignored:

- `artifacts/reports/cv_t05_member3/`: detector_config.json, environment.json,
  samples.json, sample_evaluation.json, initial integration.json and README.md;
  five split_ID directories, each with actual detections.json, raw_frames.png,
  candidates.png, comparison.png and evaluation.json.
- `artifacts/reports/cv_t05_final_evaluation/`: frozen membership.json,
  benchmark.json, predictions.json, image_hashes.json and three comparison panels.
- `artifacts/reports/cv_t05_integration_probe/`: first standalone backend probe.
- `artifacts/reports/cv_t05_integration_current/`: current probe, including the
  externally added CV-T06 backend adapter's signature/default selection.
- `artifacts/reports/cv_t05_tracking_snapshot/`: compatibility.json, five actual
  Track-list JSON outputs, and byte-identical tracker.py/fit.py source snapshot.

The initial package probe predates adapter availability; use integration_current
for current backend selection. These historical outputs were not overwritten.
Original PNGs are dataset-relative references, not copied into the source package
or Git. Local previews are rendered from actual image arrays; saved proposals
are actual detector outputs, never hand-authored detections.

## Detector verification and real data actually accessed

Actual extracted root: **E:\Fusion\data\raw\SpotGEOv2**.

Package PNGs accessed (all official frames1.png..5.png):

- `train/84/`, `train/438/`
- `test/10/`, `test/57/`, `test/1107/`

Supplemental evaluation: 128 other official test sequence folders, all five
frames each; exact IDs are frozen in cv_t05_final_evaluation/membership.json.
First three selected IDs are test/43,49,68. No overlap with package samples or
recorded T03/CV-T04 tuning/scoring/presentation IDs. In total, **665 distinct real
PNG files** were decoded this milestone (25 package +640 final evaluation), with
additional repeat/direct-call/package verification passes over the sample PNGs.
All were decoded as 640x480 uint8 in official order1..5/internal order0..4 by the
existing loader. This does not claim a fresh exhaustive32,000-image validation.

train_anno.json and test_anno.json were discovered by content/membership and
parsed separately for evaluation/rendering. Both complete annotation files were
read; none of their coordinates enters inference. The original32,000-image hash
manifest was read as metadata for unchanged-pixel/duplicate checks; that did not
decode32,000 images again. Dataset/archive identity remains unverified beyond
the user-provided local source and prior metadata; dataset_version is unknown.

Verification used the exact existing CV-T04 selected mapping, source/config
hashes and callable. All25 sample frames passed:

- Native dimensions/order and shared Detection v0.1.0 validation, finite JSON,
  frame-consistent detections/unique IDs, bounded exclusive boxes and centroids.
- Read-only input checksum comparison; repeat inference produced identical
  scientific output and IDs.
- Direct OptimizedDetector.detect and detect_optimized_sequence agreed on every
  scientific field; helper namespacing only changed the expected opaque IDs.
- Python file-access guards blocked Path.open/builtins.open during inference;
  loader tracing observed only the expected five PNG reads. Labels were first
  opened after all sample inference completed, for separate scoring.
- New outputs exactly reproduced the previously saved CV-T04 outputs on all
  five sequences (timings excluded), including genuine empty output.
- Original T03 final-source manifest, CV-T04 algorithm/script hashes and selected
  configuration digest remained unchanged. No detector parameters were tuned.

Annotation hashes remain:

- train: `2727e7c21f1fef229b024dcb00952d0781057661c4ccb64937dce50f08e1fdfe`
- test: `8c3e141fba0b5d3ed220563b458a17b17d73ec8cc762aa46abe40d1016f557f4`

## Five real examples for Member 3

| Sequence | Actual candidates, internal frames0..4 | Actual separate scoring TP/FP/FN |
|---|---|---|
| train/84 | 7,7,6,8,6 | 15/19/10 |
| train/438 | 6,8,5,3,5 | 12/15/18 |
| test/10 | 2,2,1,1,3 | 4/5/1 |
| test/57 | 7,4,7,4,14 | 14/22/6 |
| test/1107 | 0,0,0,0,0 | 0/0/0 |

These illustrative cases are reused known sequences, not an accuracy benchmark.
Each detections.json retains all five entries, including empty arrays. For
test/1107, all five detections lists are [] from real inference, and the separate
annotation parser also reports no objects. Empty precision/recall/localization
are null with reasons where denominators/matches are absent; no fabricated
perfect-accuracy claim. train/84 is the multiple-candidate example.

Panels: raw_frames.png displays original pixels with display-only stretch;
candidates.png overlays image-only proposals in green; comparison.png uses the
separate inclusive5px matching layer (TP green, FP orange, missed label magenta).
Test/1107 candidate panel and train/438 comparison panel were visually inspected.
The existing gray-scale normalization/coordinate grid is unchanged for inference.

Known real failures: train/84 still has10 missed label positions; train/438 has18.
test/10 internal frame4 returns3 FP and misses its labeled target. test/57 frame4
has3 TP/11 FP/1 FN. These are real saved outputs/matches; streak fragments and
compact noise remain ambiguous, and faint/overlapping sources can be suppressed.
Do not infer physical identity from brightness/shape or annotation index.

## Exact detector callable, dependencies and output

```python
from astrotrace.datasets import SpotGeoDataset
from astrotrace.detection.interface import FrameContext
from astrotrace.detection.optimized import OptimizedConfig, OptimizedDetector, detect_optimized_sequence

config = OptimizedConfig(threshold_sigma=4.5, max_context_elongation=2.0).to_dict()
sequence = SpotGeoDataset("data/raw/SpotGEOv2", split="train").load_sequence(84)
frame = sequence.frames[0]
context = FrameContext(frame.frame_index, frame.width_px, frame.height_px,
                       "spotgeo", frame.timestamp_s)
one_frame = OptimizedDetector().detect(frame.pixels, context, config)
result = detect_optimized_sequence(sequence, config)
flat = [d for frame_result in result.frames for d in frame_result.detections]
```

`OptimizedDetector.detect(pixels: np.ndarray, context: FrameContext,
config: Mapping[str,object]) -> list[app.schemas.result.Detection]`.
`detect_optimized_sequence(sequence, config) -> SequenceDetections` is the existing
five-frame helper; no new detector interface was invented. Its local envelope
is not public SequenceInput or AnalysisResult. JSON consumers reconstruct each
existing Detection with `Detection.model_validate(d)`.

Inputs: native2D uint8/uint16 or finite normalized float32/64[0,1], nonempty and
bounded at4M pixels, exact context size/profile/frame index, finite timestamp or
None. Empty pixel arrays are invalid; valid images with zero detections return [].
All raw centroids retain fractional x/y in original-image pixels, top-left origin,
x right/y down, NumPy[y,x], integer pixel centers. Boxes have exclusive upper
limits. No shift/axis swap/resize/registration; reference fields remain null.
Unknown acquisition times remain null; no cadence is inferred.

Shared required fields remain detection_id/frame_index/x_raw_px/y_raw_px/
bbox_raw_px/kind/quality_score/detector_name, plus finite evidence and nullable
reference/endpoints. Envelope declares coordinate_system=
raw_top_left_xy_px_integer_centers, score_type=uncalibrated_heuristic.
IDs namespace sequence/frame/proposal rank; they do not track persistent objects.

Quality formula remains `(1-exp(-peak_snr_heuristic/8))/max(1,component_elongation)`.
It is a contrast/compactness heuristic, not calibrated probability or certified
debris confidence. Raw aperture SNR/shape are also uncalibrated. The exact selected
config is copied into detector_config.json: denoise .6, background8, noise12,
threshold4.5, area3..150, max_elongation2.5, cap200, background_step1,
max_peak_fraction.55, max_context_elongation2, max_component_aspect20,
min_aperture_snr0, min_score0. Bare class defaults differ; use this mapping.

Existing Python3.12.14 environment; installed runtime versions: NumPy2.5.3,
OpenCV headless4.14.0.94 (cv2 4.14.0), Pillow12.3.0, Pydantic2.14.0,
SciPy1.18.1 for separate scoring/tracking, pytest9.1.1. Read-only backend checks
use existing FastAPI/httpx dev setup. No dependency installation/lock modification.
Follow integration-owned SETUP for a new environment. Direct imports need src
and backend on PYTHONPATH; current backend packaging does not install astrotrace.
The CLI bootstraps both paths and sets one OpenCV CPU thread; library leaves
global thread settings alone. No YOLO/torch/GPU/learned weights are needed.

License attribution is preserved from prior installed metadata: OpenCV Apache2;
NumPy BSD plus bundled licenses; SciPy BSD/bundled notices; Pillow MIT-CMU;
Pydantic MIT. ESA spotGEO v2 attribution: Chen, Liu, Chin, Rutten, Derksen,
Maertens, von Looz, Lecuyer and Izzo; DOI10.5281/zenodo.4432143; publisher metadata
previously verified as CC BY4.0. Prefer dataset-relative references; samples and
panels remain local/ignored, original archive integrity remains unverified.

## Actual tracking compatibility and backend selection

Initial active checkout: tracking and registration packages are placeholders;
no actual Tracker import exists there. A later already locally fetched ref
`origin/feature/tracking-trajectory` resolves to
**8edb6ea778571b08db5cf7217a199dfe8fab9a2a** and contains Member3's real code.
Its T04/T05 docs have stale imports/methods; the actual source consumes
`app.schemas.result.Detection` and implements:

```python
Tracker.process_sequence(self, detections: Sequence[Detection],
                         frame_indices: Sequence[int] | None = None,
                         frame_timestamps: dict[int,float] | None = None) -> list[Track]
attach_trajectories(tracks, coordinate_frame="reference_frame_0", time_basis="frame",
                    prediction_horizon=2, frame_dimensions=None, frame_timestamps=None) -> list[Track]
```

Reuse the actual flat list above with `frame_indices=range(5)` so empty/trailing
frames advance lifecycle; timestamps remain unknown. CV-T05 reused CV-T06's
existing read-only source-snapshot loader, copied two unchanged Git blobs into
an ignored directory and invoked these interfaces on **actual saved sample
detections**. No fetched branch was checked out/merged, no tracking source was
modified, no fake tracker was substituted. Python disk access was blocked during
the tracker/trajectory calls; they received no labels.

| Actual real input | Detections/observations | Tracks | Confirmed | Trajectories |
|---|---:|---:|---:|---:|
| train/84 | 34/34 | 23 | 3 | 3 |
| train/438 | 27/27 | 26 | 0 | 0 |
| test/10 | 9/9 | 9 | 0 | 0 |
| test/57 | 36/36 | 35 | 0 | 0 |
| test/1107 | 0/0 | 0 | 0 | 0 |

All shared Track outputs serialize finitely, raw coordinates/frame/detection IDs
are preserved, real observations are neither lost nor fabricated, and trajectory
predictions are extrapolated with detection_id=None. These counts verify data
consumption, **not scientifically correct identities/ESA trajectory accuracy**.
Snapshot checksums:

- tracker.py: `34911026f4f21b47006ad5cb0c2893e9ca2b746ec3a7f1f11a35839edd3a57b3`
- fit.py: `fa4f02be0bd005c38d429132621f8dd4626bf4a3d860da068cf23791728b1658`

Coordinate limitation: actual `extract_detection_coords` falls back to raw x/y
when reference fields are null. ESA camera orientation changes between frames;
that is not measured registration or an established common frame. Minimal required
correction is image-derived registration and an explicit raw/reference failure
policy agreed by registration/tracking/integration owners, not a shared Detection
schema change. Old handoff examples using app.schemas.sequence.Detection,
TrackerConfig, update/finalize or TrajectoryEstimate must use actual source APIs.

Current team-lead selection report:

- **Standalone backend detection adapter:** externally authored
  `orbittrace.detection.detect_sequence(...,method="optimized")` defaults to
  frozen CV-T04; `method="baseline"` keeps T03 available. It returns flat shared
  Detection objects; scientific fields match original CV-T04, IDs use its own
  namespace. See the separate CV_TO_TRACKING handoff for that implementation.
- **Backend public/API pipeline:** selects **neither**. Actual pipeline.analyze
  raises T07 NotImplementedError. Health returns200/bootstrap_only with
  detection/tracking/analysis false; POST/api/analyze/demo returns404/not_found.
  These read-only calls verify current absence, not successful API integration.
- **Active checkout tracker:** unavailable. Snapshot consumption is tested,
  canonical installed import/pipeline wiring and valid reference registration
  remain unverified. Backend selection logic was not edited by CV-T05.

## Fixed-config generalization evidence and its limits

A genuinely independently blind set cannot be established from repository
provenance. All32,000 images and annotation schema were previously audited, and
broader human/external exposure or capture-session independence is unknown.
**Independent blind validation is not available.** Prior CV-T04 measurements
remain regression evidence, not a fresh blind test.

An additional128-sequence official test subset was uniformly sampled with
seed20261009 after excluding156 known-used split-scoped sequences (prior tuning,
scoring and presentation examples). IDs/config/code hashes were written before
selected image/label inspection. Every selected PNG matched the previous full
manifest; zero exact-byte overlap with known-used frames; no reselection/tuning.
Inference finished with file-access guards before annotations were loaded for
matching. This is **recorded-use-disjoint supplemental evaluation**, not an
independent blind-validation claim or a new model/configuration.

| Current supplemental measurement | Actual value |
|---|---:|
| Sequences / frames / labels | 128 / 640 / 1,155 |
| TP / FP / FN | 706 / 911 / 449 |
| Precision | 43.6611% |
| Recall | 61.1255% |
| F1 | 50.9380% |
| Matched mean localization error | 0.2716 px |
| Matched localization RMSE | 0.3355 px |
| False positives/frame | 1.42344 |
| Empty frames / FP per empty frame | 165 / 1.21212 |
| Mean / p95 detect time | 63.3727 / 97.0744 ms |

Same existing inclusive5px maximum-cardinality/minimum-distance one-to-one
raw-pixel protocol; pooled counts include empty scenes, localization is matched
only, undefined denominators are null. It is not official ESA challenge scoring
or a tracking metric. Timing is one OpenCV thread, actual detect calls including
preprocessing/schema, excluding image IO/wrapper/scoring/guard setup. Single
observed wall-time run; package verification overlapped startup and normal local
activity was not isolated. No direct speedup comparison to71.84ms is supported.
Environment: Windows11 build26300, Python3.12.14, Intel64 Family6 Model151
Stepping2 GenuineIntel (actual platform processor string, not invented CPU SKU).

Reproducibility hashes:

- sample manifest: `42867f69dcf3724993ee7453d0303a072487e3e564c6270290a78559d87a1a60`
- package numeric config: `aeffd97594ffcdb40aa056265d9f577473a8c47022d75333917b55b4a3f10b3a`
- original CV-T04 selected config: `66f47213bb37ddd825565cd405a43e694d0e8274b4ab834883d82986c78e976b`
- final membership: `bf4c84f3599ece488a6336e43a08a13d146190a17947b056f46200651d842b72`
- final benchmark: `cb890f32f9bfec30667d7449ef466af7c4b57b8a43c62ac6a1208cbf8e3fa414`

Evaluation/package manifests record their actual harness SHA at invocation. The
owned harness later gained optional tracking-ref/current-adapter inspection
commands after the fetched source became available; detector/preprocessing/config
hashes stayed unchanged. The supplemental set was not reevaluated or tuned after
seeing these metrics. Benchmarks and historical provenance were not overwritten.

## Commands run, actual tests and execution instructions

All Python commands used `.\.venv\Scripts\python.exe` from E:\Fusion.

| Command/check | Actual outcome |
|---|---|
| Required documentation/source inspection, git status/HEAD, current tracking/backend imports | Existing work preserved; initial tracking/pipeline placeholders identified |
| `scripts/spotgeo_handoff.py package --output artifacts/reports/cv_t05_member3` | Exit0; five real sequences,25 verified frames, actual JSON/raw/candidate/comparison panels |
| `-m pytest -q -c backend/pyproject.toml tests/detection/test_handoff.py` | **16 passed,0 failed in1.41s**, one existing Starlette/httpx warning |
| `scripts/spotgeo_handoff.py verify --package artifacts/reports/cv_t05_member3` | Exit0; all25 frames and saved detections reproduced, no inference annotation access |
| `scripts/spotgeo_handoff.py final-evaluate --count 128 --seed 20261009 --output artifacts/reports/cv_t05_final_evaluation` | Exit0;640 unchanged pixels, frozen disjoint membership, actual metrics above |
| First full `-m pytest -q -c backend/pyproject.toml` while concurrent CV-T06 tests appeared | **226 passed,6 skipped,0 failed in48.15s**, one dependency warning; skipped tracking cases required unavailable active-checkout modules |
| `scripts/spotgeo_handoff.py inspect-integration --output artifacts/reports/cv_t05_integration_probe` | Exit0; actual fail-closed pipeline/health/unavailable route evidence |
| Local refs plus `git show origin/feature/tracking-trajectory:...` source and handoffs | Existing fetched Member3 commit/interface found; no network fetch/checkout |
| `scripts/spotgeo_handoff.py verify-tracking-ref --package artifacts/reports/cv_t05_member3 --ref origin/feature/tracking-trajectory --output artifacts/reports/cv_t05_tracking_snapshot` | Exit0; all5 actual sample Detection-to-Track/trajectory data-consumption cases passed |
| `scripts/spotgeo_handoff.py inspect-integration --output artifacts/reports/cv_t05_integration_current` | Exit0; CV-T04 standalone adapter available/default, public pipeline still selects neither |
| Full pytest with CV_T06_TRACKING_SNAPSHOT set to CV-T05 snapshot | **235 passed,0 failed,0 skipped in44.14s**, one existing Starlette/httpx warning; includes concurrent worker tests, not235 newly authored CV-T05 tests |
| Compile new harness/test | Exit0 |
| Original `OpenCVBaselineDetector` through `detect_sequence` on real train/84 with Path.open blocked during inference | Exit0; frames0..4 and [7,15,13,13,11] candidates; T03 remains callable |
| `python scripts/check_docs.py` | 67 local links in57 Markdown files resolved |
| Owned whitespace/link/source-preservation audit | 5 CV-T05 files,19 owned-document links,0 issues; original T03/CV-T04 and inspected protected source hashes unchanged; final membership disjoint |
| `python -m pip check` | No broken requirements found |
| `git diff --check` and result ignore check | Passed; only existing PROBLEM_STATEMENT line-ending notice; generated package/benchmark/compatibility ignored |

The16 new CV-T05 tests verify actual detector/schema round trips for empty and
multiple outputs, forbidden inference file access, wrong frame/coordinate/score/
tracking metadata, nonfinite coordinates, out-of-image boxes, unintended reference
coordinates, duplicate IDs, deterministic disjoint selection and read-only backend
absence evidence. Existing detector/loading/contracts and external adapter/snapshot
compatibility tests are retained. No successful test count is copied from a prior
milestone as current evidence; the warning is the existing Starlette httpx
deprecation, not a test failure.

Exact Windows PowerShell reproduction commands (new output names avoid overwrite):

```powershell
Set-Location E:\Fusion
$env:PYTHONPATH = 'E:\Fusion\src;E:\Fusion\backend'
$cvT05Run = Get-Date -Format 'yyyyMMdd-HHmmss'
$cvT05Package = "artifacts/reports/member3_$cvT05Run"
$cvT05Tracking = "artifacts/reports/tracking_$cvT05Run"
.\.venv\Scripts\python.exe scripts/spotgeo_handoff.py package --source data/raw/SpotGEOv2 --output $cvT05Package
.\.venv\Scripts\python.exe scripts/spotgeo_handoff.py verify --source data/raw/SpotGEOv2 --package $cvT05Package
.\.venv\Scripts\python.exe scripts/spotgeo_handoff.py verify-tracking-ref --package $cvT05Package --ref 8edb6ea778571b08db5cf7217a199dfe8fab9a2a --output $cvT05Tracking
$env:CV_T06_TRACKING_SNAPSHOT = Join-Path (Get-Location) "$cvT05Tracking/tracking_snapshot"
.\.venv\Scripts\python.exe -m pytest -q -c backend/pyproject.toml
.\.venv\Scripts\python.exe scripts/spotgeo_handoff.py inspect-integration --output "artifacts/reports/integration_$cvT05Run"
.\.venv\Scripts\python.exe scripts/spotgeo_handoff.py final-evaluate --source data/raw/SpotGEOv2 --count 128 --seed 20261009 --output "artifacts/reports/final_$cvT05Run"
```

No automatic installation/fetch occurs. The tracking snapshot command requires
the already available local Git commit and the separately authored CV-T06 loader;
if absent, canonical tracking integration remains blocked, do not fabricate a
replacement. The fresh set is consumed now: rerunning these same IDs is a
reproduction/regression check, not another fresh test. No future tuning on it.

View saved results and genuine images:

```powershell
Invoke-Item .\artifacts\reports\cv_t05_member3\train_84\raw_frames.png
Invoke-Item .\artifacts\reports\cv_t05_member3\train_84\candidates.png
Invoke-Item .\artifacts\reports\cv_t05_member3\test_57\comparison.png
Invoke-Item .\artifacts\reports\cv_t05_member3\test_1107\candidates.png
Get-Content .\artifacts\reports\cv_t05_member3\test_1107\detections.json
Get-Content .\artifacts\reports\cv_t05_final_evaluation\benchmark.json
Get-Content .\artifacts\reports\cv_t05_integration_current\integration.json
Get-Content .\artifacts\reports\cv_t05_tracking_snapshot\compatibility.json
```

Further instructions/module inputs/outputs:
[Member 3 guide](../../src/astrotrace/detection/MEMBER3.md),
[actual Member3 package manifest](../../artifacts/reports/cv_t05_member3/samples.json),
[supplemental benchmark](../../artifacts/reports/cv_t05_final_evaluation/benchmark.json),
[current backend probe](../../artifacts/reports/cv_t05_integration_current/integration.json),
[snapshot compatibility](../../artifacts/reports/cv_t05_tracking_snapshot/compatibility.json),
[separate CV-T06 interface handoff](CV_TO_TRACKING.md).

## Readiness decision and next task

**Ready for Member3 as a verified standalone shared-Detection source**, with five
reproducible real examples, genuine empty output and actual snapshot data
consumption evidence. T03 and CV-T04 both work locally; no learned model is trained
or required. Actual installed/public backend integration is **not verified or
implemented**, despite the standalone adapter's availability.

Outstanding blockers: transfer/version the uncommitted src work and package it
through integration review; install/merge Member3 source deliberately; estimate
image-derived registration and agree raw-fallback failure semantics; implement
T07/API storage/pipeline/health selection explicitly. Current raw-fallback tracks
are diagnostic, and identity/trajectory accuracy has not been established.

Recommended next task: integration owner wires the existing adapter and Member3
Tracker with explicit frame indexes/config and registration status, then reruns
an actual image-to-API end-to-end test. Tracking/registration owners audit common-
frame transform direction and failures. Retain current detector checkpoints;
faint/overlap/near-border misses, residual noise/streak FP and runtime need a
new properly governed validation set, not tuning on this now-used final subset.
No shared schema change is requested and no out-of-scope modification was made.
