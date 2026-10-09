# T20 — Latest development UI integrated in original Fusion

Verdict: **PASS**, implemented and tested locally. Branch `Subham`; base/unchanged HEAD `b07fe9873a39cd8897374078a7729cb4a50d6737`. Latest fetched development: `97a617c536e001a06a1cf3998c62113d10e4a2ac` (design commit `9b41c47`). No branch/worktree/clone created; no stage, commit, push, merge or rebase. Only `E:\Fusion` was modified. Other project folders, datasets, backups and experiments were preserved.

## Files and reconciliation

26 files match fetched development bytes exactly; 6 files reconcile its design with original live integration. No frontend source was removed. package.json, package-lock.json and vite.config.ts are unchanged. This is plain CSS, React, existing Three.js and GSAP; no Tailwind or new dependency was added.

| Path relative to E:\Fusion | Action | Import |
|---|---|---|
| `frontend/index.html` | Modified | Exact upstream |
| `frontend/public/assets/earth-blue-marble.provenance.json` | Created | Exact upstream |
| `frontend/public/assets/earth-blue-marble.webp` | Created | Exact upstream |
| `frontend/public/assets/earth-clouds.jpg` | Created | Exact upstream |
| `frontend/public/assets/earth-clouds.provenance.json` | Created | Exact upstream |
| `frontend/public/assets/orbittrace-earth-background.provenance.json` | Created | Exact upstream |
| `frontend/public/assets/orbittrace-earth-background.webp` | Created | Exact upstream |
| `frontend/src/App.tsx` | Modified | Exact upstream |
| `frontend/src/components/HealthPanel.tsx` | Modified | Exact upstream |
| `frontend/src/components/landing/CapabilitySection.tsx` | Modified | Reconciled |
| `frontend/src/components/landing/HeroCanvas3D.tsx` | Modified | Exact upstream |
| `frontend/src/components/landing/SpaceHero.tsx` | Modified | Exact upstream |
| `frontend/src/components/landing/createDecorativeSatellite.ts` | Created | Exact upstream |
| `frontend/src/components/workbench/AnalysisPanel.tsx` | Modified | Reconciled |
| `frontend/src/components/workbench/BackendConnection.tsx` | Modified | Exact upstream |
| `frontend/src/components/workbench/DemoWorkbench.tsx` | Modified | Reconciled |
| `frontend/src/components/workbench/LocalWorkbench.tsx` | Modified | Reconciled |
| `frontend/src/components/workbench/OpticalViewer.tsx` | Modified | Exact upstream |
| `frontend/src/components/workbench/WorkbenchShell.tsx` | Modified | Exact upstream |
| `frontend/src/pages/LandingPage.tsx` | Modified | Exact upstream |
| `frontend/src/pages/ReadinessPage.tsx` | Modified | Reconciled |
| `frontend/src/pages/WorkbenchPage.tsx` | Modified | Exact upstream |
| `frontend/src/styles.css` | Modified | Exact upstream |
| `frontend/src/styles/interactions.css` | Modified | Exact upstream |
| `frontend/src/styles/landing.css` | Modified | Exact upstream |
| `frontend/src/styles/layout.css` | Modified | Exact upstream |
| `frontend/src/styles/product.css` | Created | Exact upstream |
| `frontend/src/styles/readiness.css` | Modified | Exact upstream |
| `frontend/src/styles/tokens.css` | Modified | Exact upstream |
| `frontend/src/styles/workbench.css` | Modified | Exact upstream |
| `frontend/tests/analysis-jobs.test.ts` | Modified | Exact upstream |
| `frontend/tests/live-visualization.test.ts` | Modified | Reconciled |

Created this handoff and `docs/handoffs/T20_LATEST_UI_FILES.txt`. Temporary helpers `.cache/t20_integrate.py` and `.cache/t20_finalize.py` are excluded from publication. Evidence/backup files are under `.cache/t20-ui-backup` and `artifacts/reports/t20_ui`; generated outputs are excluded.

The observation panel uses the new toolbar, section navigation, compact status, inspector, emerald theme and responsive layout while retaining its real five-file multipart upload and analysis state. Results lead with counts and warnings; detailed tables/provenance remain available in a disclosure. Synthetic controls follow observations and stay explicitly labelled. Homepage has the new NASA-textured decorative globe, satellites, horizon background, lazy graphics loading, card styling and animations. Asset hashes match their retained provenance records. Decorations are not analysis data. Capability/readiness descriptions were corrected to reflect actual uploads and exports. Mobile Analyze retains an accessible name despite its compact icon treatment.

Preserved byte-for-byte from pre-T20: API client, response validation, transport, frame manifest validator, useAnalysisJob, analysis state, contracts/types, Vite proxy, T08Overlay, ScientificOverlay wrapper, trackColors, upload/scientific coordinate mappers, frame retrieval and local loading/playback hooks. All 94 inventoried backend/CV/script/config files are unchanged. Detector/tracking/schema/pipeline code was not edited; schema stays 0.1.0.

