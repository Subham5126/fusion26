# CV-TRACK-01 — unified Member 2 + Member 3 algorithms

Task: user-assigned CV-TRACK-01, continuing T03/T04/T05/T06/T13/T14 algorithm
integration. Owner: CV + tracking integration engineer. Base: merged development
`da28ab8b0aa4e7abaeec802aff1714a1b4bb8336`. Workspace: detached
`E:\Fusion-integration`. Original `E:\Fusion` stays on Subham at
`922fb937a109ec3231d7ec462bb88f3fdbdd62b4`. Date: 9 October 2026.
State: ready_for_review for Member 1's CPU integration; real ESA tracking PARTIAL.
No commit/push/branch/history operation. No existing source file edited.

## Files created and ownership

- backend/orbittrace/cv_tracking.py: one stable, image-only algorithm entry point,
  validation, strict scientific failures, baseline selection and diagnostics.
- backend/orbittrace/evaluation/cv_track_diagnostics.py: actual tracker replay,
  summary statistics and coordinate-correct Member 3 evaluation bridges.
- scripts/verify_cv_track_01.py: actual installed-package examples, post-inference
  evaluation, native-coordinate overlays and a self-contained HTML report.
- tests/pipeline/test_cv_track_01.py: 34 meaningful algorithm/contract acceptance
  tests, including the requested ESA cases and no inference file/label access.
- docs/handoffs/CV-TRACK-01.md and CV-TRACK-01-files.txt: this handoff and exact
  six-file review set. These are not an authorization to publish.

All pre-existing Member 1 pipeline/API/queue/frontend files, shared models,
root config/packaging/locks, tracker/fit/evaluator implementations and original
CV-T15 experiments are preserved. AGENTS, active role prompts, STATUS, TEAM,
PROJECT_BRIEF, BACKLOG, CONTRACTS, algorithm/evaluation docs and required CV
handoffs were read. Old readiness claims are historical; no shared status edit.

## Exact import and stable signature

```python
from orbittrace.cv_tracking import analyze_telescope_sequence, TelescopeAnalysisError

analyze_telescope_sequence(
    frames: Sequence[np.ndarray], *, sequence: SequenceInput,
    frame_indices: Sequence[int] | None = None,
    timestamps: Sequence[float | None] | None = None,
    config: PipelineConfig | None = None,
    method: Literal['optimized', 'baseline'] = 'optimized',
    detector_config: Mapping[str, object] | None = None,
    registration_config: RegistrationConfig | Mapping[str, object] | None = None,
    diagnostics: dict | None = None,
) -> AnalysisResult
```

Use the root installation already owned by Member 1. No new runtime dependency
or PYTHONPATH is needed. Dependencies remain the repository's pinned NumPy,
OpenCV headless, SciPy, Pydantic and associated core packages. Pillow is used by
the offline report. Private verification uses Python 3.12.14 and the existing
backend/requirements.lock.txt; no shared venv was replaced or changed.

Input: exactly five ordered, same-size 2D NumPy grayscale arrays, native uint8 or
uint16, or already-normalized finite float32/64 in [0,1]. Each frame <=4MP.
Native size must equal the validated SequenceInput metadata. No resizing,
color conversion, sorting, file opening, timestamp inference or truth input.
Explicit frame indexes are supported and must equal [0,1,2,3,4], as required by
current SequenceInput. Offsets, sparse indexes, duplicate/reordered indexes and
partial timestamps are rejected; arbitrary acquisition indexes would require a
separate metadata proposal. Explicit timestamps must equal the manifest values.
Unknown timestamps remain null. This entry always checks telescope suitability,
even on synthetic images; it has no static-demo or failed-registration bypass.

Default method uses the frozen CV-T04 settings: sigma4.5/context elongation2.0,
validated by OptimizedConfig. Baseline uses T03 BaselineConfig. Explicit numeric
PipelineConfig threshold_sigma/candidate_cap map to detector overrides; conflicting
CV overrides are rejected. RegistrationConfig remains the T13 default. Tracker
uses unchanged 20px gate, >=3 real observations and maximum2 consecutive misses.
No parameter was tuned against ESA84/438 or lowered to force confirmation.

