# T08 — Live tracking visualization integration

Owner: frontend/display, explicitly assigned by the user. Implemented and tested
in `E:\Fusion-t08-live`; publication pending approval. No staging, commit, push,
merge or rebase was performed.

## Base and isolation

`E:\Fusion-integration\frontend` is the functional base: it already supports
five-image multipart upload, job creation/polling, diagnostics, native demo-frame
retrieval, completed results, error presentation and exports. Its detached base
commit is `da28ab8b0aa4e7abaeec802aff1714a1b4bb8336`; the tested snapshot also includes
Member 1's existing uncommitted integration files. The base commit alone does
**not** reproduce this working integration.

`E:\Fusion\frontend` contains the earlier T08 saved-result viewer. Its appearance
and stable palette were adapted to the functional base's verified native-image
coordinate plane, rather than replacing upload/job state with that standalone
viewer. The two original frontends were not modified by this task.

An isolated detached worktree was created at `E:\Fusion-t08-live`, then populated
with Git-visible files from Member 1's working integration snapshot. Existing
dependencies were reused: Node 24.19.0/npm 11.17.0, React 19, TypeScript 5.9,
Vite 7.3.7, and Python 3.12.14 in `E:\Fusion-integration\.venv`. The test checkout's
`frontend\node_modules` is a junction to the integration checkout's existing
installation. No new package, dependency or lockfile change is required.

Primary publication checkout: `E:\Fusion`, branch `Subham`, verified HEAD
`b07fe9873a39cd8897374078a7729cb4a50d6737`. Only this handoff, the patch and its
allowlist are additionally copied there. The isolated detached worktree is a
test checkout, not a publication branch.

## Exact T08 delta

Created:

```text
frontend/src/components/workbench/T08Overlay.tsx
frontend/src/components/workbench/t08-overlay.css
frontend/src/viewer/trackColors.ts
frontend/tests/t08-overlay.test.ts
frontend/tests/verify-t08-http.mjs
docs/handoffs/T08_LIVE_INTEGRATION.md
docs/handoffs/T08_LIVE_INTEGRATION.patch
docs/handoffs/T08_LIVE_INTEGRATION_FILES.txt
```

Changed relative to Member 1's working snapshot:

```text
frontend/src/components/workbench/ScientificOverlay.tsx
frontend/src/components/workbench/LocalWorkbench.tsx
frontend/src/components/workbench/DemoWorkbench.tsx
frontend/src/viewer/uploadOverlay.ts
frontend/tests/run-data-tests.mjs
```

ScientificOverlay is an interface-preserving wrapper around T08Overlay. Both
workbenches pass the existing verified overlay model, current scale, selection,
toggles and native dimensions. Upload mapping additionally checks the declared
reference frame, sorts actual observations and excludes predictions at/before
the last observation. No browser-generated trajectory or backend algorithm is
introduced. Local inspection adds actual status, RMSE, warnings and a final-frame
forecast notice. The existing workflow, hooks, API clients, response validators,
transport types and OpticalViewer are retained.

The patch contains only the **10 frontend paths** above, not the other integration
snapshot changes. It was checked successfully with `git apply --check` against
`E:\Fusion-integration`. Baseline/target SHA-256 hashes are locally recorded in
`.cache\t08\patch-hashes.json`. New files have Git new-file headers. A preliminary
patch check failed because those headers were missing; the corrected patch
passes. The patch has not been applied to either original checkout.

A final byte comparison of the other **285 integration source paths** found no
unexpected differences between the isolated snapshot and Member 1's checkout.

## API and field mapping

The frontend uses its unchanged same-origin API client:

| Operation | Endpoint |
|---|---|
| Synthetic one-object job | `POST /api/analyze/demo` (bodyless) |
| Five native ordered images | `POST /api/analyze/upload` (`manifest` and `files`, multipart) |
| Status polling | `GET /api/jobs/{job_id}` |
| Genuine AnalysisResult 0.1.0 | `GET /api/jobs/{job_id}/result` |
| Sequence and T13 transforms | `GET /api/jobs/{job_id}/diagnostics` |
| Native cached frame | `GET /api/jobs/{job_id}/frames/{frame_index}` |
| Existing exports | `GET /api/jobs/{job_id}/exports/json` and `/csv` |

