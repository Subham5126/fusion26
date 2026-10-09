# Handoff: CV-T13 — star-field registration and motion compensation

Owner: Computer Vision & Dataset Engineer, OrbitTrace / FUSION SPACE-02.
Backlog task: T13 / Data-CV. Base commit:
c802622800ed14739bd841ee840ec16cf905e4cd. Branch: Subham only.
Date: 9 October 2026 (Asia/Calcutta). State: ready_for_review.
Implemented/tested translation, coordinate bridge and explicit failures; real
registration quality and actual tracker consumption measured. Pure camera motion,
ESA object identity and tracking accuracy are not scientifically established.
No commit, push, merge, rebase, reset, package installation or dataset download
occurred in CV-T13. The unrelated PROBLEM_STATEMENT modification was retained.

## Exact files created or changed

Created:

- src/astrotrace/preprocessing/registration.py
- src/astrotrace/preprocessing/registration_fixtures.py
- src/astrotrace/preprocessing/registration_visualization.py
- src/astrotrace/preprocessing/REGISTRATION.md
- scripts/spotgeo_register.py
- tests/detection/test_registration.py
- docs/handoffs/CV-T13.md

Modified: src/astrotrace/preprocessing/README.md, linking the new module and
removing the now-stale statement that no registration exists. Original image and
candidate preprocessing, T03/CV-T04 algorithms, detection adapter, shared schemas,
tracking/trajectory/evaluation source, frontend/backend glue, configs, dependencies,
lockfiles, STATUS/BACKLOG and packaging remain unchanged.

Already ignored local artifacts: artifacts/reports/cv_t13/run_01 (earlier complete
diagnostic run), final (final code/three synthetic variants), full_pytest.txt,
rigid_diagnostic.json and audit evidence. .cache exploration scripts are local-only.
No generated ESA images, transformed datasets, tracker snapshots or large reports
are added to source control.

## Inspection and implementation

Read AGENTS, shared contracts, STATUS/TEAM/BACKLOG, project brief/architecture,
Data-CV role, CV-T05/CV_TO_TRACKING, existing preprocessing, schemas and actual
tracking source. Existing backend/orbittrace/registration contained only a
placeholder initializer; no working algorithm was replaced. Git fetch/ls-remote
confirmed Member3's latest feature/tracking-trajectory at
c7227e9f00cc50a1b480f6d257dd1367bc589aec; branch Subham remained active.

Image-only pipeline: native dtype normalization; Gaussian high-pass background
suppression; high-SNR Shi–Tomasi corners; Hanning-window phase correlation;
phase-seeded pyramidal Lucas–Kanade correspondences with forward/backward check;
deterministic exhaustive translation RANSAC/median refinement; reserved validation
features, spatial coverage/overlap/residual support gates; inverse transforms;
separate aligned previews and invalid-border masks.

All frames register directly to frame0, avoiding chained drift. The reference
has identity geometry. Subsequent failures have null usable matrices, concrete
reasons and diagnostic correspondences. Inputs, raw detections and boxes are
preserved. The shared Detection bridge fills only the optional reference pair
on new revalidated copies. A failed frame rejects conversion of the whole
sequence, including empty frames, to prevent the current tracker's raw fallback
from mixing incompatible coordinate systems.

Declared config: max_features300, min_inliers12, feature spacing12px, feature
SNR6, forward/backward gate1px, consensus radius1.25px, minimum fit/validation
ratios0.6, maximum validation-inlier RMSE0.8px, phase response0.1, maximum shift
250px, minimum axis coverage0.2, minimum overlap0.45. LK windows25x25,3 pyramid
levels,40 iterations/0.001 epsilon. Every fifth original feature is reserved from
translation fitting before pruning. Config fields are worker-owned numeric
parameters, not changes to shared pipeline contracts. No label-based tuning or
detector change occurred. Large translation bounds reflect observed ESA drift.
Canonical sorted-config JSON SHA-256:
c836b7f8a1c3fd5fc900d8f4abe37e76ad3a4918c32d97b8f16984f626c1bde9.
Per-file source SHA-256 and preservation evidence are in cv_t13/audit.json.

