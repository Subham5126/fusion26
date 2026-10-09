# Windows integration — T07 lead continuation

Base: `da28ab8b0aa4e7abaeec802aff1714a1b4bb8336` (`origin/development`).
Implementation location: detached `E:\Fusion-integration`; primary `E:\Fusion`
remains on Subham at `922fb937a109ec3231d7ec462bb88f3fdbdd62b4`.
State: implemented and locally verified; scientific readiness PARTIAL. No commits or pushes authorized for this task.

## Dependency map recorded before implementation

| Member / existing component | Consumer / gap |
|---|---|
| 1: backend/app API, JobManager, orbittrace.pipeline | Connect registration and suitability; bound request reads/decode; preserve structured failures |
| 2: src/astrotrace loader, optimized CV, registration, suitability | Package with app/orbittrace; retain frozen CV-T04 defaults and native pixels |
| 3: orbittrace.tracking.tracker, trajectory.fit, evaluation | Reuse actual functions; pass every frame; registered coordinates; observed/predicted separation |
| 4: React local sequence ordering, demo jobs, OpticalViewer, SVG overlays | Enable uploads; reuse polling and viewer; add source-specific metadata and transforms |

Existing backend packaging discovers only app/orbittrace, excluding astrotrace.
No root pyproject exists. Historical README/STATUS and some handoffs describe the
bootstrap rather than merged implementation. docs/contracts is absent; the actual
contract is docs/CONTRACTS.md plus backend/app/schemas and frontend/src/types.
Public analysis remains schema 0.1.0. Supplemental per-job diagnostics can carry
input geometry and matrices without changing the analysis contract.

Policy: public telescope uploads require exactly five native grayscale PNG or
JPEG frames. Unsupported/uncertain suitability blocks inference. Any registration
failure blocks the whole registered sequence. Trusted synthetic static-camera
demo may skip registration and low-feature suitability; no public upload may
claim that profile. No YOLO runtime/checkpoint adoption in this integration.

Execution evidence follows. No publication was performed.


## Actual environment, packaging and architecture

Windows PowerShell; Python 3.12.14, Node 24.19.0, npm 11.17.0. Own integration
venv and npm dependencies use backend/requirements.lock.txt and existing npm
lock. No optional model dependency, lock change or global environment change.
Root non-editable wheel built and installed with no-deps: SHA256
`2e3f6ce2e62186cc98c1301c60bade08822695d4d925f371a62b2b3438d17243`.
`python -I` imports app.main, orbittrace.pipeline and astrotrace registration
from .venv/Lib/site-packages, then performs demo POST 202, succeeded poll and
result 200 with five detections. pip check reports no broken requirements.

Flow: native five frames -> suitability -> existing optimized detector ->
translation registration -> additive reference coordinates -> existing Tracker
on all frames -> existing attach_trajectories -> schema 0.1.0 result.
Full raw-to-reference and inverse matrices are in per-job diagnostics. Raw
boxes/points are preserved. No label loader or truth input enters inference.
The detector uses reviewed frozen settings (threshold sigma 4.5); only explicit
numeric overrides change them. API telescope config leaves overrides unset;
the authored static demo explicitly uses sigma 3.0.

## Verified HTTP routes

| Route | Actual check |
|---|---|
| GET /api/health | 200, local_prototype, upload/analysis/tracking/export capabilities |
| POST /api/analyze/demo | 202, genuine synthetic computation, successful polling/result |
| POST /api/analyze/upload | Multipart manifest + five repeated files; 202 or bounded structured 422/413 |
| GET /api/jobs/{job_id} | running -> succeeded/failed, safe scientific error codes |
| GET /api/jobs/{job_id}/result | 200 with explicit nulls on success, 409 after failure |
| GET /api/jobs/{job_id}/frames/{frame_index} | 200, decoded native values equal submitted inputs |
| GET /api/jobs/{job_id}/diagnostics | 200 after completion/failure, real matrices/reasons |
| GET /api/jobs/{job_id}/exports/{json,csv} | 200 on success, observations and extrapolations separated |
| GET /docs and /openapi.json | 200, actual route descriptions |
| OPTIONS /api/analyze/upload | 200, exact local frontend origin accepted |

