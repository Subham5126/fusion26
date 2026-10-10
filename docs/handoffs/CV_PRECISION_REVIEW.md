# CV-T04 precision review / T11 workbench follow-up

Base: `f151108`, branch `Subham`. Implemented and tested on 2026-10-10 in
`E:\Fusion`. This follows the user's request to reduce false candidates, shorten
the final-frame forecast and simplify the workbench. No schema, tracking source,
trajectory algorithm, dependencies, lockfiles or original detector algorithms
were changed. This is a configuration improvement, not new model training.

## Actual detector change and evidence

The optimized adapter and live CV pipeline now use `precision_config()`:
`threshold_sigma=4.5`, `max_context_elongation=2`, `min_score=0.3`,
`min_aperture_snr=4`, `max_peak_fraction=0.45`. Other original defaults remain,
including the 200-candidate frame cap. The unchanged detector remains
`opencv_context_filtered_v2`. Baseline T03 and CV-T04's `OptimizedConfig` defaults
are preserved. Scores and coordinates of retained proposals are not boosted or
moved. Inference only receives pixels and declared metadata.

Selection used the existing 24 training sequences (120 frames) and cached
CV-T04 proposals. The 75 combinations were score `[0,.2,.3,.4,.5]`, aperture SNR
`[0,4,8,12,20]`, and peak fraction `[.35,.45,.55]`. Choose highest precision with
at least 95% of the old development recall, then freeze the settings. Fresh native
image inference reproduced both profiles' cached metrics exactly. Annotation
loading in the reproduction script happens after inference for each partition.
Matching is one-to-one within 5 raw pixels. The existing 128 test sequences have
already been used historically: this is regression evidence, **not a new blind
test, all-ESA evaluation, or a guarantee about arbitrary uploads**.

| Existing sample | Profile | TP / FP / FN | Precision | Recall | F1 | FP/frame |
|---|---|---|---|---|---|---|
| Train, 120 frames | CV-T04 | 139 / 180 / 116 | 43.57% | 54.51% | 48.43% | 1.500 |
| Train, 120 frames | Precision | 139 / 132 / 116 | 51.29% | 54.51% | 52.85% | 1.100 |
| Test, 640 frames | CV-T04 | 640 / 991 / 450 | 39.24% | 58.72% | 47.04% | 1.548 |
| Test, 640 frames | Precision | 630 / 756 / 460 | 45.45% | 57.80% | 50.89% | 1.181 |

The test regression has 23.71% fewer false positives but loses ten true positives
(0.92 percentage points of recall). Do not present remaining proposals as
identified debris or the quality score as a calibrated probability. There is
no fixed track-count limit or assumption that a sequence must contain fewer
than 15 objects. Persistent artifacts and fragmented associations remain possible.

`CV_PRECISION_MEMBERSHIP.json` preserves the exact small historical sample list;
`CV_PRECISION_METRICS.json` records numeric configs, fresh metrics and hashes.
Membership SHA256: `9ee29f756f71028197aa503984244f23460836638293490432cbed2afb446d63`.
Train annotation SHA256: `2727e7c21f1fef229b024dcb00952d0781057661c4ccb64937dce50f08e1fdfe`.
Test annotation SHA256: `8c3e141fba0b5d3ed220563b458a17b17d73ec8cc762aa46abe40d1016f557f4`.
Original baseline source SHA256: `3f3104b87fec612891bddb0083846ecd3ded257c16d1255f65e7948201fc5841`.
Original optimized source SHA256: `35e3c10adc45af93f69e4626a5aa16b61909f73340ff72599788439224e73908`.

To reproduce the original CV-T04 behavior through the adapter or integrated
pipeline, supply the full original config, or these overrides on the new default:
`{"min_score":0., "min_aperture_snr":0., "max_peak_fraction":.55}`.
Use `config=` for `orbittrace.detection.detect_sequence` and `detector_config=`
for `orbittrace.cv_tracking.analyze_telescope_sequence`.

## Workbench behavior

