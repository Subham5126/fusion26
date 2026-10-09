# T08 — Tracking visualization workbench

Owner: frontend/display work, explicitly requested by the user.
State: implemented and tested; ready for integration review.
Initial base: `922fb93` on `Subham`.
HEAD at verification: `b07fe9873a39cd8897374078a7729cb4a50d6737`.
An unrelated FITS/CV handoff commit landed during this task. No Git staging,
commit, push, merge or rebase was performed by this task.

## Repository boundary

This checkout had a React readiness screen, no existing sequence workbench,
and a placeholder backend pipeline with health-only HTTP support. A separate
saved-result viewer is available at `#/workbench`; the default readiness screen
is preserved. The user was asked whether another viewer path exists; no location
was supplied during this task. Live analysis wiring is not claimed.

Backend source, transport types, detector/tracker algorithms, dependencies,
lockfiles, root config and concurrent CV-T15 files were not changed.

## Exact changed-file allowlist

```text
frontend/src/App.tsx
frontend/src/pages/ReadinessPage.tsx
frontend/src/pages/WorkbenchPage.tsx
frontend/src/components/TrackingWorkbench.tsx
frontend/src/components/tracking-workbench.css
frontend/src/visualization/overlay.ts
frontend/src/visualization/input.ts
frontend/tests/overlay.test.mjs
docs/handoffs/T08_TRACKING_VISUALIZATION.md
```

Review only these paths for publication. Exclude existing unrelated
`docs/PROBLEM_STATEMENT.md`, `Ultralytics/`, `experiments/`, `tests/yolo/`,
`docs/handoffs/CV-T15.md`, raw datasets, screenshots, generated artifacts and
environments. Obtain explicit user approval before any Git index/publication
operation; do not use `git add .` while CV-T15 is in progress.

## Implemented display behavior

- Current detections use their exclusive-upper raw boxes, subtle neon glow and
  their owning track's ID/color. Unassociated detections say “candidate”.
- ID hashing provides persistent cyan/lime/magenta/orange/yellow channels.
  Selected geometry has full opacity and stronger strokes; other tracks use 0.3
  opacity. Clicking boxes, labels or paths and selecting a sidebar row works.
- History includes only actual `observed` points through the visible frame.
  Filled dots and solid segments fade with age; newest dots are brighter.
  Interpolated/extrapolated points never count as observed history or support.
- `track.trajectory.predictions` supplies forecasts. Hollow glowing dots and
  dashed segments use a contrasting per-track color, anchored at the last actual
  observation. Only predictions strictly after that observation are shown, once
  the visible frame reaches it. No browser extrapolation is invented.
- Final-frame status highlights available forecasts. Results without fitted
  forecasts explicitly say none are available. Off-image geometry is clipped,
  never clamped or distorted into the image.
- Independent Detections / Tracks / Predictions toggles, playback at 750 ms per
  frame, step/scrub controls, 1–8× zoom, pointer-anchored wheel zoom, drag pan and
  Fit. Zoom/pan and selection persist through navigation.
- Image and geometry share a single SVG viewBox. Original image dimensions and
  aspect ratio are preserved, including letterboxing. Strokes are non-scaling;
  labels/markers account for both fit scale and zoom using ResizeObserver.
- Local JSON/image decoding errors remain visible. Explicit image ordering,
  equal dimensions, result frame bounds and registration dimensions are checked.
  JSON parsing is a rendering guard, not a replacement for backend validation.
- Cached result/source labels, heuristic-quality wording, warnings, trajectory
  pixel units and identity-unverified wording are retained.

## Integration imports and coordinates

```tsx
import { TrackingWorkbench } from './components/TrackingWorkbench';
import type { ViewerFrame, Matrix } from './visualization/overlay';
import type { AnalysisResult } from './types/contracts';

// result: the unchanged backend AnalysisResult 0.1.0.
// frames: original images for this same result, with explicit zero-based indices.
const frames: ViewerFrame[] = [{
  frameIndex: 0, imageUrl: approvedFrameUrl, width: 640, height: 480,
  referenceToRaw: inverseTransform as Matrix, // optional only when alignment permits
}];
// Render this in the team's existing successful-analysis view:
<TrackingWorkbench result={result as AnalysisResult} frames={frames} />;
```

Props: `TrackingWorkbench({ result: AnalysisResult, frames: ViewerFrame[] })`.
`Matrix` is a finite 3×3 homogeneous transform. `ViewerFrame` is frontend display
metadata, not a modification to SequenceInput or AnalysisResult.

All supplied images must be **original/native** frames with their declared
dimensions; do not supply aligned crops or resized images with native metadata.
Current boxes are already raw. Historical and forecast points use the declared
reference coordinates and are mapped through the **current frame's**
`reference_to_raw`, including all past points. Applying each historical frame's
raw position to the current image would be incorrect under camera motion.

Identity / not_required registration and results explicitly declared `raw` use
their common coordinates directly. Frame 0 can serve as the `reference_frame_0`
anchor. Other registered native frames need their inverse transform. Missing
alignment suppresses history/forecasts and shows a notice; native boxes remain.
Failed T13 report frames do not supply usable transforms. No transform is guessed.

