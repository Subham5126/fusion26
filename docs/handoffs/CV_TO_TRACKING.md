# Handoff: CV-T06 — detector-to-tracking compatibility

Owner: Computer Vision & Dataset Engineer, explicitly assigned by the user.
Backlog ownership: continuation of **T03 / Data-CV**. CV-T06 is this compatibility
milestone, not BACKLOG T06 (evaluation).
Base commit: `fa593cf5052f96d311d049f2b84949f588a99407`, checkout `main`.
Date: 9 October 2026, Asia/Calcutta.
State: **ready_for_review**. Adapter and actual detector-to-tracker compatibility
implemented and tested. Backend packaging, pipeline/API integration and valid
real-sequence registration remain pending with their owners.

## Repository mismatch: actual evidence

- Initially `git branch -avv` listed only local `main` and fetched `origin/main`,
  both at `fa593cf`. `git worktree list --porcelain` showed only `E:/Fusion`.
- T03/CV-T04 implementations are **untracked**, under `src/astrotrace/detection/`
  and `src/astrotrace/preprocessing/`. Their handoffs, dataset modules, scripts and
  detection tests also remain uncommitted. `git ls-files src` returned no files.
  `git check-ignore -v` did not report the detector Python files as ignored.
  A teammate checking out a Git branch cannot receive uncommitted local files.
- The committed backend detection/tracking/trajectory packages on local `main`
  contained only `__init__.py` placeholders. The detectors were implemented in a
  different package, not absent from this working directory.
- `backend/pyproject.toml` discovers only `app*` and `orbittrace*` under backend.
  It does not install `src/astrotrace`, even with editable backend installation.
  A real import with only backend on PYTHONPATH failed with
  `ModuleNotFoundError: No module named 'astrotrace'`.
- `git ls-remote --heads origin` revealed `Rohit`, `Subham`, `Yogesh`,
  `development` and `main` at `fa593cf`, plus **feature/tracking-trajectory** at
  `8edb6ea778571b08db5cf7217a199dfe8fab9a2a`. A bounded fetch of that one branch
  made `origin/feature/tracking-trajectory` available for inspection; it contains
  the completed tracker/trajectory, but no `src/astrotrace` or detector algorithm.
- Actual source imports **`app.schemas.result.Detection`**, as do T03/CV-T04.
  No schema/package translation is needed. Member 3's T04/T05 handoff examples
  are stale: `app.schemas.sequence.Detection`, `TrackerConfig`, `update()`,
  `finalize()` and `TrajectoryEstimate` do not describe the inspected source.
  Use the exact interfaces below.

No local commit, branch/worktree creation, checkout, merge, push, installation,
training, dataset download or deployment occurred. Fetch retrieved existing Git
objects/ref information only. Shared schema/config/lock files were not changed.

## Ownership and exact changes

[TEAM](../TEAM.md), [Data-CV role](../agents/DATA_CV_AGENT.md), root AGENTS and
BACKLOG T03 assign `backend/orbittrace/detection/` and corresponding tests to CV.
The user's instructions permit implementing the adapter there if ownership allows.
No approval to change another member's implementation was needed or inferred.

Created:

- [backend/orbittrace/detection/adapter.py](../../backend/orbittrace/detection/adapter.py)
- [backend/orbittrace/detection/example.py](../../backend/orbittrace/detection/example.py)
- [tests/detection/test_adapter.py](../../tests/detection/test_adapter.py)
- [tests/detection/test_tracking_compatibility.py](../../tests/detection/test_tracking_compatibility.py)
- This file: `docs/handoffs/CV_TO_TRACKING.md`

Changed:

- [backend/orbittrace/detection/__init__.py](../../backend/orbittrace/detection/__init__.py): exports bridge callables and FrameContext.

Preserved: T03/CV-T04 algorithms, preprocessing, historical tests/scripts/handoffs,
shared schemas, tracking/trajectory source, configs, dependencies, STATUS/BACKLOG
and the pre-existing PROBLEM_STATEMENT edit. SHA-256 snapshot checked 62 existing
files; all 47 existing Python files stayed byte-identical. One detector README
changed externally during this run; it was not edited/reverted by CV-T06.
Concurrent `scripts/spotgeo_handoff.py` and `tests/detection/test_handoff.py`
additions were also observed and left alone.

Local generated evidence, already ignored by Git:

- `artifacts/reports/cv_t06/preservation_before.json`
- [preservation_audit.json](../../artifacts/reports/cv_t06/preservation_audit.json): original/current source hashes and installed dependency versions.
- `train_84/`: retained incomplete first example run, **not passing evidence**.
- `train_84_v2/`, `test_57/`, `test_1107/`: each contains `detections.json`,
  `candidates.png`, `tracking_result.json`, and `tracking_snapshot/{tracker.py,fit.py}`.
  Snapshot files are exact Git bytes, not edited replacements or merge candidates.

