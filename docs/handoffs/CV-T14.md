# Handoff: CV-T14 — judge feedback robustness

OrbitTrace / FUSION SPACE-02, Member2 Computer Vision & Dataset Engineer.
Backlog continuation: Data/CV T10/T13/T14; user-assigned CV-T14 robustness scope.
Base commit c802622800ed14739bd841ee840ec16cf905e4cd; branch **Subham**.
9 October 2026 (Asia/Calcutta). Implemented/tested local CV utilities and
read-only tracking integration. API adoption/model training are planned/blocked,
not implemented. No commit/push/merge/rebase/reset or dataset download performed.

## Exact CV-T14 files created

No pre-existing file was edited by this task. Eleven new reviewable source/docs:

1. src/astrotrace/preprocessing/suitability.py
2. src/astrotrace/preprocessing/ROBUSTNESS.md
3. src/astrotrace/datasets/stress.py
4. src/astrotrace/datasets/inventory.py
5. src/astrotrace/detection/stress_evaluation.py
6. scripts/spotgeo_robustness.py
7. scripts/spotgeo_inventory.py
8. tests/detection/test_robustness.py
9. docs/handoffs/CV-T14.md
10. docs/handoffs/CV-T14-JUDGE.md
11. docs/handoffs/CV-T14-DATASETS.md

Preserved existing uncommitted CV-T13 registration modules, fixtures,
visualization/script/tests/docs and preprocessing README, unrelated
docs/PROBLEM_STATEMENT.md and all old results. Nine protected source/document
hashes recorded before work in artifacts/reports/cv_t14/preservation_before.json.
Final preservation/source/Git audit is artifacts/reports/cv_t14/audit.json.
Root configs, dependencies, packaging, schemas, backend, tracking and frontend
were not modified. T03/CV-T04 algorithms and CV-T06 adapter remained unchanged.

During work, unrelated new untracked Ultralytics/, experiments/, tests/yolo/ and
docs/handoffs/CV-T15.md
appeared from another workstream. They were preserved, not authored or edited by
CV-T14; extra tests were included by full-root pytest discovery. Check current
Git status before any future staging; this file list is not a blanket allowlist
for all untracked files. Nothing was staged.

## Implementation and input/output

- Pixel-only suitability rules produce supported/unsupported/uncertain,
  reason codes, explanations and finite metrics. Multi-quantile/occupancy profile
  mismatch, clipping, feature count, noise, blur and sequence consistency;
  never a mean-only daylight detector or physical identity classifier.
- Deterministic seed14 five-frame uint8 scenes with separate visibility,
  track-ID, bbox, point and transform truth; 11 named cases with real rendered
  inference. Background stars/artifacts, gaps, entry/exit, exact crossing, nearby
  pairs, camera shifts, blank/noise/daylight-like/blurred examples.
- Independent post-inference native-point matcher and association diagnostics.
  Truth never passed to detector/registration/tracker. Inference I/O guard test
  forbids open/Path.open; geometry tests verify unchanged raw pixels/coordinates.
- Read-only wider inventory audits all headers, streak/CSV labels and non-ESA
  encoded SHA256 duplicates. No auto-repair, copying or training.
- Local runner snapshots actual Member3 source from an already fetched Git
  commit, runs frozen CV-T04 and T13, validates schema AnalysisResult, saves
  actual candidate/observed-track/star overlays and structured offline reports.

Public detector contract unchanged:

```python
from orbittrace.detection import detect_sequence
from astrotrace.preprocessing.suitability import validate_sequence_suitability
from astrotrace.preprocessing.registration import register_sequence, add_reference_coordinates

assessment = validate_sequence_suitability(frames)
if assessment['status'] != 'supported':
    raise ValueError(assessment['explanations'])  # expose review/reacquisition
raw = detect_sequence(frames, sequence_id='demo', method='optimized')
registration = register_sequence(frames)
if registration.status == 'failed':
    raise ValueError('Registration failed; do not mix raw/reference tracking')
observations = add_reference_coordinates(raw, registration)
tracks = Tracker().process_sequence(observations, frame_indices=range(5))
```