The upload view displays the original validated local image blobs paired to
its confirmed manifest/result. The demo view fetches actual job frames. HTTP
verification additionally fetched all five native frames for every successful
case; byte/dimension checks passed. No URL or arbitrary path was added to the
public upload contract.

| Result fields | Display |
|---|---|
| `detections[].detection_id`, `frame_index`, `bbox_raw_px` | Current-frame neon boxes, exclusive upper limits |
| `x_raw_px`, `y_raw_px` | Native current centroids and provenance checks |
| `tracks[].track_id`, observed `points[].detection_id` | Box ownership, persistent hashed color, selection |
| `points[].point_type`, `frame_index`, `x_reference_px`, `y_reference_px` | Observed-only filled dots/solid connections through the timeline frame |
| `trajectory.coordinate_frame`, `predictions[]` | Backend extrapolations only, dashed lines/hollow markers in contrasting colors |
| `status`, `observed_count`, `quality_score`, `warnings`, trajectory speed/unit/RMSE | Actual selected-track inspector |

Track history and forecasts are in `reference_frame_0` for uploads. Every history
point and prediction is transformed by **the currently displayed frame's** T13
`reference_to_raw`, then decoded/native geometry, then the common image-plane
fit/zoom/pan transform. Current detection boxes already use raw coordinates.
Identity demo results use `raw_pixels` with verified `not_required` registration.
The upload mapper retains the existing translation-only T13 inverse requirement;
it suppresses overlays with a visible warning for unusable/mismatched provenance
or transforms. General affine/projective registration is not implemented here.

OpticalViewer uses integer pixel centers and an SVG viewBox starting at `-.5`;
exclusive raster box edges are therefore `x0-.5` through `x1-.5`. Image and SVG
share the same transformed plane. Marker/font/stroke/glow sizes account for the
fit scale and zoom; off-image paths are clipped rather than displaced into view.

Forecasts appear only at/after a track's final actual observation, and only for
backend extrapolated points strictly after it. Missing observations have no
manufactured marker or current box. Solid lines connect actual observations
across gaps. Non-selected tracks have 0.3 opacity; selected geometry has full
opacity and stronger strokes. Candidate labels remain identity-unverified.

## Actual verification

Final Python suite: **438 passed, 0 skipped**, 60.03 seconds. One existing
Starlette/httpx TestClient deprecation warning remains. The first run was 433
passed/5 skipped; supplying existing ESA data and an untouched Member 3 snapshot
enabled the five external compatibility checks. No tracking source was edited.
Snapshot commit: `a015cc949955d0438c8a16789b23746c3206f3d1`.

```text
tracker.py SHA256 34911026f4f21b47006ad5cb0c2893e9ca2b746ec3a7f1f11a35839edd3a57b3
fit.py     SHA256 fa4f02be0bd005c38d429132621f8dd4626bf4a3d860da068cf23791728b1658
```

Final frontend suite: **77 passed, 0 failed, 0 skipped** (70 existing plus 7 new).
TypeScript/Vite build passed, 74 modules. `git diff --check -- frontend` passed.
One early brittle class-selector test failed; retaining the existing forecast
class fixed it. A React SSR title-child warning was fixed. The HTTP verifier's
initial CJS top-level-await build failed; its awaited exported promise fixes it.
Final frontend and verifier runs have no such failures/warnings.

Fresh HTTP checks passed through Vite's proxy, not fixtures alone:

| Case | Real outcome | Final-frame T08 geometry |
|---|---|---|
| Synthetic demo, 64×48 | 1 confirmed track, 1 fit | 1 box, 5 observed dots, 2 forecast dots |
| Synthetic counts-change, 320×240 | 22 detections; 5 confirmed tracks/fits | 5 boxes, 22 observed dots, 10 forecast dots |
| Empty targets, 320×240 | Successful empty result | 0 boxes/dots/forecasts |
| ESA train/84, 640×480 | 34 detections, 31 tracks, 0 confirmed/fitted | 6 boxes, 34 observed dots, **0 forecasts** |
| Daylight-like unsupported image | `unsupported_observation`, result HTTP 409 | No analysis geometry |
| Noise-only uncertain input | `uncertain_observation`, result HTTP 409 | No successful result |
| Registration-failure synthetic | `registration_failed`, frame 1, HTTP 409 | No analysis geometry |
| ESA train/438 | `registration_failed`, frames 3/4, HTTP 409 | No successful result |

