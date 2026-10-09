# Latest development integration — local Windows handoff

Task: integration continuation T07 / T09 / T11; CV-TRACK-01 consumer integration.
Date: 2026-10-09. Outcome: PARTIAL overall; synthetic local application implemented and tested. ESA scientific validation remains limited.
No commit, push, branch creation, merge, rebase, reset, clean, dataset download, environment deletion or model overwrite was performed for this task.

## Base and preservation

- Repository: https://github.com/Subham5126/fusion26.
- Executed `git fetch origin development Subham` before creating the new workspace.
- Fetched development and new detached HEAD: `61e381065642a592eef5ace97cb32cb3eefefb33` (PR 8, review/member-integration).
- Original `E:\Fusion`: branch `Subham`, HEAD and origin/Subham `922fb937a109ec3231d7ec462bb88f3fdbdd62b4`, divergence 0 / 0.
- Previous `E:\Fusion-integration`: detached at `da28ab8b0aa4e7abaeec802aff1714a1b4bb8336`.
- Created `git worktree add --detach E:\Fusion-latest-dev 61e381065642a592eef5ace97cb32cb3eefefb33`; initially clean. This is a local test workspace, not a publication branch.
- Final SHA-256 audit: all 227 original-workspace and 290 previous-integration tracked/visible-untracked paths and contents are identical to the preserved baseline. Existing staged state was preserved; new workspace index is empty.
- CV-T15 best.pt unchanged: `a019175e841b8842cd84cf395b7eda9585df4f9e306c60e42c27d15a3ff97f03`.
- Existing services on ports 8000 (PID 13848) and 5173 (PID 3088) were retained. New service listeners: backend 8001 (PID 26540), frontend 5174 (PID 20784). Process IDs are session-specific.
- No datasets, model weights, generated reports, caches or environments were transferred into source or staged. Local test artifacts were generated under ignored paths in this workspace only; ESA images were read from the existing original dataset.

## Latest committed changes inspected

Relative to the previous integration base: 28 paths, 1304 insertions / 163 deletions. Relative to Subham: 95 paths, 8488 insertions / 113 deletions, plus the binary landing asset. Exact upstream inventories and diffs are under `artifacts/reports/latest_development/upstream-vs-*.{txt,diff}`.

Member 1 added JobManifest / ManifestFrame models, retained job manifests and a `GET /api/jobs/{job_id}/manifest` route. Member 4 added strict frontend manifest parsing, validated job/sequence/frame membership, actual native frame dimensions and acquisition times, and manifest-aware demo loading. Transport retains abort checks and handles string error detail. GSAP / Three.js, a decorative hero, custom cursor, scroll effects and styling were added. New manifest tests cover rejection and stale/aborted requests.

No committed changes to root Python packaging, Python lockfile, shared AnalysisResult 0.1.0, configuration or scientific algorithms occurred between the two integration bases. Development includes the existing T03/CV-T04 detection, T04 tracking and T05 trajectory code but lacks CV-TRACK-01, root packaging for astrotrace, native bounded uploads and a working telescope pipeline entry. The latest upload button was disabled and the non-synthetic pipeline still raised a missing-registration placeholder.

Latest manifest schema, frontend manifest parser/controller, DemoWorkbench, decorative hero/cursor, GSAP, assets, styles and package dependency files were preserved. Changes to concurrently updated backend job management/routes and frontend client/transport were surgical additions, rather than wholesale copies.

## Reviewable transfer and exact changed files

`docs/handoffs/LATEST-DEVELOPMENT-INTEGRATION-files.txt` is the exact source/documentation change inventory (38 paths: 23 modified and 15 untracked). It includes this handoff and its inventory; generated artifacts are excluded.

Before transfer, `.cache/prepare_latest.py` compared each modified-existing candidate's blob at the old integration base and latest development. It copied only unchanged upstream paths, and required new paths to be absent. `.cache/transfer_plan.json` records all 20 copied files and source SHA-256 hashes. It contains the six CV-TRACK-01 allowlist files, root packaging, bounded-upload helper, upload overlay/controller support and verification code. The two algorithm source modules, CV tests, script and two historical handoff files remain exact copies of the reviewed six-file source.