Translation first: an off-line rigid least-squares diagnostic was fit on existing
translation fitting inliers, evaluated on the same reserved/inlier subset.
Train/438 frame3 RMSE changed0.576->0.595px; frame4 changed0.788->0.746px.
Test/57 frame3 changed0.852->0.682px at fitted0.0079deg rotation. Improvements
were inconsistent, did not resolve weak correspondence consensus, and are not
independent evidence of true rotation. No rotation/affine extension was promoted.
The failed test/57 frame remains failed under the declared translation pipeline.

## Real data actually processed

Extracted root: E:\Fusion\data\raw\SpotGEOv2. Read all5 native640x480 uint8 PNGs
for each requested sample, in official1..5/internal0..4 order:
train/84, train/438, test/10, test/57, test/1107.25 distinct real PNGs, with repeat
passes; full regression tests additionally repeat their existing real cases.
No ESA annotation JSON was needed by registration, detection or tracking. Input
SHA-256 manifests are in final/summary.json. No new dataset download/exhaustive
32,000-image audit or independent blind/generalization benchmark was performed.
These are previously used diagnostic examples; do not tune detector thresholds
or claim blind validation on them.

### Final real measurements

Non-reference indexes are1..4. RMSE is a reserved-validation INLIER matching
residual, conditioned on the radius/support gates, not astrometric ground truth.
Rejected correspondence residuals are not in that RMSE; assess counts/ratios too.
The table includes diagnostics even for rejected frames, clearly marked.

| Sequence | Valid transforms /4 | Validation RMSE by frame1..4 (px) | Fit inliers by frame1..4 | Mean registration ms/frame |
|---|---:|---|---|---:|
| train/84 | 4 | 0.238,0.315,0.310,0.382 | 48,49,43,34 | 61.87 |
| train/438 | 2 | 0.525,0.691,0.576 failed,0.788 failed | 61,41,24,20 | 64.87 |
| test/10 | 4 | 0.533,0.720,0.506,0.595 | 31,28,28,25 | 53.94 |
| test/57 | 3 | 0.535,0.394,0.852 failed,0.445 | 26,27,23,21 | 58.42 |
| test/1107 | 4 | 0.291,0.481,0.343,0.514 | 29,29,26,27 | 60.84 |

Success:17/20 estimated non-reference transforms (85%); failure3/20 (15%).
Complete valid sequences3/5 (60%). Reference identity anchors are not counted
as estimated successes. Accepted reserved-validation RMSE range0.238..0.720px.
Mean measured preparation/matching/estimation runtime across all25 frames is
59.99ms. The final run overlapped the full test run; timing is observed wall time,
not isolated throughput. Loading, detection, rendering, JSON and tracker calls
are excluded. Total call times:312.68,327.60,271.79,294.95,307.11ms respectively.

| Sequence | Fit inlier ratios frame1..4 | Validation inliers / usable validation matches |
|---|---|---|
| train/84 | 0.980,1.000,1.000,0.971 | 14/14,13/13,12/12,10/10 |
| train/438 | 0.984,0.774,0.558 failed,0.541 failed | 15/15,9/12,7/10,4/8 |
| test/10 | 0.886,0.966,0.903,0.926 | 8/8,7/7,7/9,5/7 |
| test/57 | 0.929,0.964,0.885,1.000 | 7/7,7/7,6/7,6/6 |
| test/1107 | 0.935,1.000,0.897,1.000 | 8/8,8/8,8/8,6/6 |

Train/438 frame3 fails fit consensus ratio0.558<0.6; frame4 fails fit ratio0.541
and validation ratio0.5. Test/57 frame3 fails validation RMSE0.852>0.8. Gates were
not relaxed to turn these into successes. Remaining frames of failed sequences
are available for diagnostic plotting, but no partial coordinate stream is sent
to tracking by the helper.