## Exact implemented calls and output

```python
assessment = validate_sequence_suitability(frames)
raw = orbittrace.detection.adapter.detect_sequence(
    frames, sequence_id=sequence.sequence_id, profile=sequence.profile,
    timestamps_s=[f.timestamp_s for f in sequence.frames],
    config=declared_detector_config, method=method)
registration = register_sequence(frames, config=reg_cfg)
detections = add_reference_coordinates(raw, registration)
tracks = Tracker(config=cfg).process_sequence(
    detections, frame_indices=indexes, frame_timestamps=frame_times or None)
tracks = attach_trajectories(
    tracks, coordinate_frame='reference_frame_0', time_basis=basis,
    prediction_horizon=cfg.prediction_horizon_frames,
    frame_dimensions=(width,height), frame_timestamps=frame_times or None)
```

Adapter dispatches the actual OptimizedDetector (`opencv_context_filtered_v2`)
or OpenCVBaselineDetector (`opencv_compact_dog_v1`). It preserves actual score,
kind/evidence, unique sequence/frame proposal IDs, raw center and exclusive-upper
raw boxes. Registration creates validated copies with additive references;
raw fields are never overwritten. Tracker runs EVERY frame, including empty
frames, and assigns each actual detection exactly once. Its real lifecycle
is tentative/confirmed/ended; there is no invented public lost state. Missing
observations advance internal miss counts, never fabricated points. Fitting uses
>=3 observed points, not predictions; px/frame with unknown times, px/s with actual
seconds. Irregular cadence is warned because association predicts by frame count.
Future timestamps estimated by the existing fitter are explicitly warned as
predictions, not measurement timestamps. Field-exit flags use reference geometry.

Success returns the exact app.schemas.result.AnalysisResult 0.1.0; serialization
uses model_dump(mode='json') or model_dump_json(exclude_none=False). Finite values
and unknown nulls round-trip through Pydantic. Metrics stays null in inference;
separate evaluator outputs never replace unknown production metrics. IDs and
associated TrackPoint.detection_id fields are unchanged. Trajectories reside in
Track.trajectory, observed samples in Track.points, predictions in
Track.trajectory.predictions, with null raw coordinates and no detection ID.

## Errors and supplemental diagnostics (no schema changes)

AnalysisResult.status supports only succeeded. Expected failures raise
TelescopeAnalysisError containing existing app.schemas.job.ApiError. Use
exc.error.model_dump(mode='json') or exc.as_job_state(job_id).model_dump(mode='json')
for a contract-valid failed JobState. Codes: invalid_input, invalid_configuration,
unsupported_observation, uncertain_observation, registration_failed. Unsupported
and uncertain inputs require review/reacquisition and block detection; any failed
registration blocks the entire registered stream. No identity substitution or
mixed raw/reference tracking. Unexpected exceptions remain exceptions for the
job owner to log and handle safely. Empty supported/registered input succeeds
with empty detections and tracks; it is not a debris absence certificate.

Caller-owned diagnostics is cleared per call and populated on success/failure.
Existing component records are reused: sequence is SequenceInput JSON;
suitability is the CV-T14 result; registration is SequenceRegistration.to_dict()
with each FrameRegistration's full raw_to_reference/reference_to_raw matrices,
quality, residuals, reasons and runtime; detections is actual raw Detection JSON;
config records validated shared/CV/registration settings. status/error/runtime_ms
and measured timings_ms describe this invocation. Counts can be derived from
Detection.frame_index, Track.status and Track.trajectory, as shown in the offline
summarizer; they are not unapproved AnalysisResult fields.

Backward-compatible proposal for Member 1: retain this information in the existing
supplemental job diagnostics route, optionally add an integration-owned typed
Diagnostics response model later. Do NOT add frames, transforms, timing maps or
failed status to AnalysisResult 0.1.0 independently. No shared schema definitions,
contract version, routes or frontend types were changed by CV-TRACK-01.

Reference-to-raw plotting must use the selected frame's inverse:

```python
matrix = np.asarray(diagnostics['registration']['frames'][frame_index]['reference_to_raw'])
raw_xy = (matrix @ np.array([x_reference_px, y_reference_px, 1.0]))[:2]
```