`detect_sequence(frames, *, sequence_id, profile='spotgeo', timestamps_s=None,
config=None, method='optimized') -> list[Detection]`, five same-size native
grayscale arrays here. Score heuristic `(1-exp(-peak_snr/8))/max(1,elongation)`;
quality is not calibrated probability. Default optimized adapter threshold_sigma
4.5, max_context_elongation 2.0, remaining CV-T04 config unchanged. All parameters
recorded in final_review/summary.json. Per-frame detection IDs are not object IDs.

Raw origin top-left, x right/y down, integer pixel centers with subpixel values;
bounding boxes exclusive upper limits. `raw_to_reference` subtracts frame camera
shift. T13 bridge only adds paired reference fields; all raw fields preserved,
reference coordinates not clipped. No timestamps/cadence or physical speed invented.
Input-format bounds, exact module calls/thresholds, output artifacts, heuristic
metric definitions and limitations: src/astrotrace/preprocessing/ROBUSTNESS.md.

Member3 source tested at a015cc949955d0438c8a16789b23746c3206f3d1:

- tracker.py SHA256 34911026f4f21b47006ad5cb0c2893e9ca2b746ec3a7f1f11a35839edd3a57b3
- fit.py SHA256 fa4f02be0bd005c38d429132621f8dd4626bf4a3d860da068cf23791728b1658

Actual constructor and PipelineConfig defaults are **20px**, confirmation=3
observations, retirement after >2 misses. CV-T13's default15 statement is a
documentation error; original T13 files preserved. No tracking gate modified.

## Data actually accessed and evidence

Fully decoded 15 real PNGs in E:\Fusion\data\raw\SpotGEOv2:
train/84, train/438, test/1107, official frames1..5. SHA256s in final_review/
summary.json. Existing integration tests additionally load train/84, test/57 and
test/1107 (20 distinct real PNGs across run+tests). These are previously used
diagnostics; no new blind real test or threshold tuning performed.

Inventory: all 32,000 ESA headers, 2,388 streak headers/labels, 20,000 train,
2,000 val and 5,000 test JPEG headers, train.csv/val.csv, 10 existing authored
synthetic headers under data/synthetic. Full inventory outcomes and training
blockers: CV-T14-DATASETS.md. One representative streak JPEG and train/0.jpg also
visually decoded. No complete wider-source decoding claim or rights adoption.

New 55 synthetic 320x240 PNGs are stored separately in ignored reports, never
mixed into real ESA metrics. Suitability agreements: 11/11 controlled sequence
labels, **not independent real validation accuracy**. All 3 selected ESA sequences
supported. Adequate labelled real daylight/cloud/non-astronomical negatives absent.

Authoritative final evidence: artifacts/reports/cv_t14/final_review/.
Earlier probe/probe2/final/accepted_v1/review directories remain preserved as
development evidence; use final_review for current output shape and measurements.
Daylight-like unsupported inference has null detections/counts, not empty success.
Uncertain noise/blank/blurred bypass is explicit diagnostic-only; normal processing
would block. Registered mode never processes a partially failed sequence.

## Actual stress results

Details/denominators in CV-T14-JUDGE.md and per-case report.json. Point gate 5px
inclusive; coincident truths within1px excluded from identity scoring; no predicted
points scored. All numbers below come from actual CV-T04/Member3 outputs.

- Counts [5,3,4,5,5]: 22TP/0FP/0FN, 5 confirmed tracks, 17 correct links/0 wrong,
  0 switches/fragmentation, both one/two-frame gaps recovered. Both raw/ref modes.
- Camera shifts (18,8)px/frame: 25TP/4FP/0FN, raw29 tracks and20 switches/fragments;
  registered9 tracks (5 confirmed) and0 switches/fragments. Max known synthetic
  translation error0.0083895px; same actual20px gate. This is not real accuracy.