These six files alone do not wire up the application. They depend on already committed detection, suitability, registration, shared schemas, tracker and fitter. Importing from an installed package also requires astrotrace in root packaging; backend-only installation omits it. Full browser operation requires API upload, pipeline/job orchestration and UI/controller changes. The previous 40-file integration batch was not applied wholesale: only compatible required paths were selected, with latest routes/manifest/transport preserved.

The complete review patch including untracked files is `artifacts/reports/latest_development/local-integration.patch`; the hash inventory is `local-files-sha256.json`. `git diff --check` and reverse application validation of the review patch passed. No path was staged.

## Implementation and contracts

- Root pyproject installs `app`, `orbittrace`, `astrotrace`; existing backend requirements.lock.txt and frontend package-lock.json remain unchanged. This packaging is local to the new workspace.
- Pipeline retains its trusted synthetic path. Only telescope/non-trusted input delegates to `analyze_telescope_sequence`, retaining suitability checks, native T03/CV-T04 detection, registration, gated minimum-cost association and existing image-plane fitter. No YOLO dependency is required or installed.
- AnalysisResult remains schema 0.1.0. Raw detections stay raw; reference-frame tracks and forecasts are transformed back to the inspected raw frame for display. Unknown timestamps remain null and uploads use px/frame. Predictions do not count as observations.
- Exactly five native grayscale PNG/JPEG frames; 10 MiB/file, 50 MiB aggregate file bytes, 51 MiB request including multipart overhead. Streamed reads, signature/header bounds, dimensions/orientation validation and native uint16 preservation precede analysis. Actual file hashes replace client-supplied hashes. Existing SequenceInput contains no truth path, arbitrary disk path or remote URL.
- Existing JobManifest lifecycle is retained; diagnostics follow job lifecycle. One active job, atomic capacity reservation, incoming-aware retained-frame budget and maximum 100 jobs. Structured CV failures become failed jobs with no successful result/export. In-memory results disappear after restart.
- Added real JSON/CSV export and diagnostics routes without changing existing polling/result/frame/manifest routes. CSV labels point type, frame index, coordinate frame and time basis.
- Health readiness changes from `bootstrap_only` to `local_prototype` and exports is true because real exports now exist. Frontend health parser accepts both readiness values. This is metadata compatibility, not scientific validation.
- UI retains Member 4 layout, adds real multipart submission, polling, matching diagnostics, observed/predicted overlays and downloads. Replacement/clear invalidates completed results; failed jobs show no stale tracks. Static contract fixtures remain visibly separated from real job results.
- Vite `/api` proxy targets `http://127.0.0.1:8001`; browser uses relative API paths. CORS permits only local 5174 origins (127.0.0.1 and localhost). No additional environment file is required.

## Python and frontend installation

Fresh `.venv`, Python 3.12.14, created using:

```powershell
& 'C:\Users\subha\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m venv E:\Fusion-latest-dev\.venv
```

Installed dependencies from `backend/requirements.lock.txt` plus setuptools, built a non-editable root wheel with `python -m pip wheel . --no-deps --no-build-isolation --wheel-dir .cache/wheel_02`, then installed that wheel with `python -m pip install --force-reinstall --no-deps .cache/wheel_02/orbittrace-0.1.0-py3-none-any.whl`. Final wheel SHA-256: `5963c83fb75c1bd1d78fd8077f23700a2e056d1a4051c7e5f09a41a404ee5eaf`.

Clean `python -I` imports of app/orbittrace/astrotrace/CV and FastAPI OpenAPI discovery passed; 59 installed Python source modules match source SHA-256. `python -m pip check`: no broken requirements. Selected installed versions: FastAPI 0.143.0, OpenCV-headless 4.14.0.94, NumPy 2.5.3, SciPy 1.18.1, Pydantic 2.14.0. Trained CV-T15 weights and environment remain in the original workspace.