Check registration status, matrix availability and provenance before drawing.
A predicted future reference point can be projected into a selected existing
raw image for a clearly labeled forecast, but future camera motion is unknown;
this does not predict a future raw camera location. The report renderer uses
that inverse; raw detections/boxes remain on their original grid. Accepted
reference previews call the existing warp_to_reference and mask invalid borders.

## Member 1 adoption — precise T07/T09 boundary

Current backend still imports orbittrace.pipeline.analyze(sequence,config,
frame_pixels=...,diagnostics=...) and handles its AnalysisInputError. Those files
were intentionally not edited. For telescope profiles, Member 1 can replace its
algorithm body with this delegation while retaining its trusted tiny synthetic
demo policy separately (the tiny demo lacks suitability feature support):

```python
try:
    return analyze_telescope_sequence(
        frame_pixels, sequence=sequence, config=config, diagnostics=diagnostics)
except TelescopeAnalysisError as exc:
    raise AnalysisInputError(exc.code, exc.error.message, exc.details) from exc
```

This precise error bridge preserves existing scientific failure codes; simply
changing the import without adapting the exception would turn expected failures
into generic pipeline errors. Member 1 continues job ID assignment, queue state,
transport, bounded decode, progress updates and model serialization. No detector,
registration, association, trajectory or coordinate logic needs rebuilding.

## Actual tests and outputs

34 new acceptance tests passed. Final full relevant repository suite: 438 passed,
0 failed, 0 skipped; one upstream Starlette TestClient/httpx deprecation warning.
The full suite includes existing API regressions and original tracker/trajectory/
evaluation tests. First focused attempt:29 passed/2 failed because an assertion
assumed detector name substrings; source inspection corrected it to the actual
published names without changing output semantics. Later 31/33/34 focused and
435/437/438 full regressions passed as coverage was added.
A report-edit helper initially failed under PowerShell's legacy cp1252 default;
explicit UTF-8 fixed it. Visual inspection also found a malformed/cropped failure
caption; the final report uses short, wrapped labels. Earlier reports are retained,
not overwritten. Final report is artifacts/reports/cv_track_01/run_05/index.html.

The final root wheel was built from an isolated cache copy, installed non-editably
into a new private .cache/cv_track_01/venv, and executed with Python -I. All13
scenario reports were generated from INSTALLED packages with no manual PYTHONPATH.
Import location is that venv's Lib/site-packages/orbittrace/cv_tracking.py;
pip check passed. Wheel SHA256:
`d6b8806bcb14b46cad2c2afccbd5991ee17ab9c9455026b460aae82c3d2db202`.
Public root packaging and Member 1's environment were not edited.

| Scenario | Actual counts | Tracks / confirmed / fits | Outcome |
|---|---|---|---|
| One moving object | 1,1,1,1,1 | 1 /1 /1 | registered success |
| Five objects with misses | 5,3,4,5,5 | 5 /5 /5 | 2/2 gaps recovered, zero scored switches/fragments |
| Crossing | 2,2,1,2,2 | 2 /2 /2 | coincident detection merge; two truth observations excluded from identity scoring |
| Stationary stars/noise | 0,0,0,0,0 | 0 /0 /0 | supported registered empty success |
| Supported empty targets | 0,0,0,0,0 | 0 /0 /0 | empty success |
| Persistent false artifact | 6,6,6,6,6 | 6 /6 /6 | one false confirmed track; confirmation is not debris identity |
| Camera motion | 5,8,5,5,6 | 9 /5 /5 | zero scored identity switches; extra nuisance births |
| Daylight-like | no result | not claimed | unsupported_observation |
| Noise-only | no result | not claimed | uncertain_observation |
| Accepted suitability, rotated frame | no result | not claimed | registration_failed, no usable inverse for rejected frame |
| T03 baseline one-object field | 57 each frame | 57 /57 /57 | includes stationary-star proposals; not 57 true targets |
| ESA train/84 | 7,7,6,8,6 | 31 /0 /0 |13 ended,18 tentative; no trajectories |
| ESA train/438 | raw proposals diagnostic only | no registered tracks claimed | rejected frames3/4 |

