# T11 — Member 4 development UI integrated with live analysis

State: implemented and tested; PASS for local integration. Base Subham commit:
`df16b6c032a1ee46d30b95c0123c956564c9678d`. Fetched development tip:
`4c61a62`, which merged Member 4/Rohit's UI commit
`a95c7fc608b9cc7fc4ea081cdead2853741a63b0` in PR #13. Work stayed in `E:\Fusion`
on `Subham`. No new project root/worktree, dataset edits or dependency installs.

## Reconciliation

Imported the latest UI commit with a no-commit cherry-pick, then reconciled its
conflicts against Subham's already functioning analysis. The older development
backend/pipeline history was not merged over the current integration. Previous
T20 styling was already incorporated in Subham; this imports its latest UI delta.

The new overview, native-size/frame summary, frame-order card, playback dock,
homepage/capability styling, simplified navigation and diagnostics drawer now wrap
the actual upload workflow. Upload submission, polling, native images, errors,
accepted transforms, candidate review, connected paths, short forecasts, quality
panel, PDF/JSON reports and backend CSV remain connected. Diagnostics describes
these implemented capabilities rather than upstream's stale “pending” text.

Routine health information stays in the optional diagnostics drawer. No synthetic
runner or fixture was reintroduced into live results; the homepage conceptual
preview remains explicitly labeled. The default view contains actual uploads.
Removed misleading “browser only; no upload” wording. The readiness route opens
the drawer without replacing the workbench; opening/closing the drawer preserves
the current analysis. Its button is visible on mobile and desktop.

The source-specific native image mapping and T08 overlay renderer are unchanged.
The complete history uses accepted reference-to-raw transforms for the current
raw frame. Detection boxes use actual native boxes with exclusive upper bounds;
only past observed points are connected; the live preview retains one future
frame of existing backend predictions. No trajectory is fabricated for ESA.
The inspector is bounded and scrollable on desktop to keep the timeline near the
image, and expands normally in the mobile stacked layout.

## Exact changed files / publication allowlist

```text
frontend/src/App.tsx
frontend/src/components/landing/CapabilitySection.tsx
frontend/src/components/layout/AppNavigation.tsx
frontend/src/components/workbench/AnalysisPanel.tsx
frontend/src/components/workbench/BackendConnection.tsx
frontend/src/components/workbench/DemoWorkbench.tsx
frontend/src/components/workbench/LocalWorkbench.tsx
frontend/src/components/workbench/OpticalViewer.tsx
frontend/src/components/workbench/SystemDiagnostics.tsx
frontend/src/components/workbench/WorkbenchShell.tsx
frontend/src/hooks/useHashRoute.ts
frontend/src/pages/WorkbenchPage.tsx
frontend/src/styles/interactions.css
frontend/src/styles/landing.css
frontend/src/styles/layout.css
frontend/src/styles/product.css
frontend/src/styles/readiness.css
frontend/src/styles/tokens.css
frontend/src/styles/workbench.css
frontend/tests/live-visualization.test.ts
docs/handoffs/T11_MEMBER4_UI_INTEGRATION.md
```

No schema/API/config/dependency/lockfile, detector, registration, association or
trajectory source changes. Package dependencies already installed; no npm ci was
needed. API base URL handling and Vite's original 8000 proxy remain unchanged.
Unrelated Dockerfile/deployment notes, `.railwayignore`, Ultralytics and
`scripts/Vercel.cmd` changes remain excluded. Backups/evidence under
`.cache/member4-ui-integration/` are ignored and excluded from publication.

## Commands actually run and results

- `git fetch origin`: succeeded; inspected source commit and both branch diffs.
- `node tests/run-data-tests.mjs`: **119 passed**, zero failures/skips, including
  two new regressions for retained upload actions and truthful optional diagnostics.
- `node tests/overlay.test.mjs`: **19 passed**, zero failures/skips. Total frontend
  checks: **138 passed**.
- `npm run build`: TypeScript and Vite passed; 91 modules. Workbench JS 334.25kB,
  lazy homepage JS 662.02kB. The existing >500kB homepage chunk advisory remains.
- Full Python `python -m pytest -q`: **539 passed, 2 skipped, 6 warnings in
  102.21s**. The skips concern optional historical tracker snapshots. Warnings are
  existing Starlette/httpx and 422-name deprecations plus intentional FITS metadata.