## Actual execution results

Final full Python suite: 404 passed in 60.39 seconds, including native 16-bit
CLI preservation and explicit null serialization. Frontend: 70 passed, zero failed/skipped;
TypeScript + Vite production build passed. Seven CLI/pipeline regressions passed
before adding explicit 16-bit preservation coverage. Import checker: 31 package
modules and all CPU dependencies import. The wheel isolated API check passed.
One upstream Starlette TestClient/httpx deprecation warning remains.

Actual TCP HTTP verifier evidence is under ignored
`artifacts/reports/integration/http_01/receipt.json`, with result/diagnostic JSON
and five-file example folders. Existing data/reports were not overwritten.

| Input | Outcome | Detections per frame | Tracks / confirmed / fits |
|---|---|---|---|
| Synthetic API demo | succeeded | 1,1,1,1,1 | 1 / 1 / 1 |
| Changing counts | succeeded, registered | 5,3,4,5,5 | 5 / 5 / 5 |
| Supported empty targets | succeeded, registered | 0,0,0,0,0 | 0 / 0 / 0 |
| Daylight-like | failed unsupported_observation | no result | none claimed |
| Noise only | failed uncertain_observation | no result | none claimed |
| Supported fixture with failed registration | failed registration_failed | no result | none claimed |
| ESA train/84, 640x480 | succeeded, registered | 7,7,6,8,6 | 31 / 0 / 0 |
| ESA train/438 | failed registration_failed, frames 3 and 4 | no result | none claimed |

Invalid type and wrong count: 422; oversized file: 413. ASGI tests also enforce
streaming request limits without Content-Length and reject decoded >4MP headers
before allocation, RGB, corrupt bytes and synthetic upload bypass.

Four actual HTTP result JSONs pass the frontend's strict AnalysisResult parser
via tests/verify-live-results.mjs, including the valid empty result. Browser
flow used local file chooser, confirmed five-file order, real POST, visible
submitting/queued state, completed results, frame navigation, actual boxes,
track selection and dashed predictions. Changing-count frame five rendered five
boxes and five dashed forecast paths (ten predicted points). ESA train/84
rendered 34 candidates, 31 tracks and zero predictions at native 640x480.
Daylight-like input visibly failed with unsupported_observation and no result
counts/exports. Browser console error/warn inspection returned none at that
checkpoint. Screenshots are in the ignored integration report directory.

## Known failures and limits

- Documentation checker: 17 inherited links to ignored historic reports missing
  in the fresh worktree. New documentation links resolve; old report artifacts
  were neither invented nor copied wholesale. This is a recorded failed check.
- `npm test` is not a declared script and failed; use the actual
  `node tests/run-data-tests.mjs` command (70 passed). The corrected command and
  production build were rerun after final frontend edits.
- First browser tab failed in browser-session binding; a fresh tab and supported
  browser handle completed actual uploads. A selector initially used the wrong
  confirmation label; the visible label was inspected and corrected. Editing
  during the first ESA browser run refreshed React state; a second ESA run was
  executed and verified after edits stopped.
- ESA train/84 association is fragmented (no track with three observations).
  Registered candidate processing works, but real-data trajectory quality needs
  calibration/evaluation. Gates were not widened just to obtain a fit.
- Registration is translation only; no failed-frame fallback, rotation/affine
  fitting or scientific calibration. Predictions describe image-plane motion;
  quality scores are heuristic. No orbit/debris identity/physical speed claim.
- Exactly five grayscale PNG/JPEG frames; EXIF orientation 1, common dimensions,
  native uint8/uint16 PNG or grayscale JPEG. UI timestamps remain unknown, so
  uploads use pixels/frame. Irregular trusted timestamp cadence is warned.
- One active CPU job; 20 jobs/256MiB native frames retained, then completed jobs
  evicted. Jobs disappear on restart. No auth, durable queue, production hosting,
  public evaluation route, reviewed trained YOLO model or dataset redistribution.
- Historical generic script templates do not constitute the current workflow.
  Trusted run_t07 CLI remains usable; use bounded HTTP for arbitrary uploads.

