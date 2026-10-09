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

## Follow-up: visible connections and PDF report (2026-10-10)

Base revision: `80a988df9abf07125c209b63e6e45c53e47c0238` on Subham.
This supersedes the preceding JSON-only limitation: Download Report now saves
a real frontend-generated PDF directly; Report JSON retains the complete data.

Observed root causes in the user's current 640x480 upload:
- Default track-0001 had one observation, so no legitimate segment existed.
- Track-0002 and track-0003 each had five observations and four SVG segments.
  Existing `.observed-point` CSS forced cyan dots while the owning lines used
  lime/magenta. The non-selected tracks were heavily dimmed.
- Selected track-0002's registered full-track displacement was only 0.919 px;
  its points/segments nearly overlapped on the native image. Other central dots
  were different single-observation track records and cannot honestly be linked.

Changes: explicit matching colors on observed dots/lines and forecast markers,
stronger glowing strokes, non-selected opacity 0.5, automatic longest observed
track selection, observation counts in track options, explanation for single
observations, and a separately labeled enlarged selected-track path detail.
The detail retains reference coordinates and aspect ratio; the main raw image
overlay is unchanged geometrically. Detail observations follow timeline frames;
future dashed/hollow markers appear after the last observed frame only, and
only when prediction and observation coordinate frames match.

PDF: dependency-free PDF 1.4, A4, Helvetica, paginated source/frame metadata,
selected track/quality bar, motion summary, observed raw/reference tables,
forecast table, warnings/limitations and page numbers. No backend/schema or
package/lock changes. PDF strings are escaped, byte offsets/stream lengths are
computed, and long text is wrapped. Coordinates are rounded to 3 decimals in
PDF; JSON preserves exact values. Non-ASCII PDF text is transliterated when
possible, otherwise replaced with `?`; original filenames remain in JSON.

Follow-up exact staging allowlist:
```text
frontend/src/components/workbench/LocalWorkbench.tsx
frontend/src/components/workbench/T08Overlay.tsx
frontend/src/components/workbench/TrackPathDetail.tsx
frontend/src/components/workbench/t08-overlay.css
frontend/src/viewer/pdfReport.ts
frontend/tests/t08-overlay.test.ts
frontend/tests/track-report.test.ts
docs/handoffs/T11_LIVE_PATH_REPORT.md
```

Actual commands: same frontend commands above, now 115 data/component tests plus
19 legacy overlay tests passed (134 total); TypeScript/Vite build passed with
the existing large landing chunk warning. Python tests were not repeated for
these additional UI-only edits.

Browser tests on the actual annotated upload: track-0002 selected automatically;
frames 1..5 yielded 1..5 dots and 0..4 connecting segments, matching lime point
and line colors, separate magenta forecast, enlarged path, single-observation
explanation, and actual PDF download without navigation. Job
`job-1479c61680764933a36507f2bd754df4`: 24 detections, 16 tracks, 4 predictions.
Additional genuine five-image browser upload regressions:
synthetic counts-change 22 detections/5 tracks/10 forecasts (selected 5 dots,
4 lines); ESA84 34 detections/31 tracks/0 forecasts (selected 2 dots, 1 line);
empty result 0/0/0, valid PDF with no selected track. Console errors/warnings: 0.

Actual downloaded PDFs were reopened with `pypdf` strict parsing; text bounds
verified with `pdfplumber`. The annotated upload's two PDF pages were rendered
via Poppler and visually inspected: no clipping/overlap. Poppler emitted two
local fallback-font notices (`Symbol`/`ArialUnicode`) but rendered Helvetica
correctly; no such fonts are referenced by the report. All four browser PDF
downloads parsed successfully and their text stayed inside margins.

Ignored evidence: `.cache/pdf-path/actual-upload-report.pdf`, three regression
PDFs, rendered PDF pages, browser-regressions JSON and connected-path screenshots.
User's current result tab remains available; select a multi-observation track
and use Download Report (PDF). Production Vercel deployment still requires the
owner action described above; this local verification does not claim a new
production deployment. Existing unrelated Git changes remain excluded.