## Exact imports and callable contracts

```python
from app.schemas.result import Detection
from orbittrace.detection import FrameContext, detect_frame, detect_sequence

# These canonical tracker imports work after Member 1 integrates Member 3's source.
from orbittrace.tracking.tracker import Tracker
from orbittrace.trajectory.fit import attach_trajectories
```

```python
detect_frame(pixels, context, config=None, *, method="optimized", sequence_id="sequence")
# -> list[app.schemas.result.Detection]

detect_sequence(frames, *, sequence_id, profile="spotgeo", timestamps_s=None,
                config=None, method="optimized")
# -> flat list[app.schemas.result.Detection], ordered by frame then proposal rank
```

`frames` is an explicit ordered list/tuple of native grayscale NumPy arrays, not
paths, URLs, a public request, or a truth-bearing dataset object. The kernel accepts
0..30 frames; the public unchanged SequenceInput still requires 3..30. Dimensions
must agree. Images are nonempty 2D uint8/uint16 or finite float32/64 in [0,1],
bounded at 4,000,000 pixels each. Zero-target/constant frames produce no detections;
an empty pixel array is invalid. All supplied timestamps must be finite, strictly
increasing seconds, or all unknown. No cadence is inferred from ESA filenames.

The bridge delegates directly to `OpenCVBaselineDetector.detect()` or
`OptimizedDetector.detect()`. It revalidates returned Detection objects, bounds
their boxes against actual frame dimensions, checks frame/name and applies a
deterministic namespace. No algorithms, shared models or coordinate transforms
were copied/reimplemented. Raw/reference values and evidence are unchanged.

IDs are `s<hash(sequence_id/detector_name)>-f<frame_index>-c<rank>`: unique across
all proposals in a sequence, stable on repeat calls, distinct across detector
methods. Use distinct contract-compatible sequence IDs, e.g. `train-84` versus
`test-84`, when combining sequences. IDs do **not** establish persistent identity.
Boxes have exclusive upper bounds, may end at width/height, and contain the
finite fractional raw centroid. Kind/name are preserved; quality is [0,1] and
uncalibrated. Reference coordinates remain null until registration provides them.

`method="baseline"` uses unchanged BaselineConfig defaults unless overridden.
`method="optimized"` uses the frozen CV-T04 settings: OptimizedConfig with
`threshold_sigma=4.5`, `max_context_elongation=2.0`, other original class settings
unchanged (including denoise .6, background 8, noise 12, area 3..150, elongation
2.5, max_peak_fraction .55, background_step 1, cap 200).
Explicit config values override that selection and are checked by the original
config class; unknown/truth/path keys are rejected. This differs intentionally
from constructing bare OptimizedConfig(), whose threshold/context defaults are
5.5/2.5. Nothing reads an ignored selected_config.json during inference.
CandidateLimitWarning propagates on truncation; final cap is 1..2000 per frame,
with the preserved optimized detector's separate 2000-proposal work ceiling.

## Small reproducible integration example

```python
from astrotrace.datasets import SpotGeoDataset
from orbittrace.detection import detect_sequence
from orbittrace.tracking.tracker import Tracker
from orbittrace.trajectory.fit import attach_trajectories

sequence = SpotGeoDataset("data/raw/SpotGEOv2", split="train").load_sequence(84)
frames = [f.pixels for f in sequence.frames]
detections = detect_sequence(frames, sequence_id="train-84")
tracks = Tracker().process_sequence(detections, frame_indices=range(len(frames)))
tracks = attach_trajectories(tracks, coordinate_frame="raw", time_basis="frame",
                            frame_dimensions=(640, 480))
```

This is a **raw-fallback compatibility diagnostic** for ESA, not a validated
common-frame trajectory. Always provide every frame index, including empty and
trailing empty frames; otherwise tracker lifecycle cannot see those misses.
Alternatively use `Tracker.process_frame(index, detections_for_that_frame,
timestamp_s=known_time_or_None)` sequentially. Start/reset a tracker for each
sequence. For known times pass `frame_timestamps={index: seconds}` to tracking,
and `time_basis="second"` plus the same mapping to trajectory attachment.
Detection itself has no timestamp field. Predictions never re-enter detection.

## Real data and actual measured outputs

All three runs loaded five original ESA PNGs and **no annotations**. The real
compatibility test compares every non-ID Detection field to unchanged CV-T04,
then runs actual tracker/trajectory functions and validates AnalysisResult,
same-frame observation references and no invented prediction detection IDs.