Neon boxes use real `detections[].bbox_raw_px` / `x_raw_px` / `y_raw_px`. Track association uses actual detection IDs and `tracks[].points` with `point_type=observed`; trajectories use actual `trajectory.predictions`. Reference coordinates are inverse-transformed into the displayed raw frame using verified diagnostics. The same native coordinate plane transforms image and SVG; integer centers use viewBox `-.5 -.5 width height`, with exclusive-upper boxes offset by half a pixel. Previous observations stop at timeline index; future points appear only after the last observation. Colors, selected-track opacity, solid filled observations and contrasting dashed hollow forecasts are preserved.

## API compatibility and actual execution

Live OpenAPI saved in `.cache/t20-ui-backup/openapi.json`. Verified GET health, POST upload/demo, GET job/result/frame/manifest/diagnostics and JSON/CSV exports with the original service. Frontend `/api` proxy still targets `http://127.0.0.1:8000`. No fixture is substituted for a failed real analysis. Unsupported and uncertain inputs reject the whole job; registration failure blocks tracking. Valid empty telescope frames succeed with no geometry. Unknown upload timestamps remain null; units remain pixels/frame.

| Genuine HTTP job | Status | Detections per frame | Fitted trajectories | Error |
|---|---|---|---|---|
| synthetic-demo | succeeded | [1, 1, 1, 1, 1] | 1 | none |
| counts-change | succeeded | [5, 3, 4, 5, 5] | 5 | none |
| empty-targets | succeeded | [0, 0, 0, 0, 0] | 0 | none |
| daylight-like | failed | None | None | unsupported_observation |
| noise-only | failed | None | None | uncertain_observation |
| registration-failure | failed | None | None | registration_failed |
| esa-train-84 | succeeded | [7, 7, 6, 8, 6] | 0 | none |
| esa-train-438 | failed | None | None | registration_failed |
| synthetic-upload | succeeded | [1, 1, 1, 1, 1] | 1 | none |

Nine genuine TCP jobs ran through `http://127.0.0.1:5173`. Five successful result payloads passed frontend contract validation and production T08 mapping/rendering. Final rendered geometry: multi-object 5 boxes / 22 observed points / 17 connecting segments / 10 forecasts; single object 1 / 5 / 4 / 2; ESA train/84 6 current boxes / 34 past observations / 0 forecasts; empty 0 / 0 / 0 / 0. ESA's 31 track records do not imply confirmed trajectories or debris identity. Invalid MIME/count return 422; oversized upload returns 413. CORS 204; successful manifests preserve timestamps.

## Tests actually run

- `npm ci`: succeeded, 78 packages added, 79 audited, zero vulnerabilities. Existing dependencies/lock unchanged. Nonblocking npm warning about esbuild postinstall allowScripts remains; build ran successfully.
- `node tests/run-data-tests.mjs`: **102 passed**, zero failed/skipped (101 retained plus section/source regression).
- `node tests/overlay.test.mjs`: **19 passed**, zero failed/skipped.
- `npm run build`: TypeScript `tsc --noEmit` and Vite **passed**, 87 modules; final build 2.51 s. Workbench bundle ~322 kB; lazy homepage graphics ~662 kB emits Vite's >500 kB advisory. No compile error.
- Full `python -m pytest -q -rs`: **500 passed**, zero failed/skipped, 80.28 s. Five existing warnings: Starlette/httpx deprecation, three legacy 422-name deprecations, and deliberately invalid FITS BLANK metadata. No dependency/schema modification was made to silence them.
- `verify_final_http.py`: **9 genuine jobs passed their expected outcomes**, including supported/empty successes and expected suitability/registration failures.
- `verify-live-results.mjs`: **5 real result contracts accepted**.
- `verify-t08-http.mjs`: **5 genuine HTTP result/image sets mapped and rendered correctly**.

## Browser verification

Codex in-app browser used actual file choosers, confirm-order controls and Analyze. Browser receipt: `artifacts/reports/t20_ui/browser/verification.json`, 24 recorded checks and six main scenario cases, plus a repeated multi-object upload and separate synthetic demo. Verified homepage design, homepage-to-workbench navigation, readiness, capabilities/mobile navigation, five-image upload, queued/loading/progress, successful polling, actual PNG retrieval, empty/suitability/registration errors, invalid and corrupt PNG rejection preserving the confirmed sequence, clear/reset, selection, all toggles, playback, frame navigation, fit/150%/800% zoom, keyboard and pointer pan, and mobile 390x844 with no document overflow. At 800% raster and SVG bounds match exactly and raw box bounds remain unchanged. Frame 4 has 17 observations and zero forecasts; final frame has 22 observations and 10 forecasts. Real ESA has no invented forecasts. Main page console: zero warnings/errors. Expected HTTP rejections were tested separately; no browser network interception was used.

Screenshots: `homepage.png`, `multi-final.png`, `multi-full.png`, `esa-final.png`, `empty.png`, `unsupported.png`, `registration-failure.png`, `mobile.png`, `readiness.png` in `artifacts/reports/t20_ui/browser`.

## Processes, URLs and startup