Frontend: Node 24.19.0 / npm 11.17.0; `npm ci` installed 78 packages, audited 79, zero reported vulnerabilities. Lockfile and dependencies unchanged locally. npm emitted an esbuild install-script policy warning; esbuild executed successfully in tests/build. Build script runs `tsc --noEmit && vite build`.

## Actual verification commands and results

From `E:\Fusion-latest-dev`:

```powershell
$env:CV_T06_REAL_SOURCE = 'E:\Fusion\data\raw\SpotGEOv2'
$env:CV_T06_TRACKING_SNAPSHOT = 'E:\Fusion\artifacts\reports\cv_readiness\final\tracking_snapshot'
$env:CV_TRACK_SOURCE = 'E:\Fusion\data\raw\SpotGEOv2'
.\.venv\Scripts\python.exe -m pytest -q -rs
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -I -c "import app, orbittrace, astrotrace; from orbittrace.cv_tracking import analyze_telescope_sequence; from app.main import app as api; print(len(api.openapi()['paths']))"
.\.venv\Scripts\python.exe scripts/verify_integration_http.py --url http://127.0.0.1:8001 --esa E:\Fusion\data\raw\SpotGEOv2 --output artifacts/reports/latest_development/http_01
.\.venv\Scripts\python.exe .cache/final_audit.py
```

From `E:\Fusion-latest-dev\frontend`:

```powershell
node tests/run-data-tests.mjs
npm run build
node tests/verify-live-results.mjs ../artifacts/reports/latest_development/http_01
```

- Final full Python suite: **428 passed, 0 failed, 0 skipped**, 3 deprecation warnings, 67.56 s. Includes real ESA tests, detection, registration, robustness, leakage, association, trajectory, evaluation, upload bounds, manifests, schema serialization and CV-TRACK-01 behavior.
- Targeted API + new integration tests: 12 passed. Contract/pipeline regression after legacy-expectation fixes: 32 passed.
- Frontend: **94 passed, 0 failed, 0 skipped**. TypeScript and production build passed (83 modules). JavaScript 970.41 kB minified / 278.76 kB gzip; Vite emits a >500 kB chunk warning.
- Frontend strict parser accepted four real TCP results: demo, counts-change, empty-targets, ESA84.
- Real HTTP smoke suite: eight job cases plus three invalid-input checks; exit 0. Health/docs/OpenAPI, multipart submission, job polling, schema parsing, diagnostics, exact native decoded frame retrieval, JSON/CSV exports and CORS were exercised.
- Supplemental actual HTTP: eight successful manifest retrievals with five frames each, four 404 unknown/out-of-bounds checks, and website / proxied health / proxied job-result all 200.
- Browser: actual synthetic demo job, five-object upload, queued/loading states, frame 5 inspection, stable five track IDs, selection, 22 observed points and 10 explicitly predicted points. Browser SVG boxes exactly match backend frame-4 raw bounding boxes, including half-pixel rendering convention. Screenshot saved as `browser_final.png`; geometry comparison saved in final_audit.json.
- Browser empty-target upload succeeded with zero detections/tracks/predictions and visible empty-state copy. Daylight-like upload showed actual `unsupported_observation`, no completed overlays or exports. Positive five-object example restored. No browser error/warning log entries during final positive example; expected invalid jobs return unsuccessful result status rather than fabricated scientific output.

| Actual input | Observed detections per frame | Tracks / fits / outcome |
|---|---|---|
| Synthetic demo, one object | 1,1,1,1,1 | 1 confirmed track, 1 fit |
| Native five-object changing counts | 5,3,4,5,5 | 22 detections, 5 confirmed tracks, 5 fits |
| Supported empty targets | 0,0,0,0,0 | successful empty result, 0 tracks/fits |
| Real ESA train/84 | 7,7,6,8,6 | 34 detections, 31 track records, **0 confirmed / 0 fits** |
| Real ESA train/438 | registration failed at frames 3,4 | failed job, no successful result |
| Rotated synthetic star field | registration failure at frame 1 | `registration_failed` |
| Daylight-like | suitability rejected | `unsupported_observation` |
| Noise-only | insufficient observation evidence | `uncertain_observation` |