Before-alignment correspondence RMSE for train/84 rises31.08,62.31,93.43,124.74px;
after-alignment validation residuals above are subpixel. These are different
correspondence subsets (pooled accepted matches versus reserved validation), so
not a paired accuracy statistic. Examples of accepted raw->reference translations:

| Sequence | Frame1(tx,ty) px | Frame4(tx,ty) px |
|---|---|---|
| train/84 | (-30.169,-7.548) | (-121.035,-30.441) |
| train/438 | (48.007,24.135) | null: failed |
| test/10 | (-11.960,-4.064) | (-47.859,-16.471) |
| test/57 | (39.778,5.159) | (160.359,19.728) |
| test/1107 | (-6.189,7.150) | (-25.170,28.943) |

These map apparent background-field positions into frame0. Sky/sidereal motion,
camera pointing and imaging effects are not separated without telescope metadata;
they are not independently calibrated pure camera transformations.

## Synthetic validation and target-motion preservation

All scenes: deterministic seed13,5 frames256x192, rendered Gaussian backgrounds,
read-only uint8 arrays, independent target moving(3,1.5)px/frame. True background
camera shifts: (0,0),(3.25,-2.5),(6,-4),(-2.5,3.75),(1.5,6.25). Truth is separate
and used after image-only inference. Analytic rendering avoids using warped copies
as the sole benchmark truth. Streaks use a fixed12px diagonal trail.

| Scene | Registration | Max known-shift error px | Independent known-background RMSE px | Actual target detections within5px |
|---|---|---:|---:|---|
| Crowded compact stars | 4/4 | 0.0133 | 0.00890 | 4/5;1 missing |
| Crowded streaks | 4/4 | 0.0276 | 0.01683 | 0/5; detector returned no candidates |
| Isolated target with streaks | 4/4 | 0.03094 | 0.02155 | 5/5; errors0.0161,0.0282,0.0192,0.0299,0.0181px |

Isolated rendering explicitly reserves22px around the target path at fixture
generation: an easy controlled integration test, not a representative ESA scene.
The crowded misses were preserved, not silently replaced or repaired by truths.
They expose unchanged detector blend/shape-filter limitations, separate from
registration's transform accuracy.

Compensated known target positions retain independent motion in all three scenes.
Most importantly, actual detections in the isolated case support one real
five-observation confirmed track through unchanged Member3 code. Its fitted
vx=2.99576693,vy=1.50024673px/frame, fit RMSE0.02126966px. All points reference
actual detection IDs; predictions remain separate extrapolated points. This
validates the controlled image-plane compensation/association path, not physical
speed or real ESA identity correctness.

## Member 3 compatibility and integration proposal

Exact callables:

```python
from astrotrace.preprocessing.registration import register_sequence, add_reference_coordinates
from orbittrace.detection import detect_sequence
registration = register_sequence(frames)
raw = detect_sequence(frames, sequence_id="train-84")
registered = add_reference_coordinates(raw, registration)  # fails for any failed frame
# After separately reviewed tracker integration:
# tracks = Tracker().process_sequence(registered, frame_indices=range(len(frames)))
# tracks = attach_trajectories(tracks, coordinate_frame="reference_frame_0",
#                            time_basis="frame", frame_dimensions=(640,480))
```

SequenceRegistration returns frame-indexed diagnostics and raw_to_reference plus
reference_to_raw3x3 matrices. Transform convention is x_ref=x_raw+tx,
y_ref=y_raw+ty; NumPy[y,x], top-left origin, integer centers, floating precision.
Frame0 is identity. The inverse round-trip and OpenCV warp direction are tested.
Aligned images are previews with masks, never replacements for detector inputs.
Only shared Detection.x/y_reference_px change; raw centroid, raw exclusive-upper
bbox, endpoints, score, ID, frame index and evidence remain byte-value equivalent.