- Entry/exit:10TP/0FP/0FN,3 tracks (2 finally confirmed),7 correct links/0 wrong.
- Exact crossing:9TP/0FP/1FN,2 tracks;6 correct resolvable links;2 coincident truth
  observations excluded and1 false-confirmation assessment unscorable.
- Nearby4px pair:0TP/0FP/10FN,0 tracks. Undefined association fraction, not success.
- Persistent compact artifact:25TP/5FP/0FN,1 false confirmed track.
- Empty targets:0 candidates/tracks; precision/recall undefined. Noise-only:0
  candidates/tracks under explicit uncertain bypass, not universal noise rejection.
- Blank frame2 registration failure:registered mode blocked; raw diagnostic five
  tracks recovered all five one-frame gaps with0 switches/fragments.
- Blur bypass:25TP/280FP/0FN,56 false confirmed tracks; validator marked uncertain.
  This exposes model failure when suitability is ignored, not production acceptance.

Local one-run timing (ms/frame detector/registration): counts9.28/5.59,
camera26.46/18.31, artifacts25.53/18.40, blur58.55/15.35; real train84
75.91/52.37, train438100.51/76.56, test110724.33/22.22. CPU timings include
concurrent test/other-run interference; they are logged diagnostics, not isolated
runtime comparisons or acceptance targets. Detector time excludes file loading,
registration/tracking/evaluation/rendering; registration reports its own per-frame
time. Frames/images retained native dimensions.

Real train84:[7,7,6,8,6] candidates;23 raw vs31 reference tracks. train438:
[6,8,5,3,5];26 raw tracks;registration fails3/4 and registered tracking blocked.
test1107:zero candidates/tracks in both modes. No persistent ESA truth IDs here
to certify tracking accuracy. Star alignment includes apparent sky drift and may
increase GEO-staring target displacement beyond initial20px gate. No claim that
registration always improves real association. Existing baseline results remain
historical; no fresh precision/recall benchmark or blind daylight validation.

## Tests and actual commands

New focused tests:42 passed,0 failed,0 skipped in6.95s. Test meaningful invalid
formats/noise/background changes, unsupported guard, no file-I/O leakage, visibility
and native bounds, real algorithm counts, preserved geometry, actual snapshot gap
recovery/camera compensation/artifact failure, safe label audit, failure handling
and refusing to overwrite results.

First root run without CV_T06_TRACKING_SNAPSHOT:306 passed,8 skipped,0 failed
(40.76s); skips were the existing optional Member3 tests, not missing ESA.
After specifying actual snapshot:314 passed,0 failed/skipped (117.40s), before
final guard additions. Later full run:337 passed,0 failed/skipped (70.05s), which
also discovered20 tests from concurrently appearing tests/yolo/. Collection then
found338 after an additional notebook test appeared; latest full run evidence is
artifacts/reports/cv_t14/latest_full_tests.txt: **338 passed,0 failed,0 skipped in
94.45s**, including the now21 external YOLO utility/notebook tests. The reviewed
CV/contract subset has317 collected cases (275 prior plus42 CV-T14); full-root
results include21 additional tests from that other workstream.
One existing Starlette/httpx deprecation warning; no dependency alteration applied.
The later YOLO utility/notebook tests do not demonstrate trained model availability.

Initial evidence probe failed on an invalid local `not_attempted` RegistrationResult
status; corrected to existing `not_required` for the explicitly raw comparator.
No shared schema changed. Partial failed probe preserved; final CLI/schema tests
passed. An early regular-grid fixture produced a phase-correlation alias on large
camera motion; background positions/intensities were made non-periodic for a
more informative authored test. Registration/detector/tracker algorithms unchanged.
This is renderer development, not a blind benchmark.

Actual command forms (from E:\Fusion):

