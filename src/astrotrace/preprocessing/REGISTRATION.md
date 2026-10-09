# OrbitTrace T13 background-field registration

Implemented and tested: image-only CPU translation to the first supplied frame,
robust feature consensus, reserved validation correspondences, failure gates,
invertible raw/reference transforms, aligned previews/masks and a shared Detection
bridge. Original T03/CV-T04 algorithms are unchanged. No tracking, labels, learned
models, astrometric calibration, or physical camera model enter registration.
See [measured handoff](../../../docs/handoffs/CV-T13.md).

## Modules and interfaces

| Module | Input | Output |
|---|---|---|
| registration.py | Ordered native grayscale arrays and declared numeric config | SequenceRegistration with per-frame immutable matrix/diagnostic records |
| registration_fixtures.py | Seed, streak/noise/rendering settings | Small authored five-frame arrays plus separate camera/target/background truth |
| registration_visualization.py | Raw arrays, SequenceRegistration, local output directory | Original/aligned/before-after overlays, correspondences, residual PNGs and validity masks |
| scripts/spotgeo_register.py | Extracted ESA root, new output directory, optional locally fetched tracker ref | Two crowded and one isolated synthetic scene, five named real sequences, summaries and optional actual tracker consumption |

```python
from astrotrace.datasets import SpotGeoDataset
from astrotrace.preprocessing.registration import (
    register_sequence, add_reference_coordinates, warp_to_reference,
)
from orbittrace.detection import detect_sequence

sequence = SpotGeoDataset("data/raw/SpotGEOv2", split="train").load_sequence(84)
frames = [frame.pixels for frame in sequence.frames]
registration = register_sequence(frames)  # pixels only, no annotation object
raw_detections = detect_sequence(frames, sequence_id="train-84")
if registration.status == "failed":
    raise ValueError("Registration failed: stop reference-frame tracking")
registered = add_reference_coordinates(raw_detections, registration)
aligned_preview, valid_mask = warp_to_reference(frames[1], registration.frames[1])
```

`register_sequence(frames: Sequence[np.ndarray], config=None) -> SequenceRegistration`
accepts1..30 equal-size images, each >=32px on either axis and <=4M pixels.
uint8/uint16 or finite normalized float32/64 [0,1] follow the original grayscale
validator. Arrays are not mutated. Config is RegistrationConfig or a mapping of
declared finite numeric fields; unknown keys/truth/paths raise ValueError. Invalid
inputs raise ValueError; valid feature-poor/unrelated scenes return failed records.
The library changes no global OpenCV thread or random-seed settings.

`FrameRegistration.transform_points(points, inverse=False) -> np.ndarray`
maps finite Nx2 xy arrays. On a failed frame it raises ValueError. Both matrix
directions are exported as3x3 tuples, and empty Nx2 arrays are valid. Successful
status is `estimated`; frame0 is `identity`. Sequence status is failed if any
frame fails; a reference anchor alone is not evidence of cross-frame alignment.

`add_reference_coordinates(detections, registration) -> list[Detection]` returns
new revalidated app.schemas.result.Detection objects. It preserves every field
except the previously-null x_reference_px/y_reference_px pair. It rejects failed
sequences, out-of-sequence/bounds detections and double registration. It requires
successful registration even if the detection list is empty, preventing an empty
failed frame from silently entering a mixed coordinate stream. It does not infer
timestamps, alter IDs, clip coordinates or transform raw boxes/endpoints.

`warp_to_reference(pixels, frame_registration) -> (float32_image, bool_mask)`
returns a new normalized aligned image. It uses bilinear interpolation, constant
zero borders and a warped unit-support mask; partially sampled border pixels are
invalid and zeroed. Supply the frame's original image at the declared dimensions.
Use originals for detection; interpolation and borders must not create proposals.

## Algorithm and declared quality gates

1. Normalize by native dtype range. Mild Gaussian sigma0.8 smoothing minus sigma8
   background removes smooth illumination. Registration-only display/flow pixels
   are scaled by max(p99.8 positive response,12 MAD noise scales), then clipped.
2. Shi–Tomasi corners on positive high-pass pixels above6 robust noise scales;
   14px border exclusion, <=300 features, 12px spacing. Features are suitable image
   structures, often streak endpoints/intersections; star identity is unverified.