| Split/sequence | Candidates per frame | Tracks | Confirmed | Trajectories | Compatibility |
|---|---|---:|---:|---:|---|
| train/84 | 7,7,6,8,6 | 23 | 3 | 3 | passed |
| test/57 | 7,4,7,4,14 | 35 | 0 | 0 | passed |
| test/1107 | 0,0,0,0,0 | 0 | 0 | 0 | passed |

These track counts measure code behavior under the raw-coordinate fallback,
not association accuracy, debris identity or scientific trajectory validity.
No registration was attempted; diagnostic JSON marks registration unavailable
(`failed`) with an explicit warning. Unknown timestamps remain null; units are
px/frame. `metrics` stays null. A zero-candidate scene does not prove zero targets.

Actual first train/84 candidate:

```json
{
  "detection_id": "saf4470bba67a858a-f0-c0",
  "frame_index": 0,
  "x_raw_px": 61.35224346723875,
  "y_raw_px": 427.97201121585204,
  "bbox_raw_px": [59.0, 426.0, 65.0, 431.0],
  "kind": "compact",
  "quality_score": 0.8320982666451765,
  "detector_name": "opencv_context_filtered_v2",
  "x_reference_px": null,
  "y_reference_px": null
}
```

Tracker source tested: commit `8edb6ea778571b08db5cf7217a199dfe8fab9a2a`.
SHA-256: tracker `34911026f4f21b47006ad5cb0c2893e9ca2b746ec3a7f1f11a35839edd3a57b3`;
trajectory `fa4f02be0bd005c38d429132621f8dd4626bf4a3d860da068cf23791728b1658`.
Shared schemas/config on that branch match local main (Git diff was empty).
Frozen optimized config canonical-JSON SHA-256 is
`50e48c61052883ad8a2b8906911d931001652cb6cb8c688d8e14f39c70a61595`;
15 source PNG hashes are recorded across the three detections.json files.

T03 and optimized CV-T04 are working CPU OpenCV heuristics. There is no trained
neural model/checkpoint or training claim. Existing benchmark.json was inspected:
historical CV-T04 precision 39.2397%, recall 58.7156%, F1 47.0415%, FP/frame
1.5484375 on 640 frames. These are preserved checkpoint measurements, **not a
fresh accuracy evaluation from CV-T06**. No further tuning occurred.

## Actual commands, outcomes and failures

All Python commands used the existing `.\.venv\Scripts\python.exe`, Python
3.12.14. No packages were installed. Installed versions: NumPy 2.5.3,
opencv-python-headless 4.14.0.94, SciPy 1.18.1, Pillow 12.3.0, Pydantic 2.14.0,
pytest 9.1.1. Existing package metadata was inspected: NumPy multi-license,
OpenCV Apache 2.0, SciPy BSD with bundled notices, Pillow MIT-CMU, Pydantic MIT.
No new external code/weights were adopted; ESA rights remain as documented in
T03/T14, and these local panels/pixels are not committed for redistribution.

| Check run | Outcome |
|---|---|
| Git status/branches/worktrees/tracked files/ignore checks and remote-head listing | Confirmed mismatch above |
| `git fetch --no-tags origin feature/tracking-trajectory`, `git show`, schema/config diff | Read actual Member 3 source; same shared schema |
| Initial `pytest ... tests/detection/test_adapter.py` | 35 passed in .37s |
| Initial example train/84 | Failed: invalid authored registration status `not_requested`; fixed locally to existing `failed` plus warning, no schema edit |
| Example train/84 rerun at train_84_v2 | Passed, 34 detections consumed by untouched tracker/trajectory |
| Example test/57 and test/1107 | Both passed, 36 and 0 detections consumed |
| Initial full pytest | 231 passed, 1 failed: incorrectly authored test/57 expected counts; output already matched unchanged CV-T04; expectation corrected to actual 7,4,7,4,14 |
| Updated detection suite | 209 passed, 1 existing warning in 30.96s |
| Final full pytest with snapshot configured | **235 passed, 0 failed, 0 skipped**, 1 existing warning in 44.73s |
| `python -m pip check` | No broken requirements |
| `compileall -q` on new detector modules/tests | Exit 0 |
| Backend-only PYTHONPATH import probe | Expected integration gap: ModuleNotFoundError for astrotrace |
| Preservation hash audit | All 47 existing Python files unchanged; separate concurrent README edit retained |
| Candidate panel inspection | train/84 five-frame green overlays inspected; native scientific coordinates preserved; contrast is display-only |
| Final `python scripts/check_docs.py` | 61 local links in 56 Markdown files resolved |
| Final `git diff --check` and generated-output ignore checks | Passed; existing PROBLEM_STATEMENT line-ending notice only; evidence stays ignored |

The one upstream Starlette/httpx deprecation warning is existing. Candidate-cap
warnings are intentional and asserted in tests; none occurred in the three real
example runs. Real example timings were recorded but are not comparable latency
benchmarks (two examples ran concurrently).