```powershell
git fetch --no-tags origin feature/tracking-trajectory
& .\.venv\Scripts\python.exe -u scripts\spotgeo_inventory.py --output artifacts\reports\cv_t14\inventory.json
& .\.venv\Scripts\python.exe -u scripts\spotgeo_robustness.py --output artifacts\reports\cv_t14\final_review --tracking-ref a015cc949955d0438c8a16789b23746c3206f3d1
$env:CV_T06_TRACKING_SNAPSHOT = "$PWD\artifacts\reports\cv_t14\final_review\tracking_snapshot"
& .\.venv\Scripts\python.exe -m pytest -q -rs
git diff --check
git diff --cached --name-only
git branch --show-current
```

Evidence runners completed exit0. Fetch only refreshed a remote ref; no checkout,
merge or local branch creation. Do not rerun into existing output paths.
Reproduce without overwriting:

```powershell
Set-Location E:\Fusion
$env:PYTHONPATH = "$PWD\src;$PWD\backend"
& .\.venv\Scripts\python.exe scripts\spotgeo_robustness.py --output artifacts\reports\cv_t14\my_rerun --tracking-ref a015cc949955d0438c8a16789b23746c3206f3d1
$env:CV_T06_TRACKING_SNAPSHOT = "$PWD\artifacts\reports\cv_t14\my_rerun\tracking_snapshot"
& .\.venv\Scripts\python.exe -m pytest tests\contracts tests\detection -q -rs
& .\.venv\Scripts\python.exe -m pytest -q -rs
& .\.venv\Scripts\python.exe scripts\spotgeo_inventory.py --output artifacts\reports\cv_t14\my_inventory.json
Start-Process "$PWD\artifacts\reports\cv_t14\my_rerun\index.html"
Start-Process "$PWD\artifacts\reports\cv_t14\my_rerun\counts_change\tracking_registered.png"
Start-Process "$PWD\artifacts\reports\cv_t14\my_rerun\train_84\candidates.png"
Get-Content "$PWD\artifacts\reports\cv_t14\my_rerun\summary.json"
```

If the snapshot commit is absent, the above explicit fetch is needed once.
No automatic fetch happens in the scripts. `--synthetic-only` is available when
ESA is missing; neither script downloads anything. All images/results ignored.

## Readiness and next dependencies

Member3 can consume actual CV-T06 Detection with paired reference coordinates;
read-only snapshot integration and schema validation tested. Member3's modules
are not canonical imports on Subham, hence explicit snapshots, not a hidden merge.
API/backend integration is **not implemented**: backend/orbittrace/pipeline.py
raises NotImplementedError. Internal suitability statuses need Member1 approval.
Backend packaging excludes src/astrotrace; root packaging patch remains unapplied.
Direct library commands require PYTHONPATH; script bootstrapping tested. No new
clean wheel-install result is claimed.

Working classical models: T03 baseline/frozen CV-T04, CV-T06 adapter, T13
registration, CV-T14 diagnostics. Torch/Ultralytics are not importable in active
.venv and models/ has only README; no trained checkpoint verified. New unrelated
experiments/notebooks are outside this task's model validation. No training done
**by CV-T14**. Concurrent CV-T15.md reports an isolated .cache/cv_t15/venv with
successful CPU/GPU smoke training and main evaluation pending at inspection;
these reported model results were not independently rerun by CV-T14. Do not
interpret unavailable in the shared .venv as unavailable in that separate runtime.

Member1 actions: bounded upload/status integration, packaging, honest pipeline
selection; no empty-success mapping for unsuitable input. Member3: reviewed
whole-sequence registration failure policy, profile/cadence/uncertainty-aware
initial gating, merged/nearby ambiguity, nuisance confirmation and field-exit flags.
Keep raw/reference distinction and predicted vs observed invariants.

Next recommended task: curate independently labelled real daylight/noise/cloud
and telescope hard negatives, verify wider dataset rights/labels/session splits,
then jointly review suitability and registration policies. Improve nearby-target
sensitivity against held-out real examples before claiming robustness or training
new models; coordinate model plans with the already active CV-T15 experiment.
Candidate tracks never establish debris identity, orbit, altitude,
physical speed or collision probability.