Actual c7227e9 tracker/fit files were copied byte-identically from Git into ignored
report snapshots; none of Member3's files were edited/merged. Tracker consumes
reference positions when supplied and preserves raw in TrackPoints. Successful
sequence calls for train/84,test/10,test/1107 passed shared AnalysisResult checks,
with31/9/0 tracks respectively and0 confirmed tracks each. This is compatibility
acceptance, not improved ESA tracking performance. Failed train/438/test/57 were
not sent to the reference-frame tracker. Synthetic cases additionally pass.

Specific coordination issues:

1. Tracker falls back to raw when references are null. Integration must implement
   an explicit failed-registration policy, not mix partial transforms. This
   helper conservatively refuses the entire sequence. Segmentation/retry/drop
   policies require Member1/Member3 review; no automatic identity fallback.
2. Default20px gating can miss ESA targets whose motion relative to the background
   is much larger than raw motion. Review apparent star-relative geometry,
   velocity initialization and gates using development data; do not enlarge the
   gate based on ground-truth test tuning or claim more valid tracks without scoring.
   CV integration review corrected the earlier15px wording: the initial and current
   tracker source both use20px; no gate tuning change occurred in this review.
3. Tracker currently writes observed out_of_field=False. Negative/outside reference
   coordinates can be legitimate after translation; Member3 should propagate
   accurate field status rather than clip points or pretend they are in-frame.
4. Shared RegistrationResult only has status/warnings. Use status estimated/failed
   and reference_frame_0 consistently; matrices stay in controlled local evidence
   until Member1 reviews artifact/provenance transport. No API field change here.
5. Packaging remains unresolved: backend discovery excludes astrotrace. The
   previously tested root packaging patch remains unapplied. Source PYTHONPATH
   works locally; backend pipeline/API integration still selects neither detector.

## Actual commands and test outcomes

| Command/check | Actual outcome |
|---|---|
| git status/branch, source/contracts inspection, latest tracking fetch | Subham at c802622; only unrelated PROBLEM_STATEMENT dirty initially; tracker ref c7227e9 |
| Initial exploratory phase/LK run on5 ESA samples | Large coherent apparent translation observed; used to declare displacement/overlap bounds, no labels |
| First new targeted tests | 31 passed,2 failed; bilinear half-pixel peak tie made an integer argmax assertion wrong; corrupt-fit test exposed empty support reduction/nonfinite diagnostics |
| Fixes | Warp test verifies intensity centroid/sign; empty fit support returns null residual/zero coverage and explicit finite failure |
| Second targeted tests | 33 passed in9.74s |
| Expanded targeted tests | 39 passed in19.79s; includes rotation rejection, out-of-field geometry and actual isolated target tracking |
| Full `python -m pytest -q -c backend/pyproject.toml` with source snapshot | 275 passed,0 failed,0 skipped in214.13s;1 existing Starlette/httpx deprecation warning |
| Real/synthetic report CLI run_01 and final | Exit0; completed diagnostics and explicit failed registrations, not100% alignment success |
| compileall new modules/CLI/test and pip check | Passed; no broken requirements |
| Preservation/content/Git audit | 180 other tracked files match HEAD after Git newline normalization; unrelated edit hash preserved; Subham/HEAD unchanged, index empty, packaging unapplied |
| git diff --check / ignore checks / local documentation | Passed; generated report/image/cache paths ignored;71 links in60 scanned Markdown files resolve locally |

No successful test count was copied from a previous milestone. Tests substantively
cover known subpixel shifts, streak backgrounds, independent moving outliers,
inverse roundtrip/warp direction, interpolation-safe borders, nonmutation/raw
field preservation, empty/constant/noise/single-feature/unrelated/rotated scenes,
shift/overlap gates, config/array bounds, uint16/float compatibility, no inference
filesystem access, determinism, double registration/wrong-frame rejection,
corrupt-fit validation failure and actual tracker reference/raw consumption.
Missing external tracker source causes explicit compatibility test skips; this
full run supplied actual source and had none. No fresh blind ESA test is claimed.

## Reproduce and inspect actual reports

