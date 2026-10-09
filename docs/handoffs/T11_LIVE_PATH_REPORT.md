# T11 follow-up — live object paths and downloadable reports

Base: `Subham`, `8126ae817172da2e0e07294770c2626201adbe38`.
Scope: frontend rendering/reporting only. Backend algorithms, schema 0.1.0,
dependencies and lockfiles are unchanged.

## Implemented and tested

- Main workbench contains uploaded/live analysis only. The synthetic runner is
  removed from this page; the explicitly conceptual landing preview remains.
- Selected observed paths have brighter solid neon segments and filled markers.
  Previous observations fade. The actual current observation has a ring and one
  frame label; a missed detection has neither a current ring nor a fabricated box.
- Existing timeline filtering, raw boxes, stable track colors and contrasting
  dashed/hollow forecasts remain. Forecasts start after the last observation.
- Selected confidence panel shows actual `Track.quality_score`, percentage, a
  normalized meter, actual observation count, track ID and image-plane direction.
  Low `<0.4`, medium `<0.7`, high otherwise are display bands, not calibration.
- Download Report saves frontend-generated JSON without navigation. It contains
  uploaded filenames/dimensions/null timestamps, analysis counts, selected-track
  observed and future positions, heuristic quality, direction/summary, limitations
  and the full original backend `AnalysisResult`. Backend JSON/CSV links open a
  separate tab, preserving the live workbench.

## Exact changed files / staging allowlist

```text
frontend/src/components/workbench/LocalWorkbench.tsx
frontend/src/components/workbench/T08Overlay.tsx
frontend/src/components/workbench/TrackQualityPanel.tsx
frontend/src/components/workbench/WorkbenchShell.tsx
frontend/src/components/workbench/t08-overlay.css
frontend/src/pages/WorkbenchPage.tsx
frontend/src/viewer/trackReport.ts
frontend/tests/live-visualization.test.ts
frontend/tests/run-data-tests.mjs
frontend/tests/t08-overlay.test.ts
frontend/tests/track-report.test.ts
docs/handoffs/T11_LIVE_PATH_REPORT.md
```

## Geometry and reporting

`uploadOverlay()` still projects historical reference positions through the
displayed frame's verified `reference_to_raw` translation. Current bounding boxes
use raw detection coordinates with exclusive upper edges. Image and SVG share
one zoom/pan plane and integer pixel centers. No guessed registration is used.

Reports retain `x_reference_px`/`y_reference_px` and original per-frame raw pairs,
and separately declare observation/prediction coordinate frames. They do not
export current-screen positions as raw measurements. Summary direction uses
first/last actual observations in the declared result frame (top-left origin,
positive y downward). Missing points remain missing. Only future extrapolations
are listed as forecasts; the original result remains available verbatim.

## Actual verification on 2026-10-10

```powershell
Set-Location E:\Fusion
node frontend/tests/run-data-tests.mjs
node --test frontend/tests/overlay.test.mjs
& .\.venv\Scripts\python.exe -I -m pytest tests/api/test_t09_api.py tests/api/test_frame_retention.py -q
Set-Location E:\Fusion\frontend
npm run build
```

- Frontend data/component tests: 112 passed, 0 failed. Legacy overlay tests:
  19 passed, 0 failed. Backend upload/frame-retention tests: 15 passed, 3 existing
  Starlette deprecation warnings. TypeScript and Vite production build passed.
  Vite warns about the existing large landing-page chunk (661.98 kB).
- Genuine browser uploads through `POST /api/analyze/upload`, job polling,
  result and diagnostics retrieval on the local backend:
  synthetic counts-change: 22 detections, 5 tracks, 10 backend forecast points;
  ESA train/84: 34 detections, 31 tracks, 0 forecasts;
  empty-targets: successful empty result;
  daylight-like: `unsupported_observation`;
  registration-failure: `registration_failed`, tracking blocked.
- Selected synthetic track-0002: observations 1/2/3/4/5 and segments 0/1/2/3/4
  as frames advance. Rewind removes future observations. Forecasts appear only
  at frame 5. Replay showed 3 observations at frame 3 and 5 at frame 5.
- Track-0001's missed frame 2 retains its prior point without current box/ring
  or early forecast. All three toggles were independently verified.
- Zoom 225% and keyboard pan changed the shared image/SVG plane while native
  box coordinates stayed unchanged. ESA uses the 640x480 SVG viewBox.
  Mobile viewport test had no horizontal page overflow; selected points,
  quality meter and download control remained available.
- Actual browser JSON downloads succeeded for synthetic, ESA and empty results.
  Synthetic report job/score were cross-checked against HTTP result retrieval;
  the page URL and analysis state stayed intact. Console errors/warnings: none
  in these browser runs. Loading/polling transitions are covered by unit tests;
  these small HTTP jobs completed too quickly to visually time every stage.
- Full backend suite was not rerun for this frontend-only change.

Local evidence (ignored, not staged): `.cache/live-path-report/` contains
`synthetic-report.json`, `esa-report.json`, `empty-report.json`,
`synthetic-api-result.json`, browser path/negative-case JSON and screenshots.

## Startup and viewing

Open two PowerShell terminals, when the ports are free:

```powershell
Set-Location E:\Fusion
.\scripts\Start-Backend.ps1
# Second terminal:
Set-Location E:\Fusion
.\scripts\Start-Frontend.ps1
```

Open `http://127.0.0.1:5173/#/workbench`. Choose five PNG/JPEG images, confirm
their order, Analyze, select a track, advance/replay, then Download Report.
Reproducible local images: `.cache/vercel-connect/http-mirror/counts-change/`
and `.cache/vercel-connect/http-mirror/esa-train-84/`, files `1.png` to `5.png`.
These local validation images are not new published datasets.

Existing listeners were preserved: backend 8000 PID 18108, Vite 5173 PID 19296.
Startup scripts refuse occupied ports and do not stop other processes.

## Publication / remaining limitations

The user authorized committing and pushing this tested change to `Subham`.
Stage only the allowlist above. Existing Dockerfile/deployment-doc changes,
Railway ignore, Vercel wrapper, Ultralytics, datasets and generated evidence are
excluded. No main/development push, merge, rebase or unrelated cleanup.

Testing proves the updated local application. It does not prove that Vercel
production has deployed this Subham change. The existing Vercel owner's project
is inaccessible to the currently authenticated CLI account; production needs an
owner deployment of this revision. Keep Production `VITE_API_BASE_URL` pointing
at `https://orbittrace-api-production.up.railway.app`, then verify the new report
button and a fresh upload on the production URL. Railway backend/schema requires
no update for this frontend change. JSON is supported; HTML/PDF reports are not
implemented. Heuristic quality is not scientific identity confidence.