- Default supported view: at least three actual observed points, quality >=0.5,
  an existing trajectory, and fit RMSE <=3 px when reported. This is a display
  policy; it does not establish object identity or mark other tracks as false.
- `Show unverified candidates` restores all backend candidates and track records.
  Raw result, reports and exports retain all proposals. The supported-track count
  remains separate from the total candidate detections.
- Quality label is now **Heuristic quality**. A two-point track with quality
  0.409 remains 0.409; it is not promoted to stronger evidence.
- Existing connected observations, neon boxes and per-track colors remain.
  Predictions display only when already supplied by a backend fit and strictly
  after the last actual observation. The preview is restricted to the next frame
  relative to the displayed frame, including frame 6 when viewing frame 5.
  Acquisition timing is unknown, so this is not a duration in seconds.
- Reference observations and forecasts still use the verified current-frame
  inverse registration transform. Native raw detection boxes share the same
  image plane during zoom and pan. No geometry is enlarged in the main overlay.
- The workbench connection/schema/check-connection/readiness panel is removed.
  Global navigation to readiness remains. Routine backend/registration warnings
  are inside the existing closed details; input, network and registration errors
  remain visible. Reports preserve warnings and limitations.
- PDF remains frontend-generated from the actual unmodified result. It includes
  the full backend prediction list (normally two frames), while the overlay
  previews only the next frame. JSON preserves full precision and raw data.

## Actual verification

Commands run: full Python suite, both frontend suites, TypeScript/Vite build,
fresh ESA precision comparison, `verify_final_http.py` through the Vite API proxy,
and actual browser file uploads. Final results:

- Python: **530 passed, 2 skipped, 6 warnings**. Optional historical Member 3
  snapshot tests skip without their snapshot configuration; actual current tracker
  compatibility ran for both detector profiles. Warnings are Starlette/httpx and
  422-name deprecations plus the intentionally invalid FITS BLANK test fixture.
- Frontend: **117 + 19 = 136 passed**. TS and production build succeeded. The
  existing landing chunk exceeds Vite's 500 kB advisory; no build failure.
- Nine genuine TCP jobs: synthetic demo, multi-object, empty, unsupported,
  uncertain/noise, registration failure, ESA train/84, ESA train/438 failure,
  and a one-object upload. Also verified bounded/type/count upload rejection,
  native frame retrieval, manifests, diagnostics, JSON/CSV exports and CORS.
- Multi-object upload: `[5,3,4,5,5]` detections, five confirmed/fitted tracks.
  One-object: `[1,1,1,1,1]`, one confirmed/fitted track. Empty: zero/zero.
- ESA train/84: `[7,5,5,8,6]` detections, 28 candidate track records, **zero
  supported tracks and zero trajectories**. Original CV-T04 remains reproducible
  at 34 detections/31 track records. No ESA forecast was fabricated.
- Browser: six uploaded sequences (multi-object, ESA, one-object, empty,
  unsupported and registration failure). Selected five-observation track grows
  1/2/3/4/5 dots and 0/1/2/3/4 solid segments. Final frame has exactly five
  next-frame forecasts, rather than ten two-frame forecasts. Neon boxes present;
  150% zoom and keyboard pan preserve native SVG geometry. Forecast toggle hides
  markers and sets the shown count to zero. Candidate toggle restores six raw
  boxes on ESA's final frame without forecasts. No captured browser console errors.
- Live synthetic and ESA PDFs downloaded and parsed successfully (two pages each).
  Actual quality, coordinate tables and warnings are retained in PDF text.

Initial failures were investigated: the full `-I` test invocation excluded the
root `scripts` package; use the normal full-suite command below. Historical
CV-T04-only count/equality assertions failed after the default-profile change;
tests now explicitly exercise preserved CV-T04 and the precision profile against
the original detector and unchanged tracker. No failing checks remain.

## Exact PowerShell reproduction

```powershell
Set-Location E:\Fusion
git branch --show-current  # Subham
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe scripts\spotgeo_precision_review.py --output .cache\precision-review\reproduced.json
Set-Location E:\Fusion\frontend
node tests\run-data-tests.mjs
node --test tests\overlay.test.mjs
npm run build
```