Invalid type and wrong count return HTTP 422; >10 MiB file returns 413. Failed-analysis result routes return 409. Native uint16 ESA frames retrieved from the backend match the uploaded pixels; metrics stay null where not evaluated.

## Errors found and corrected

Initial API targeted run: 11 passed / 1 failed because inherited health assertions still expected exports false. Initial full run: 426 passed / 2 failed because health and missing-T13 stub assertions were obsolete after actual integration. The tests now check implemented readiness and genuine suitability/registration errors. The registration test uses a supported five-frame star field with a rotated frame; it does not accept arbitrary exceptions. Focused regressions and final full suite passed.

Initial frontend run: 92 passed / 2 failed due to changed Local Image Preview heading and synthetic/local explanatory copy. Restored the existing UI wording and distinct demo guidance while retaining uploads; tests were unchanged and all 94 passed.

An import verification attempted a `.path` attribute on the newer FastAPI included-router object; imports had succeeded. Corrected verification uses public OpenAPI paths (nine route patterns). Supplemental browser geometry verification initially assumed zero-origin viewBox; actual inspected viewer deliberately uses -.5 pixel origin, matching bounding-box edge rendering. Corrected the audit assertion; no product change needed.

## Running application / exact restart commands

Both new servers remain running. Do not start another copy on the same ports while they are active. After stopping only these new services, open separate PowerShell terminals:

Backend:

```powershell
Set-Location E:\Fusion-latest-dev
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Frontend:

```powershell
Set-Location E:\Fusion-latest-dev\frontend
npm run dev -- --port 5174 --strictPort
```

- Website: http://127.0.0.1:5174/#/workbench
- API documentation: http://127.0.0.1:8001/docs
- Health: http://127.0.0.1:8001/api/health
- Logs: `.cache/backend.stdout.log`, `.cache/backend.stderr.log`, `.cache/frontend.stdout.log`, `.cache/frontend.stderr.log`.
- Backend exposes GET health; POST analyze/demo; POST analyze; GET job state/result/frames/manifest/diagnostics/exports.
- Existing `.venv` uses a non-editable installed wheel. After future backend source changes, rebuild/reinstall the root wheel and restart; frontend source reloads through Vite.
- Reproduce the five-object UI example by selecting `artifacts/reports/latest_development/http_01/counts-change/1.png` through `5.png`, confirm order, Analyze, inspect final frame. These files are local generated test evidence, not publication content.

## Remaining issues / next dependency

Synthetic local operation is tested. ESA84 still lacks confirmed tracks; ESA438 still fails registration. These historical limitations are not fixed. Short tracks represent candidate image-plane motion only; debris identity, physical speed, orbit, altitude and collision probability are not established. Quality is heuristic; synthetic metrics do not certify real-data performance.

Inherited README / SETUP / STATUS still describe bootstrap readiness. Use this tested handoff for startup. New Three.js landing code is decorative and is not an orbit solution; its large bundle warning remains. Python warnings concern upstream Starlette/httpx and deprecated HTTP 422 alias; tests pass. This prototype stores jobs only in process memory.

Member 1 can import the installed CV entry in this workspace and consume AnalysisResult now. Other checkouts cannot import unpublished source simply by fetching development or Subham; this task did not publish. Integration owner must review the exact patch/inventory and approve a separate isolated publication preparation on **Subham only**, including root packaging and API/UI compatibility. Never commit this detached worktree or push to main/development. Existing Member 1 / Member 4 work and original experiments remain intact.

Evidence: `.cache/full_tests_02.log`, `.cache/frontend-tests_final.log`, `.cache/frontend-build_final.log`, `.cache/frontend-live-results.log`, `.cache/http_01.log`, `artifacts/reports/latest_development/http_01/receipt.json`, `final_audit.json`, `browser_geometry.json`, `browser_result.json`, `browser_empty.txt`, `browser_unsupported.txt`, `browser_final.png`.