- `verify_final_http.py`: nine genuine jobs through original Vite 5173 all passed
  their expected outcomes, including synthetic demo/upload, changing multi-object
  counts, empty results, daylight/noise rejection, rotated registration failure,
  ESA train/84 success and known train/438 registration failure. Upload count/type/
  byte rejection, health, CORS, polling, native frames, manifests and exports passed.
- `verify-live-results.mjs`: five actual HTTP result contracts accepted.
- `verify-t08-http.mjs`: five actual result/image/diagnostics sets mapped/rendered.
  This low-level renderer check includes all backend forecasts; the live review
  layer separately limits the visible horizon to one frame.
- `git diff --cached --check`: passed for the isolated change.

## Actual browser verification

Used actual file chooser, confirmation and Analyze actions against the existing
backend; no intercepted HTTP responses or fixture fallback.

- Multi-object upload: five confirmed tracks. First frame: five points/no segments;
  third frame: 12 points/seven segments; final: 22 points/17 segments/five current
  boxes/five next-frame forecasts. Selection changed the highlighted track.
- Observed/forecast/detection toggles each suppressed only their own geometry.
  Replaying at four frames/s finished at frame 5 with 22 actual past points.
- At 150% zoom and keyboard pan, raster and SVG bounds matched exactly:
  width 856.78125px, height 642.5859375px, x -51.1546898px, y 288.2523499px.
  Pan changed the shared transform rather than native geometry; reset restored fit.
- Actual PDF download succeeded: `orbittrace-job-de745f34cfcb489dab9f14702402631a-track-0003.pdf`
  in the user's Downloads directory, 5830 bytes, `%PDF-1.4` header. PDF generation
  remains frontend-driven from current backend data; CSV remains backend-driven.
- Actual empty upload succeeded with zero boxes and “No candidates in this frame.”
  Unsupported and registration-failure uploads displayed actual errors with no
  stale geometry. Initial no-sequence controls remained disabled appropriately.
- Real ESA train/84: 31 detections, 28 candidate track records, zero supported
  tracks/fits. Candidate view shows six native boxes on frame 5 and zero forecasts.
- Real test/138: seven detections, zero supported tracks/forecasts, successful
  analysis. Diagnostics open/close retained the succeeded result.
- Mobile 390x844: no document overflow (scroll width 375px); accessible Analyze
  button and navigation menu worked. Temporary viewport override was reset.
- Homepage and its readiness link rendered the new UI; readiness opened live
  schema 0.1.0 / local_prototype health. Browser warning/error logs were empty.

One intermediate replay observation was invalidated by source hot reload during
editing, which reset analysis. The stable rerun after source edits passed. A first
geometry selector was corrected before the successful alignment check. Both are
recorded separately from passing checks in the ignored browser receipt.

Final uploaded multi-object browser job:
`job-89fc2bf597984656a671a44eda500cd0`. Evidence:
`.cache/member4-ui-integration/browser-verification.json`, `http/receipt.json`,
`multi-final.png`, `mobile.png`, `esa84.png`, `homepage.png` and frontend test log.

## Reproduction / services

The original backend listener remains PID 22772 on 8000; original Vite remains
PID 19296 on 5173. No service restart or unrelated process termination was needed.
Website: `http://127.0.0.1:5173/#/workbench`.

```powershell
Set-Location E:\Fusion\frontend
node tests/run-data-tests.mjs
node tests/overlay.test.mjs
npm run build
Set-Location E:\Fusion
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -I scripts\verify_final_http.py --url http://127.0.0.1:5173 --origin http://127.0.0.1:5173 --output .cache\member4-ui-integration\http-reproduced
```

When the ports are free, use separate PowerShell terminals:

```powershell
Set-Location E:\Fusion
.\scripts\Start-Backend.ps1
```

```powershell
Set-Location E:\Fusion
.\scripts\Start-Frontend.ps1
```

Upload five original ESA PNGs or the generated test images in the HTTP evidence
folders, confirm numeric order, Analyze, then select a track and frame. The PDF
button downloads a real report. Enable candidate view for ESA without supported
tracks. These tests prove local integration only; public Vercel/Railway deployments
were not run or verified by this task. Remaining known limits are translation-only
registration, unresolved train/438 alignment, in-memory jobs, uncalibrated quality
and no physical-orbit inference. Next dependency: review/publish this UI revision
through the existing deployment workflow and verify the public API origin with a
fresh five-image browser upload.