3. Windowed phase correlation provides reference->raw coarse displacement.
   Response<0.1 or shift magnitude>250px fails; copies prevent OpenCV windowing
   from modifying scientific inputs.
4. Pyramidal Lucas–Kanade tracks reference features to each frame directly, seeded
   by the coarse shift.25x25 windows,3 pyramid levels,40 iterations/0.001 epsilon.
   Reverse tracking must agree within1px; invalid/out-of-border matches are removed.
5. Reserve every fifth reference feature, before pruning, from transform fitting.
   Remaining matches propose raw->reference translation vectors. Exhaustively
   evaluate every single-vector minimal hypothesis (deterministic RANSAC), choose
   maximum1.25px consensus, break ties by median error/index, refine by median.
6. Require >=12 fit inliers and >=60% fit ratio; >=4 reserved validation inliers
   and >=60% validation ratio; validation-inlier RMSE<=0.8px; inlier span >=20%
   on both image axes; overlap>=45%. Failed records have null usable matrices.

If direct alignment fails after a previous frame aligned successfully, one
bounded retry can use that verified frame to obtain a better flow initialization.
The neighbor-to-current pair must pass the same checks. Its composed translation
only seeds a new **direct frame-0 fit**, with a 21px flow window; that final fit
must independently pass the original support, validation residual, distribution,
shift and overlap thresholds. No chained transform is returned. A false coarse
phase peak can therefore be recovered without lowering the acceptance thresholds
for the final transform. `neighbor_retry=0` reproduces the original direct-only
policy; the default is 1. `retry_flow_window_px` is an odd integer in 15..35,
default 21. Successful direct fits use the original 25px window and remain unchanged.

Supplemental frame diagnostics record `initialization`, `seed_frame_index`,
`flow_window_px` and `direct_failure_reasons`. See
[verified real-upload follow-up](../../../docs/handoffs/T13_REGISTRATION_RECOVERY.md).

The 250px/45% bounds accommodate observed large ESA field displacements. They are
declared guardrails, not learned accuracy thresholds. No label-based tuning or
detector threshold change occurred. Small rotation was investigated diagnostically
on translation inliers; inconsistent benefit did not justify a production model
extension. Non-translation scenes can fail; do not silently introduce affine warps.

Diagnostics report reference/matched counts, fitting/reserved-validation support,
ratios, conditional inlier residuals, before-alignment residual, coverage, overlap,
phase response, runtime and failure reasons, plus matched point/flag arrays.
Fit ratios use non-reserved usable matches; validation ratios use usable reserved
matches. Residual RMSE excludes rejected correspondences, so assess it together
with the ratios/counts. Reserved points do not fit the translation; coarse phase
correlation still sees the whole image. This is internal quality evidence, not an
independent statistically blind validation or certified astrometric error.

Runtime_ms includes each frame's preparation and matching/estimation; frame0 also
includes reference feature selection. Total registration call includes common
overhead. Loading, detection, plotting, JSON and tracking are excluded. Timings
are observed single runs on local CPU; not a guaranteed production throughput.

## Coordinate convention and Member 3 integration

Top-left origin; x right/y down; pixel centers at integers, NumPy indexing[y,x].
If background content moved (+dx,+dy) relative to frame0, then
`x_reference=x_raw-dx`, `y_reference=y_raw-dy`. The exported raw-to-reference
matrix contains (-dx,-dy); inverse is(+dx,+dy). No half-pixel offset, resizing,
axis swap or sign guessing. Reference points can legitimately lie outside frame0
bounds and remain finite; raw positions and exclusive-upper boxes stay intact.

After the separately reviewed tracker source is installed:

```python
from orbittrace.tracking.tracker import Tracker
from orbittrace.trajectory.fit import attach_trajectories

tracks = Tracker().process_sequence(registered, frame_indices=range(len(frames)))
tracks = attach_trajectories(tracks, coordinate_frame="reference_frame_0",
                           time_basis="frame", frame_dimensions=(640, 480))
```

The actual latest source inspected is feature/tracking-trajectory at c7227e9.
It prefers Detection reference coordinates, copies raw coordinates into observed
TrackPoints and fits trajectories in the declared coordinate frame. No dictionary
translation or schema change is required. The report script can test unchanged
Git source snapshots without merging or modifying that branch.

Current integration issues to coordinate:

- Tracker falls back to raw if references are null. Do not send partially
  registered lists: this bridge refuses the entire failed sequence. Integration
  must agree retry/segmentation/drop-frame policy, with explicit failure state.
- Tracker's default20px gate is not automatically suitable for ESA targets in
  star-relative coordinates: background drift can be30–50px/frame even when a
  target moves slowly in raw images. Motion models/gates require tracking-owner
  development-only validation; registration does not guarantee better associations.
- Observed TrackPoints currently set out_of_field=False. Member3 should review
  finite reference points outside the reference image and accurate field flags.
- Shared RegistrationResult contains only status/warnings. Matrices/diagnostics
  live in this local report; Member1 must decide controlled provenance/artifact
  transport rather than adding new API fields from the CV role.
- Packaging still needs Member1: astrotrace is outside backend package discovery.
  Root patch was not applied. Use existing source PYTHONPATH locally for imports.

ESA background displacement combines apparent sky motion, possible pointing
changes and imaging effects. Without pointing/timing/astrometric metadata it is
not an independently verified pure camera transform. Compensated target motion is
relative to the selected background frame, in px/frame unless actual timestamps
are supplied elsewhere. No orbit, physical velocity, debris identity or collision
claim is supported. Real tracks here are compatibility diagnostics only.

## Reproduce and view

From E:\Fusion with the existing Python environment and extracted data. No labels
or download are needed. The CLI bootstraps source imports and sets one CPU thread.
Output directory must be new; never overwrite historical reports.

```powershell
Set-Location E:\Fusion
$cvT13Output = 'artifacts/reports/cv_t13/reproduce_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
.\.venv\Scripts\python.exe scripts/spotgeo_register.py --source data/raw/SpotGEOv2 --output $cvT13Output --tracking-ref c7227e9f00cc50a1b480f6d257dd1367bc589aec
if ($LASTEXITCODE -ne 0) { throw 'Registration runner failed or data missing' }
$env:CV_T06_TRACKING_SNAPSHOT = (Resolve-Path "$cvT13Output/tracking_snapshot").Path
.\.venv\Scripts\python.exe -m pytest -q -c backend/pyproject.toml
Invoke-Item "$cvT13Output/train_84/original.png"
Invoke-Item "$cvT13Output/train_84/aligned.png"
Invoke-Item "$cvT13Output/train_84/star_overlay_before.png"
Invoke-Item "$cvT13Output/train_84/star_overlay.png"
Invoke-Item "$cvT13Output/train_84/correspondences.png"
Invoke-Item "$cvT13Output/train_84/residuals.png"
Get-Content "$cvT13Output/train_84/registration.json"
Get-Content "$cvT13Output/train_84/detections.json"
Get-Content "$cvT13Output/summary.json"
```

For standalone library imports set `$env:PYTHONPATH="$PWD\src;$PWD\backend"`.
Omit --tracking-ref to skip snapshot consumption; no canonical tracker is present
on Subham. Snapshot tests explicitly skip if actual source is unavailable. The
CLI returns0 for a completed diagnostic run even if some registrations fail;
inspect status/warnings. Missing ESA root returns2 after synthetic results and a
concrete missing-data report. --synthetic-only explicitly skips real samples.
Panels use a shared display contrast scale; blue indicates invalid aligned borders,
red/green overlay reference/other-frame intensities, cyan correspondence/residual
marks reserved validation, green fit inliers and red rejected pairs. Residual
arrows are enlarged10x and labelled. These are rendered from real pixels/points.

Dependencies reuse installed NumPy/OpenCV/Pillow and Pydantic; no new root
dependency/lock change. NumPy BSD/bundled notices, OpenCV Apache2, Pillow MIT-CMU,
Pydantic MIT as recorded in existing guides. Images/reports stay gitignored;
dataset attribution is in [dataset documentation](../datasets/README.md).

## Limitations

Dominant coherent background features are assumed. Repeated patterns, severe
streak morphology changes, focus/exposure variation, narrow feature distribution,
large rotation/parallax/nonrigid fields or a foreground-dominated field can fail
or bias estimates. Corners/flow residuals do not establish stars' astrophysical
identity. A failed reference provides no cross-frame transform. No unverified
identity fallback or affine recovery occurs. Tests cover failures and known
synthetic translation; the five ESA examples were previously used, and their
measurements are diagnostic, not generalization or calibration evidence.