Full module/config/limit guide: [REGISTRATION.md](../../src/astrotrace/preprocessing/REGISTRATION.md).
From E:\Fusion, output directory must be new; no data download or annotation is
needed. Member3 snapshot requires its commit to be present locally.

```powershell
Set-Location E:\Fusion
$cvT13Output = 'artifacts/reports/cv_t13/reproduce_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
.\.venv\Scripts\python.exe scripts/spotgeo_register.py --source data/raw/SpotGEOv2 --output $cvT13Output --tracking-ref c7227e9f00cc50a1b480f6d257dd1367bc589aec
if ($LASTEXITCODE -ne 0) { throw 'Registration report execution failed' }
$env:CV_T06_TRACKING_SNAPSHOT = (Resolve-Path "$cvT13Output/tracking_snapshot").Path
.\.venv\Scripts\python.exe -m pytest -q -c backend/pyproject.toml
.\.venv\Scripts\python.exe -m pip check
```

Use --synthetic-only for deliberately synthetic evidence or omit --tracking-ref
to skip actual tracker consumption. Missing real dataset writes a missing report
and returns2 after the synthetic path; no automatic archive download. Exit0 means
the diagnostic run completed, not that every transformation was accepted.

Current actual files:

```powershell
Invoke-Item .\artifacts\reports\cv_t13\final\train_84\original.png
Invoke-Item .\artifacts\reports\cv_t13\final\train_84\aligned.png
Invoke-Item .\artifacts\reports\cv_t13\final\train_84\star_overlay_before.png
Invoke-Item .\artifacts\reports\cv_t13\final\train_84\star_overlay.png
Invoke-Item .\artifacts\reports\cv_t13\final\train_84\correspondences.png
Invoke-Item .\artifacts\reports\cv_t13\final\train_84\residuals.png
Invoke-Item .\artifacts\reports\cv_t13\final\train_84\valid_mask_4.png
Invoke-Item .\artifacts\reports\cv_t13\final\train_438\aligned.png
Get-Content .\artifacts\reports\cv_t13\final\train_438\registration.json
Get-Content .\artifacts\reports\cv_t13\final\synthetic_isolated\tracking_result.json
Get-Content .\artifacts\reports\cv_t13\final\summary.json
Get-Content .\artifacts\reports\cv_t13\full_pytest.txt
```

Red reference/green aligned overlay makes coincident structures yellow; blue
marks invalid border support. Before overlay uses green raw pixels. Correspondence
plots show reference-left/current-raw-right with green fit, cyan reserved inliers,
red outliers. Residual vectors enlarged10x are labelled. Failed aligned frames
are explicitly blank/failure-marked, not raw images masquerading as aligned ones.
Actual train/84 aligned overlay was visually inspected. Inputs remain original;
PNG contrast is display-only. Reports/images and data are ignored by Git.

## Limitations and next recommended task

Model assumes a dominant spatially distributed coherent background. Repeated
patterns, changing/merged streaks, severe noise/blur, foreground majority,
rotation/parallax/nonrigid motion and clipped overlap can bias or fail it.
Residuals depend on selected flow correspondences; no catalog astrometry or real
camera ground truth is available. Low-feature scenes fail safely. Real quality
on broader/session-disjoint data and useful compensated tracking still need
validation. Crowded synthetic target misses remain unchanged detector limitations.

Next: Member1/Member3 agree registration failure/coordinate/gating/out-of-field
policies and transport, then evaluate registered versus raw tracking on a governed
development set with image-plane metrics, explicit unmatched observations and
unknown timing. Diagnose train/438 correspondence changes and test/57 failure
before considering a separately validated rigid extension. Preserve frozen
detector checkpoints. Packaging/T07/API remain Integration tasks. No physical
orbit/speed/collision/debris-certification conclusion follows from this work.

Git remains Subham at the base commit; new CV-T13 source is uncommitted/unpushed.
Publication requires new explicit user approval. Historical source and unrelated
local edits are preserved; no reset, deletion or alternate branch was used.