## Reproduction, next dependency and publication policy

See [SETUP](../SETUP.md) for exact install, test and service commands. Current backend
listens on 127.0.0.1:8000; frontend on 127.0.0.1:5173. OpenAPI /docs; workbench
/#/workbench. Use a fresh output folder when rerunning the HTTP verifier.
Result provenance and diagnostics record actual input/config SHA256 hashes;
full hashes are in the receipt-linked per-case JSON files, not invented here.

Inspected Subham and origin/Subham: 922fb937a109ec3231d7ec462bb88f3fdbdd62b4.
origin/development and detached integration HEAD:
da28ab8b0aa4e7abaeec802aff1714a1b4bb8336. Inspected origin/main:
fa593cf5052f96d311d049f2b84949f588a99407. Subham is an ancestor of development
(0 local-only, 16 development-only commits). No branch history was altered.

Safe proposed publication, requiring explicit approval BEFORE execution:
refetch and repeat ancestry/agent/index checks; preserve/check primary dirty
files; approve a fast-forward-only advancement of Subham to the inspected merged
base; check/apply only the reviewed integration patch; stage only the reviewed
file list; review cached diff/tests; commit on Subham; normal push and remote SHA
verification. This proposal is NOT executed and does not authorize a merge,
rebase, reset, detached commit or force-push. Stop if remotes diverge, dirty paths
collide or CV-T15 uses the index. The development change list currently does not
include original PROBLEM_STATEMENT or CV-T15 paths. Fresh checks are still needed
at publication time. A review patch is saved under ignored integration artifacts.

Next dependency: lead approves publication method/file set; Member 3 evaluates
ESA associations with separate truth and reviewed registration/gate settings.
Member 1 uses root installation, bounded upload API and documented failure policy.
Judging verdict PARTIAL: reproducible synthetic candidate/track/trajectory demo
works; real-data tracking quality, official rules and submission remain open.

## Exact changed source/documentation/test files

Paths below are relative to E:/Fusion-integration. The machine-readable list is
INTEGRATION-WINDOWS-files.txt. No data, checkpoints, environment or generated
report is included. This is a review list, not permission to commit.