With explicit user approval, verified old Fusion Vite PID 30892 and its esbuild child 29536 were stopped for npm ci. CloseMainWindow was attempted; the headless Node process has no window, so targeted termination was required. No unrelated process/backend was stopped. Current frontend PID **19296**, esbuild **23024**, port **5173**, launched with working directory `E:\Fusion\frontend`. Backend unchanged: launcher **10948** at `E:\Fusion\.venv\Scripts\python.exe`, listener child **18108**, port **8000**. The child uses the bundled base Python interpreter; editable app/orbittrace and astrotrace modules resolve under E:\Fusion. Native runtime binaries may live outside the repository; source/services are the original Fusion application.

Already running: website http://127.0.0.1:5173/#/workbench ; homepage http://127.0.0.1:5173/ ; backend http://127.0.0.1:8000/docs . Do not start duplicates while occupied; existing startup scripts check ports and do not kill processes.

Terminal 1, when backend is stopped:
```powershell
Set-Location E:\Fusion
.\scripts\Start-Backend.ps1
```
Terminal 2, when frontend is stopped:
```powershell
Set-Location E:\Fusion\frontend
..\scripts\Start-Frontend.ps1
```

## Reproduce tests and inspect outputs

```powershell
Set-Location E:\Fusion\frontend
# npm ci requires the frontend to be stopped to release Windows esbuild locks.
node tests/run-data-tests.mjs
node tests/overlay.test.mjs
npm run build

Set-Location E:\Fusion
$env:CV_TRACK_SOURCE='E:\Fusion\data\raw\SpotGEOv2'
$env:CV_T06_REAL_SOURCE=$env:CV_TRACK_SOURCE
$env:CV_T06_TRACKING_SNAPSHOT='E:\Fusion\.cache\original-consolidation-20261010\tracking-snapshot'
.\.venv\Scripts\python.exe -m pytest -q -rs

# Both services must be running. Use a new output directory for each HTTP replay.
$t20RunTag=Get-Date -Format yyyyMMdd-HHmmss
$t20Output="artifacts/reports/t20-recheck-$t20RunTag"
.\.venv\Scripts\python.exe -I scripts/verify_final_http.py --url http://127.0.0.1:5173 --esa data/raw/SpotGEOv2 --output $t20Output
Set-Location E:\Fusion\frontend
node tests/verify-live-results.mjs "../$t20Output"
node tests/verify-t08-http.mjs "../$t20Output" http://127.0.0.1:5173
```

To inspect visually, open the website, Choose images, select `E:\Fusion\artifacts\reports\t20_ui\http\counts-change\1.png` through `5.png`, Confirm order & view, Analyze, then Inspect frame 5. Repeat using `esa-train-84` to inspect real 640x480 detections. Expand `Inspect detection tables, track history & provenance`; JSON/CSV links belong to that actual job. Saved JSON evidence is `artifacts/reports/t20_ui/http/*_result.json` and `receipt.json`; browser receipts/screenshots are adjacent under `browser`. In-memory jobs expire/restart; saved evidence survives.

## Backup and publication

Pre-edit backup `E:\Fusion\.cache\t20-ui-backup\files\frontend`, **83 source files verified**, includes tracked/untracked source, lock and environment templates. `manifest.json` has original hashes; `RESTORE.md` gives exact one-file recovery. Secret env files, node_modules and dist were excluded and not overwritten by source import. To restore one reviewed file:
```powershell
Set-Location E:\Fusion
Copy-Item -LiteralPath .cache\t20-ui-backup\files\frontend\src\App.tsx -Destination frontend\src\App.tsx
```
Do not blindly erase/replace frontend or discard uncommitted work. New files have no pre-T20 counterpart; review the created-file manifest before any removal. Original datasets/backups/experiments remain untouched. `final-manifest.json` records exact imports, reconciliations and protected-file checks; before/after Git status is saved alongside it.

`docs/handoffs/T20_LATEST_UI_FILES.txt` is the proposed **T20-only staging allowlist**, a delta against this working local foundation, not a standalone clean-checkout integration set. The T19 real API/packaging/T08 foundation is also still uncommitted; review the existing T19 allowlist and required dependencies together before approving a complete publication. Review exact diffs before any explicit user-approved publication to Subham. Exclude .cache, node_modules/dist, data, generated artifacts/checkpoints/environments, secrets, unfinished T15 and unrelated pre-existing changes. Do not use broad `git add .`. No Git index operation or publication was performed in T20; existing uncommitted/staged state is retained.

## Remaining issues and next dependency

No T20 integration blocker remains. Nonblocking warnings are the existing Python dependencies/FITS test, npm allowScripts notice and the large decorative homepage graphics chunk. Scientific limitations remain: heuristic candidates, no identity/orbit/collision/altitude claims; real ESA train/84 has no fitted trajectory; arbitrary daylight/noise/failed registration must reject, not return fabricated success. FITS ingestion remains backend/CV functionality; the browser chooser continues to accept JPEG/PNG only as before. Optional next task: review T20-only diffs and approve publication on Subham; separately optimize homepage graphics loading if desired. No automatic publication or unrelated algorithm work is authorized.