Controlled development-only counts-change seeds101/102/103, frozen parameters:
each five confirmed tracks,17 correct links,0 scored switches/fragments and2/2
recovered gaps. No detector/gate/confirmation tuning occurred. ESA84/438 are
previously used diagnostic samples, not a new blind benchmark. Repeat runs
regenerated report/evaluator/visual changes under the SAME frozen algorithm/config.

## ESA diagnosis and separate evaluation

ESA84 raw-to-reference translations (px): (0,0),(-30.169,-7.548),
(-60.490,-15.094),(-90.695,-22.682),(-121.035,-30.441). Reserved validation
RMSE for nonreference frames:0.238,0.315,0.310,0.382px; registration accepted.
Raw target motion differs from apparent background motion; adding star alignment
can increase target displacement relative to the original20px birth gate.
Actual tracker replay, all pair distances saved in association_trace.json:
frame1:49 pairs/48 outside gate/1 selected; frame2:78/78/0;
frame3:152/151/1; frame4:120/119/1. Selected distances13.379,13.713,13.229px.
Only three associations are accepted across34 proposals. All31 tracks have one
or two observations, so no fit is eligible and no confirmation is fabricated.
Frame0 births7; subsequent births6,6,7,5. Explicit skipped observations advance
misses; more than two ends a track. No timestamp metadata was invented.

ESA438 frame3 fails weak_translation_consensus; frame4 also fails
validation_residual_or_support_failed. Null usable matrices remain null.
No tracker defect was demonstrated that justifies widening the gate or bypassing
registration. New offline evaluation bridge fixes a real integration risk:
Member3 match_points_frame prefers references, so registered detections must be
copied with optional references removed before comparing to ESA RAW labels.
Tests prove input models are unchanged and translated reference points cannot
corrupt raw matching. Member3 evaluate_tracks is additionally executed on
synthetic reference truth. Its legacy crossing identity scoring does not exclude
coincident truths; companion CV stress evaluation explicitly reports that ambiguity.

ESA annotations are read only AFTER all inference by the report runner.
Actual annotation file/hash: train_anno.json,
`2727e7c21f1fef229b024dcb00952d0781057661c4ccb64937dce50f08e1fdfe`.
ESA84 raw-point localization with5px gate:15TP/19FP/10FN, precision0.44118,
recall0.6, localization RMSE0.32015px. Member3 and CV raw evaluators agree on
counts. Metrics are diagnostic development records, not a newly randomized split,
official ESA score, accuracy calibration or independent generalization claim.
ESA has no verified persistent identity labels here; identity metrics remain
unknown. No ESA track or debris identity is scientifically validated.
Native array hashes, input/config provenance and all full-precision figures are
in the generated report and individual JSON outputs.

## Website-ready examples and how to view

Ignored final output folder: artifacts/reports/cv_track_01/run_05.
Required real-generated contract examples:
synthetic_success.json, multi_object_success.json, real_esa_train84.json,
empty_success.json, unsuitable_input.json, registration_failure.json.
The first four are AnalysisResult JSON; the last two are existing failed
JobState JSON because AnalysisResult has no failed status. No custom result
schema is invented. Companion <name>/sequence.json and diagnostics.json supply
native dimensions, unknown timing, suitability, settings and matrices.

Open index.html to inspect every example and its JSON links. raw_0..4.png show
native raw detections, actual IDs/observed trails and orange forecasts mapped
through the inverse. reference_0..4.png show accepted registered previews.
registration_failure/raw_1.png and real_esa_train438/raw_3.png show the actual
rejections; the HTML index selects the first rejected frame per failed sequence.
Every figure uses
original native dimensions (synthetic320x240, ESA640x480); no reference point is
plotted on raw pixels without inverse mapping. The final report links were
checked and representative raw/reference/failure figures visually inspected.

## Exact PowerShell reproduction

Existing private installed-package verification environment:

```powershell
Set-Location E:\Fusion-integration
$cvTrackPython = '.\.cache\cv_track_01\venv\Scripts\python.exe'
& $cvTrackPython -I -c "from orbittrace.cv_tracking import analyze_telescope_sequence; import inspect; print(inspect.signature(analyze_telescope_sequence))"
& $cvTrackPython -I scripts/verify_cv_track_01.py --esa E:\Fusion\data\raw\SpotGEOv2 --output artifacts/reports/cv_track_01/run_next
& $cvTrackPython -m pytest -q tests/pipeline/test_cv_track_01.py
$env:CV_T06_REAL_SOURCE = 'E:\Fusion\data\raw\SpotGEOv2'
$env:CV_T06_TRACKING_SNAPSHOT = 'E:\Fusion\artifacts\reports\cv_readiness\final\tracking_snapshot'
& $cvTrackPython -m pytest -q -rs
& $cvTrackPython -m pip check
Start-Process -FilePath 'E:\Fusion-integration\artifacts\reports\cv_track_01\run_05\index.html' -WindowStyle Hidden
```

Use a new output folder each run; existing reports cause refusal, not overwrite.
Fresh installation in an independent checkout/environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps .
.\.venv\Scripts\python.exe -I -c "from orbittrace.cv_tracking import analyze_telescope_sequence"
```

The launcher is not registered on this PC; use the bundled Python3.12 executable
shown in the existing SETUP if creating another environment here. The report
requires an existing local ESA dataset; omit --esa for synthetic-only operation.
No download, annotation access during inference or trained-model install.

## Optional YOLO and remaining dependencies

CV-T15 is actually trained experimental work in ORIGINAL E:\Fusion, not missing
weights: best.pt exists and SHA256 matches its recorded
`a019175e841b8842cd84cf395b7eda9585df4f9e306c60e42c27d15a3ff97f03`.
Its existing adapter is experiments.yolo.adapter.to_detections(xyxy,confidence,
classes,*,width,height,frame_index,sequence_id,model_id=...,max_candidates=200),
using original-pixel boxes and uncalibrated model confidence. It is uncommitted,
not in merged development/root packaging, has a separate Torch/Ultralytics
runtime, and its handoff states production tracking/profile integration untested.
Therefore this CPU module does not advertise a YOLO method, copy unreviewed
experimental source/weights or silently import its runtime. Its streak-box metrics
and ESA compact point metrics are not interchangeable. Optional adoption needs
separate profile/packaging/runtime/licensing review and actual compatibility tests.
No CV-T15 files, environment, checkpoint or settings artifact were changed.

Next dependency: Member 1 reviews the six-file set and adopts the delegation/error
bridge plus supplemental diagnostics, retaining transport/queue ownership.
Member3 may investigate profile-aware gate initialization/cadence on NEW reviewed
development sequences, with separate held-out evaluation. Current real ESA
tracking is PARTIAL; no request to lower confirmation or force matches.
Publication remains Subham-only after explicit approval; detached edits remain
uncommitted and unstaged. No main/development commit/push, force, merge, rebase,
reset, stash, discard or automatic branch switch.

## Final preservation and artifact audit

SHA256 comparison preserved all 284 pre-existing tracked/visible untracked files
in E:\Fusion-integration, including Member 1's 40 pending paths. Original
E:\Fusion's 23 previously published CV paths and 41 protected paths also remain
byte-identical, including CV-T15 source/cache/settings. This task adds exactly the
six manifest paths, with no staging, commit, push or existing-file modification.

Final installed-package report run_05 completed all 13 cases: 9 succeeded and 4
explicitly failed as expected. All 13 serialized outputs round-trip through the
actual AnalysisResult/JobState models, all 49 scientific JSON files are finite,
all 117 overlays match native manifest dimensions and all 49 HTML href/src links
resolve. Actual rejected-frame previews and raw/reference/ID/prediction figures
were visually inspected. Both Member 2 and Member 3 raw ESA84 evaluation report
15TP/19FP/10FN with identical precision/recall/localization RMSE. Neither report
certifies real ESA track identity.

Evidence: run_05/preservation_final_02.json and run_05/cv_track_01_review_final_02.patch.
The six-file patch passes git apply --reverse --check against this workspace;
git diff --check passes and the Git index is empty. Earlier run directories and
audit/patch copies are retained. Final core wheel/import/tests remain those
recorded above; the last offline-report change selects the actual rejected frame
in HTML and was verified by rerunning the installed-package report and link audit.