Local `parseRegistration(value)` reads the existing T13 `registration.json`, with
`transform_direction: raw_to_reference`, `coordinate_frame: reference_frame_0`,
and `frames[].reference_to_raw`. It returns `Map<number, Matrix>` and skips failed
frames. The page also verifies report `width_px`/`height_px` against native images.

Member 1: embed the component in your actual completed-job page and supply
approved original-frame URLs plus the already-existing inverse transforms.
Retain your current job/upload/run workflow. No new API route, arbitrary path
request or backend contract change was added here. If the working workbench is
in another checkout, port these components there before claiming live integration.

Member 3: preserve observation detection IDs and point types. Forecasts belong
in `trajectory.predictions`; supply no fabricated detection IDs. Missed frames
have history but no current box. The viewer does not change association gates,
lifecycles or trajectory fitting. It cannot create predictions for short tracks.

## Commands actually run

Environment: Windows, Node 24.19.0, npm 11.17.0; existing React 19, TypeScript 5.9
and Vite 7 dependencies. No new package or Python dependency is required.

```powershell
Set-Location E:\Fusion\frontend
npm run build
node --test tests/overlay.test.mjs
npm run dev -- --port 5173
```

- Final build: TypeScript and Vite passed, 38 modules transformed.
- Final unit/integration-format checks: **19 passed, 0 failed, 0 skipped** here.
  Two optional artifact tests skip on a checkout without the saved CV reports;
  the other 17 tests use the committed contract fixtures. Node 24's native
  TypeScript stripping executes the pure display helpers without a new runner.
- Dev server: 5173 and 5174 were already occupied, so Vite selected 5175.
  Open the URL printed by Vite with `/#/workbench`; this run used
  `http://127.0.0.1:5175/#/workbench`.
- `git diff --check -- frontend`: passed; Git printed normal LF/CRLF notices.

Tests cover current detection ownership, empty/unassociated cases, missed
observations, past-frame leakage, strict forecast timing, interpolated-point
exclusion, transform direction/perspective, finite coordinates, off-image
clipping policy, raw double-transform prevention, zoom anchor invariance,
persistent contrasting palettes and invalid/singular input rejection.

Actual saved backend artifacts for counts_change and train_84 were parsed and
checked through all five frames. Current registered points map to their native
detection centers within **1e-6 px**, not merely to plausible-looking positions.

## Browser verification and reproducible outputs

1. In the viewer, select AnalysisResult JSON, then the original five images.
2. Confirm/reorder the images to `1.png, 2.png, 3.png, 4.png, 5.png` (indices 0–4).
3. Select the matching T13 registration JSON and open the confirmed frame order.
4. Scrub to frame 5, select a track, toggle overlays, zoom and drag the image.

Synthetic saved backend output (not real data or a fresh HTTP analysis):

```text
E:\Fusion\artifacts\reports\cv_readiness\final\counts_change\tracking_registered.json
E:\Fusion\artifacts\reports\cv_readiness\final\counts_change\registration.json
E:\Fusion\artifacts\reports\cv_readiness\final\counts_change\1.png through 5.png
```

Browser final frame: **5 boxes, 22 observed dots, 10 hollow forecast dots and
10 dashed segments**. Selected track had opacity 1, others 0.3. Turning predictions
off left 22 observations; turning tracks off left 10 predictions. Pan viewBox
`42.3781813804016 34.52242402353417 213.33333333333334 160` persisted unchanged
through navigation at 1.5×. Fit restored `0 0 320 240`.

Real ESA saved backend output:

```text
E:\Fusion\artifacts\reports\cv_readiness\final\train_84\tracking_registered.json
E:\Fusion\artifacts\reports\cv_readiness\final\train_84\registration.json
E:\Fusion\data\raw\SpotGEOv2\train\84\1.png through 5.png
```

Browser final frame: native **640×480**, **6 boxes, 34 observed dots, 0 forecasts**.
This result has no fitted trajectories; no forecasts were invented. Clearing
transforms left 6 boxes, 0 path dots and the alignment notice. All toggles off
left 0 boxes/dots. These artifacts stay ignored and are not bundled in source.

Browser checks also covered an empty authored result (0 boxes/points, visible
no-tracks message), invalid-result rejection with Open disabled, and playback.
A fresh-session empty/error test had no console errors. A development-only React
Fast Refresh warning occurred when an effect dependency list was edited during
the session; it is not a production build failure.

Laptop viewport test: 1280×900. Mobile test: requested 390×844; effective content
width 375 px with scrollbar, document width also 375 px (no horizontal overflow).
The native viewBox remained unchanged. Temporary viewport override was reset.

Local ignored screenshots:

```text
E:\Fusion\.cache\ui-tracking\forecast-final.png
E:\Fusion\.cache\ui-tracking\esa-final.png
E:\Fusion\.cache\ui-tracking\mobile-final.png
```

## Remaining limitations / next dependency

No fresh analysis or live result HTTP integration was tested; this checkout has
no working analysis page/API to attach to. The completed component consumes the
actual backend result format via props and local files. Integration needs to wire
it into the team's working analysis checkout and provide native frames/transforms.
The local viewer cannot independently establish that manually selected files
belong to the same job; pairing and order require user confirmation.

No detector/model training, backend tests, benchmark rerun or association changes
were part of this frontend task. Next: Member 1 wires the viewer to a real completed
job, then runs a browser + HTTP test from upload/run through final-frame review.