Tests cover direct-frame index, full-sequence uniqueness, different sequence/method
namespaces, exact preserved geometry/evidence, last-pixel exclusive boxes, finite
JSON/quality/kind/name, wrong returned frame/name/geometry rejection, caps and
warnings, constant/empty/gap frames, memory-only inference/no truth keys, invalid
images/config/dimensions/timestamps, and both frame/second trajectory modes.
The synthetic moving Gaussian sequence contains four actual observations and one
blank frame; unchanged tracking preserves one confirmed track with observations
at 0,1,3,4 and two separate predictions at 5,6.

## Exact Windows PowerShell reproduction

From the project root, use a fresh output directory for every example run; the
runner refuses to overwrite existing evidence.

```powershell
Set-Location E:\Fusion
$env:PYTHONPATH = 'E:\Fusion\src;E:\Fusion\backend'
git fetch --no-tags origin feature/tracking-trajectory
$cvT06Run = 'artifacts/reports/cv_t06/reproduce_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
.\.venv\Scripts\python.exe -m orbittrace.detection.example --split train --sequence 84 --output $cvT06Run --tracking-ref 8edb6ea778571b08db5cf7217a199dfe8fab9a2a
if ($LASTEXITCODE -ne 0) { throw 'CV-T06 real compatibility run failed' }
$env:CV_T06_TRACKING_SNAPSHOT = (Resolve-Path ($cvT06Run + '/tracking_snapshot')).Path
.\.venv\Scripts\python.exe -m pytest -q -c backend/pyproject.toml
.\.venv\Scripts\python.exe -m pip check
```

To run only the new boundary/compatibility tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -c backend/pyproject.toml tests/detection/test_adapter.py tests/detection/test_tracking_compatibility.py
```

After Member 3 modules are integrated, remove `CV_T06_TRACKING_SNAPSHOT` from the
environment to test the canonical installed imports. Without available modules
and without a snapshot, compatibility tests explicitly skip; **a skipped run does
not establish integration**. Real tests also explicitly skip without the local
ESA data. Set `CV_T06_REAL_SOURCE` to another extracted ESA root if needed.

View newly reproduced outputs:

```powershell
Invoke-Item ($cvT06Run + '/candidates.png')
Get-Content ($cvT06Run + '/detections.json')
Get-Content ($cvT06Run + '/tracking_result.json')
```

Existing passed outputs: [train/84 candidates](../../artifacts/reports/cv_t06/train_84_v2/candidates.png),
[detections](../../artifacts/reports/cv_t06/train_84_v2/detections.json),
[tracking diagnostic](../../artifacts/reports/cv_t06/train_84_v2/tracking_result.json).
Green marks are detections only; the panel does not show tracks or labels.

## Member 3 consumption and Member 1 integration actions

Member 3 **can consume the adapter now when the source files are transferred and
both source roots are importable**; the actual remote tracker was tested on fresh
real detections. No manual dict-to-schema conversion is needed. This is local
compatibility acceptance, not a completed merge or public backend service.

Member 1 should review and integrate the existing untracked `src/astrotrace`
tree (dataset/preprocessing/detection imports are interconnected), its owned
tests/scripts and T03/CV-T04 handoffs, plus the six CV-T06 files listed above.
Include Member 3's tracking/trajectory changes from the inspected branch through
the team's review policy. Do not copy generated ESA data, report snapshots or
virtual environments into Git. Inspect the working tree and selectively stage
reviewed source; the pre-existing PROBLEM_STATEMENT edit is unrelated.

Integration owns the remaining distribution decision: ship src alongside backend
with both import roots in launch/test configuration, or package astrotrace in a
reviewed installable project. Current backend package discovery alone is
insufficient. Verify a clean teammate checkout, not only this existing venv.
No shared dependency additions or schema changes are requested by the adapter.

Then wire T07 pipeline image arrays into `detect_sequence`, preserving full frame
metadata, cap warnings and image-derived registration state. Call the actual
Tracker/trajectory APIs above; retain null unknown timestamps, observed IDs,
raw/reference transforms and finite JSON. Update root config, capability flags,
STATUS/BACKLOG only after the reviewed pipeline/API behavior is tested.
The current pipeline remains a placeholder and the analysis API is not enabled
by this detector bridge.

Specific next dependency: **Member 1 / T07** packaging and detector–tracker
pipeline wiring; **CV / T13** image-derived registration validation before any
real common-frame trajectory claim. Preserve the frozen CV-T04 benchmark rather
than tuning further on its held-out samples. Synthetic end-to-end P0 remains
the recommended integration checkpoint; real association accuracy, scientific
calibration, identity and physical/orbital quantities are not established here.