Health/docs/OpenAPI, existing CORS, JSON/CSV exports and native frame retrieval
passed. Wrong file count/type returned 422; oversized upload returned 413.
The production parser accepted all four successful HTTP results. The new HTTP
verifier fetched their current result/diagnostics/images, rendered T08 at fit
scales 0.4/1/4/8, and checked current registered centroids against native detections
within **1e-6 px**. ESA data/ground truth is not consumed by frontend inference.

Actual in-app browser verification (fresh UI-created jobs):

```text
Demo            job-2022fbd55c474265bde980f1f8908d6a
Multi final     job-00938684050043a48bc9179b79c6e16f
ESA train/84    job-45c0a194b5444e3f94816bfc5a9ffa95
Empty           job-e0b57c69d1754e69a9e63acb24174006
```

All final-frame counts in the table appeared in the real workbench. Unsupported
and registration failures showed actual API errors and zero local geometry.
An empty wrapper `<g>` may still exist; it contains no box/path/point primitives.
Dropdown and SVG-box selection, independent toggles, frame navigation, keyboard
pan and actual pointer drag passed. At frame 4, the multi-object view had 17
observations and no forecasts. At zoom 1/1.5/8, the first native box stayed
`x=63.5, y=68.5, width=6, height=6`; SVG viewBox remained `-.5 -.5 320 240`.
Pan persisted across navigation; Fit restored the view. Desktop 1280×1000 and
mobile 390×844 were inspected; mobile effective width and document width were
both 375 px, with no horizontal overflow. Viewport override was reset. Browser
console had no captured warnings/errors at the end of these runs.

## Exact PowerShell reproduction

The services are currently running on new ports **8010** and **5180**. Existing
8000/5173/5175 servers were left untouched. Do not start a second copy on these
new ports while they are still occupied. The source checkout uses the reused
integration environment, not an installed published package.

Backend, in its own terminal:

```powershell
Set-Location E:\Fusion-t08-live
$env:PYTHONPATH='E:\Fusion-t08-live\backend;E:\Fusion-t08-live\src'
& E:\Fusion-integration\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Frontend, in another terminal:

```powershell
Set-Location E:\Fusion-t08-live\frontend
npm run dev -- --config ../.cache/t08/vite.config.mjs
```

The ignored local Vite override retains the original config and proxies `/api`
to 8010; it does not change shared config/dependencies/CORS. If reconstructing
the local config after removing caches:

```powershell
Set-Location E:\Fusion-t08-live
New-Item -ItemType Directory -Force .cache\t08 | Out-Null
@'
import base from '../../frontend/vite.config.ts';
export default { ...base, cacheDir: 'E:/Fusion-t08-live/.cache/t08/vite', server: { ...base.server, host: '127.0.0.1', port: 5180, strictPort: true, proxy: { '/api': 'http://127.0.0.1:8010' } } };
'@ | Set-Content -Encoding utf8 .cache\t08\vite.config.mjs
```

Frontend tests/build:

```powershell
Set-Location E:\Fusion-t08-live\frontend
node tests/run-data-tests.mjs
npm run build
```

Full Python suite including the real/snapshot-dependent compatibility cases:

```powershell
Set-Location E:\Fusion-t08-live
$env:PYTHONPATH='E:\Fusion-t08-live\backend;E:\Fusion-t08-live\src'
$env:CV_T06_REAL_SOURCE='E:\Fusion\data\raw\SpotGEOv2'
$env:CV_T06_TRACKING_SNAPSHOT='E:\Fusion-t08-live\.cache\t08\member3'
& E:\Fusion-integration\.venv\Scripts\python.exe -m pytest -q
```

The existing local snapshot can be regenerated without switching branches or
editing tracking using this read-only Git export:

```powershell
Set-Location E:\Fusion-t08-live
@'
from pathlib import Path
import subprocess
folder=Path('.cache/t08/member3')
folder.mkdir(parents=True,exist_ok=True)
ref='a015cc949955d0438c8a16789b23746c3206f3d1'
for name,path in [('tracker.py','backend/orbittrace/tracking/tracker.py'),('fit.py','backend/orbittrace/trajectory/fit.py')]:
    (folder/name).write_bytes(subprocess.check_output(['git','show',f'{ref}:{path}']))