| Path | Reason |
|---|---|
| `README.md` | Current architecture, protocol decisions, execution evidence, reproduction and reviewed file set |
| `backend/app/api/analyze.py` | Real five-frame API, local CORS, structured errors and truthful health capabilities |
| `backend/app/api/health.py` | Real five-frame API, local CORS, structured errors and truthful health capabilities |
| `backend/app/api/jobs.py` | Supplemental diagnostics and observed/predicted JSON/CSV exports |
| `backend/app/core/upload.py` | Stream byte bounds, signature/dimension/orientation checks before native decode |
| `backend/app/main.py` | Real five-frame API, local CORS, structured errors and truthful health capabilities |
| `backend/app/schemas/health.py` | Real five-frame API, local CORS, structured errors and truthful health capabilities |
| `backend/app/services/job_manager.py` | Atomic one-job reservation, bounded retention, executor and safe failures |
| `backend/orbittrace/pipeline.py` | Connect existing suitability, frozen CV, registration, tracker and fits; explicit failure policy |
| `docs/CONTRACTS.md` | Current architecture, protocol decisions, execution evidence, reproduction and reviewed file set |
| `docs/DECISIONS.md` | Current architecture, protocol decisions, execution evidence, reproduction and reviewed file set |
| `docs/SETUP.md` | Current architecture, protocol decisions, execution evidence, reproduction and reviewed file set |
| `docs/STATUS.md` | Current architecture, protocol decisions, execution evidence, reproduction and reviewed file set |
| `docs/handoffs/INTEGRATION-WINDOWS-files.txt` | Current architecture, protocol decisions, execution evidence, reproduction and reviewed file set |
| `docs/handoffs/INTEGRATION-WINDOWS.md` | Current architecture, protocol decisions, execution evidence, reproduction and reviewed file set |
| `frontend/src/api/client.ts` | Actual multipart transport, diagnostics and coordinated health enum validation |
| `frontend/src/api/responseValidation.ts` | Actual multipart transport, diagnostics and coordinated health enum validation |
| `frontend/src/api/transport.ts` | Actual multipart transport, diagnostics and coordinated health enum validation |
| `frontend/src/components/HealthPanel.tsx` | Styled real upload/viewer/results workflow, truthful health text and labeled fixture backup |
| `frontend/src/components/workbench/AnalysisPanel.tsx` | Styled real upload/viewer/results workflow, truthful health text and labeled fixture backup |
| `frontend/src/components/workbench/BackendConnection.tsx` | Styled real upload/viewer/results workflow, truthful health text and labeled fixture backup |
| `frontend/src/components/workbench/LocalWorkbench.tsx` | Styled real upload/viewer/results workflow, truthful health text and labeled fixture backup |
| `frontend/src/hooks/useAnalysisJob.ts` | Reuse polling for upload jobs, validate identities, abort/reset stale results |
| `frontend/src/pages/WorkbenchPage.tsx` | Styled real upload/viewer/results workflow, truthful health text and labeled fixture backup |
| `frontend/src/state/analysis.ts` | Reuse polling for upload jobs, validate identities, abort/reset stale results |
| `frontend/src/state/analysisJob.ts` | Reuse polling for upload jobs, validate identities, abort/reset stale results |
| `frontend/src/types/contracts.ts` | Actual multipart transport, diagnostics and coordinated health enum validation |
| `frontend/src/viewer/uploadOverlay.ts` | Ordered manifest and verified inverse registration for native-coordinate overlays |
| `frontend/tests/analysis-jobs.test.ts` | Meaningful guards, actual upload/geometry regressions and frontend parsing of TCP results |
| `frontend/tests/live-visualization.test.ts` | Meaningful guards, actual upload/geometry regressions and frontend parsing of TCP results |
| `frontend/tests/run-data-tests.mjs` | Meaningful guards, actual upload/geometry regressions and frontend parsing of TCP results |
| `frontend/tests/upload-integration.test.ts` | Meaningful guards, actual upload/geometry regressions and frontend parsing of TCP results |
| `frontend/tests/verify-live-results.mjs` | Meaningful guards, actual upload/geometry regressions and frontend parsing of TCP results |
| `pyproject.toml` | Root multi-package discovery; existing runtime/development dependency declarations |
| `scripts/run_t07.py` | Preserve native grayscale bit depth and JSON null fields in the trusted local CLI |
| `scripts/verify_integration_http.py` | Repeatable TCP evidence for eight scientific cases, upload bounds, exports and native frame equality |
| `tests/api/test_t09_api.py` | Meaningful guards, actual upload/geometry regressions and frontend parsing of TCP results |
| `tests/contracts/test_bootstrap.py` | Meaningful guards, actual upload/geometry regressions and frontend parsing of TCP results |
| `tests/pipeline/test_t07_pipeline.py` | Meaningful guards, actual upload/geometry regressions and frontend parsing of TCP results |
| `tests/pipeline/test_windows_integration.py` | Meaningful guards, actual upload/geometry regressions and frontend parsing of TCP results |


## Final preservation and review audit

All 23 approved CV files and all 41 protected files from the primary checkout's
publication preservation snapshot still match their SHA256 hashes. Primary
Git status is unchanged: modified docs/PROBLEM_STATEMENT.md; untracked
Ultralytics/, docs/handoffs/CV-T15.md, experiments/, tests/yolo/. Original branch
is Subham at 922fb937. Integration HEAD is detached at da28ab8; 40 review paths
are modified/new; index is empty. git diff --check passed. The complete patch
including new files passed git apply --reverse --check against the current tree.
No staging, commit, push, reset, merge, rebase or branch creation was performed.
A final SHA256 audit and review patch are in ignored integration artifacts;
review_02.patch supersedes the earlier draft review_01.patch.

Final browser result: job-aef13d071686439ab23572d1e3170687, frame 5/5,
22 detections, five tracks, ten predicted points; five boxes and five dashed
forecast paths. Both services remain running on loopback, owning PIDs 13848
(backend) and 3088 (frontend). browser_final.jpg shows this genuine result.