The ESA script uses existing `E:\Fusion\data\raw\SpotGEOv2`; no data is downloaded.
Raw images, annotations, caches, old reports and model checkpoints are excluded
from publication. Evaluation uses labels; live inference does not.

Start only when the relevant port is free, in two separate terminals:

```powershell
Set-Location E:\Fusion
.\scripts\Start-Backend.ps1
```

```powershell
Set-Location E:\Fusion
.\scripts\Start-Frontend.ps1
```

Then reproduce genuine HTTP jobs in a new output directory:

```powershell
Set-Location E:\Fusion
& .\.venv\Scripts\python.exe -I scripts\verify_final_http.py --url http://127.0.0.1:5173 --origin http://127.0.0.1:5173 --output .cache\precision-review\http-reproduced
Start-Process 'http://127.0.0.1:5173/#/workbench'
```

Select five `1.png` through `5.png` files from the generated `counts-change`,
`synthetic-upload` or `esa-train-84` directory, confirm their order, then Analyze.
Go to frame 5, select a multi-observation track, toggle predictions/candidates,
and use Download Report (PDF) or Report JSON. ESA candidates require the candidate
toggle because none satisfy supported-track review. View genuine HTTP JSON,
diagnostics and receipt in `.cache\precision-review\http-current`; PDF downloads
are in the browser's Downloads directory. Screenshot evidence is in
`.cache\precision-review\live-supported.png`, `live-supported-full.png` and
`esa-candidates.png`. These generated artifacts are not staged.

## Files / integration and publication

Exact source/test/document changes for this follow-up:

1. `src/astrotrace/detection/precision.py` (new profile)
2. `backend/orbittrace/detection/adapter.py` (profile default)
3. `backend/orbittrace/cv_tracking.py` (same profile in pipeline diagnostics/config)
4. `scripts/spotgeo_precision_review.py` (fresh benchmark reproduction)
5. `tests/detection/test_tracking_compatibility.py` (both profiles, real tracker)
6. `tests/pipeline/test_cv_track_01.py` (preserved profile and stricter subset)
7. `frontend/src/viewer/resultReview.ts` (supported review/short preview)
8. `frontend/src/components/workbench/LocalWorkbench.tsx`
9. `frontend/src/components/workbench/AnalysisPanel.tsx`
10. `frontend/src/components/workbench/TrackPathDetail.tsx`
11. `frontend/src/components/workbench/TrackQualityPanel.tsx`
12. `frontend/src/pages/WorkbenchPage.tsx`
13. `frontend/tests/track-report.test.ts`
14. `docs/handoffs/CV_PRECISION_MEMBERSHIP.json`
15. `docs/handoffs/CV_PRECISION_METRICS.json`
16. `docs/handoffs/CV_PRECISION_REVIEW.md`

Backend uses `POST /api/analyze/upload`, job polling, result and diagnostics GETs
unchanged. Member 1 must deploy both updated backend source and frontend build
to activate the changes remotely; no schema migration or new dependency is
required. Member 3's source and the 20 px live pipeline gate remain unchanged.
Do not advertise 28 candidate records as 28 established objects.

Verified local backend listener PID 10372 (launcher 16932), port 8000; Vite PID
19296, port 5173. Both serve this original workspace. Only the verified previous
backend listener 18108 was restarted to activate the new detector configuration;
Vite was preserved. Local URL: `http://127.0.0.1:5173/#/workbench`.

Publication is restricted to the sixteen files above on `Subham`, using the
user's prior explicit conditional commit/push authorization after passing tests.
Unrelated Dockerfile/deployment-doc/Vercel-wrapper/Ultralytics/railwayignore edits
remain unstaged. Public Vercel/Railway deployments are **not** updated by this
local verification or a Subham push unless the owner configures them to deploy
that branch. No main-branch merge, cloud deployment or paid resource creation.

Next dependency: validate the frozen profile on a new representative labeled
sequence set, inspect persistent artifacts and association fragmentation, then
consider temporal rejection or a separately validated YOLO experiment. These
would require additional measured evidence, not higher displayed confidence.