'@ | & E:\Fusion-integration\.venv\Scripts\python.exe -
```

Fresh real HTTP reproduction (use a new output directory per run):

```powershell
Set-Location E:\Fusion-t08-live
$env:PYTHONPATH='E:\Fusion-t08-live\backend;E:\Fusion-t08-live\src'
$proofFolder='E:\Fusion-t08-live\.cache\t08\http-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
& E:\Fusion-integration\.venv\Scripts\python.exe scripts/verify_integration_http.py --url http://127.0.0.1:5180 --esa E:/Fusion/data/raw/SpotGEOv2 --output $proofFolder
Set-Location E:\Fusion-t08-live\frontend
node tests/verify-live-results.mjs $proofFolder
node tests/verify-t08-http.mjs $proofFolder http://127.0.0.1:5180
```

## Viewing outputs

Open `http://127.0.0.1:5180/#/workbench`. Run Synthetic Demo for the one-object
HTTP path, then Inspect final frame & forecasts. For uploads, choose the five
ordered native PNGs, Confirm order & view, Analyze local images, then move the
timeline to frame 5. Select a track, try the three toggles and zoom/pan/Fit.
The original analysis tables and JSON/CSV links remain beneath the viewer.

Use `.cache\t08\http\counts-change\1.png` through `5.png` for the reproducible
multi-object case. Use `E:\Fusion\data\raw\SpotGEOv2\train\84\1.png` through
`5.png` for ESA. `empty-targets`, `daylight-like` and `registration-failure`
subdirectories contain the generated HTTP test inputs. These images are ignored
local evidence, not publication files.

JSON evidence: `.cache\t08\http\receipt.json`, `t08-verification.json`, and each
successful case's `<case>_result.json` / `<case>_diagnostics.json` in that same
folder (for example `counts-change_result.json` and `esa-train-84_result.json`).
Browser screenshots:
`.cache\t08\live-multi.png`, `live-esa.png`, `live-mobile.png`, `live-empty.png`,
`live-unsupported.png`, `live-registration-failure.png`. Outputs are in the
isolated checkout. Jobs are in the existing in-memory backend store and disappear
on restart; saved evidence remains. Backend docs: `http://127.0.0.1:8010/docs`.

## Safe publication and team dependency

Member 1 must first review/publish the working integration prerequisite to
`Subham` under the user's approval; it includes currently uncommitted upload,
pipeline, API/client and contract refinements. This T08 patch applies to that
working frontend snapshot, **not** to the older standalone primary frontend.
Do not overwrite Member 1's original checkout or stage its broad snapshot as T08.

Read-only patch check, already passed:

```powershell
git -C E:\Fusion-integration apply --check E:/Fusion/docs/handoffs/T08_LIVE_INTEGRATION.patch
git -C E:\Fusion branch --show-current
git -C E:\Fusion diff --check
```

After explicit publication approval, apply only the T08 patch to the reviewed
functional base on Subham; rerun build/tests and a fresh HTTP/browser path there.
Use `T08_LIVE_INTEGRATION_FILES.txt` as the exact T08 staging allowlist after
reviewing every listed path. It is not a standalone integration staging list.
No `git add .`: exclude raw datasets, screenshots/JSON evidence, models,
environments, caches, root dependency files and unfinished CV-T15 changes.
Recheck baseline drift with `git apply --check` immediately before applying.

Member 3 needs no schema or tracker change for this viewer. Keep observed
detection IDs and point types accurate; reference-frame coordinates and the
current-frame inverse are required for registered display. Supply actual backend
trajectory predictions to display forecasts. Short/unconfirmed ESA tracks have
none; the UI will not invent them. Missed detections retain actual history but
have no current box or fabricated observation.

Live integration is verified in the isolated working copy. Remaining dependency
is team review/publication of the functional integration base plus this narrow
T08 delta onto Subham. No change to models/training, scientific calibration,
tracking gates, registration failure policy or API schema is requested. Next:
Member 1 reviews that combined publication and repeats the real upload/browser
check on the approved Subham checkout.
