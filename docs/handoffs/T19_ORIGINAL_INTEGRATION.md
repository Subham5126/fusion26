# T19 — consolidation into ORIGINAL E:\Fusion only

Verdict: **PASS for local T19 integration acceptance**, ready for human review.
State: implemented/tested locally, ready_for_review. Base and unchanged HEAD:
b07fe9873a39cd8897374078a7729cb4a50d6737; original Subham branch/.git preserved.
No clone/worktree/branch creation, merge/rebase/stage/commit/push or deletion.

## Exact source selection

| Component | Original source and destination decision |
|---|---|
| Latest frontend design/GSAP/Three.js/native viewer | Latest merged development61e3810/8c7b61b, already verified in existing OrbitTrace-Final; imported required files only into Fusion/frontend |
| Live T08 neon overlay | Fusion-t08-live implementation, narrow integration already verified in existing OrbitTrace-Final; latest manifest flow retained |
| Upload/API/jobs/exports/diagnostics/CV-TRACK-01 | Fusion-latest-dev unpublished code via verified existing OrbitTrace-Final; root editable packaging added |
| Member3 tracker/fitter/evaluator/ablations | Latest merged development source present in existing OrbitTrace-Final; missing original modules imported without edits |
| CV-T03/CV-T04/T13/T14/FITS | Existing original Fusion implementations already normalized-identical to verified source; retained unchanged |
| YOLO | Existing Fusion code/checkpoints/runtime, preserved unchanged; fresh inference smoke |
| Data/configs/result schema | Original datasets retained; no duplicate data; AnalysisResult0.1.0 source unchanged |

128 meaningful file changes imported, comparing normalized line endings to avoid
unrelated churn. Every imported path/source SHA and original SHA recorded in
.cache/original-consolidation-20261010/manifest.json. Local routing conflicts:
App.tsx, ReadinessPage.tsx and WorkbenchPage.tsx previously opened a standalone
fixture viewer; original bytes preserved, latest routing retains navigation and
adds actual backend-connected analysis plus latest design. Legacy standalone
components/tests remain in the original tree; they are not the live default.
PROBLEM_STATEMENT.md and local Ultralytics/settings.json not overwritten.

Ports localized to8000/5173, CORS includes5173. HTTP harness derives origin from
its tested URL. Exact changed/created paths: T19_ORIGINAL_INTEGRATION_FILES.txt.

## Actual callable and data flow

```python
from orbittrace.cv_tracking import analyze_telescope_sequence
# (frames, *, sequence, frame_indices=None, timestamps=None, config=None,
#  method='optimized', detector_config=None, registration_config=None,
#  diagnostics=None) -> app.schemas.result.AnalysisResult
```
Five native ordered grayscale frames -> suitability -> raw optimized detection ->
T13 registration -> add_reference_coordinates -> reference-frame gated tracking ->
rough trajectory fitting -> finite AnalysisResult0.1.0. Unsupported/uncertain and
registration failure reject the whole job; healthy zero candidates succeeds empty.
Unknown upload timestamps remain null. Constructor/PipelineConfig gate20px; older
T13 prose15px was a documented error corrected byT14, no gate algorithm change.
Predictions never count as observations; raw/reference transforms retained.

API: POST /api/analyze/upload; GET /api/jobs/{id}, /result, /manifest,
/diagnostics, /frames/{frame_index}, /exports/{format}; demos also work. Actual
multipart parsing, bounded uploads, worker execution/polling and real exports tested.
Root packages app/orbittrace/astrotrace resolve under E:\Fusion in isolated mode.

## Commands actually run and outcomes

SETUP.md lists exact reproduction commands. Full Python500passed,0failed,0skipped
in63.84s,5warnings; frontend101passed and productionbuildpassed. Five warnings:
The retained original standalone overlay suite also passed19tests (120total across
the two frontend suites); its components remain preserved but are not the live route.
Starlette/httpx deprecation1,HTTP422 aliases3,expected invalidBLANK FITS1. Existing
large frontend chunk warning remains. First npm ci failed EPERM due old esbuild
lock. On the approved continuation both old PIDs and all three ports were already
absent/free, so no process was terminated. npm ci passed:78packages,79audited,
0vulnerabilities; nonblocking esbuild install-policy warning. Actual tests/build
and Vite used the working original binary. Isolated HTTP harness initially failed
its sibling generator import; exact-path loading fixed it, then nine jobs passed.
First Python run497passed/3skipped: two old snapshot checks lacked the explicit
snapshot and one ablation report absent. Byte-identical original Member3 snapshot
and freshly generated original T15 report enabled all500 tests in the final run.

Fresh CV-TRACK-01:13scenarios,9successes/4expectedfailures. Fresh direct backend
HTTP8jobs; fresh frontend-proxy HTTP9jobs adds one-object multipart upload and
checks CORS/manifests/timestamps. Successful counts: oneobject1x5, multi5/3/4/5/5
with5confirmed fits, empty0x5, ESA84=7/7/6/8/6 with31track records and0fits.
Unsupported/uncertain/rotation/ESA438 fail with actual codes. Invalid inputs422,
oversized413,failed result409,exports200; actual native frame pixels preserved.
Five real serialized results and T08 actual result/manifest/image mappings pass.

Fresh browser on original5173: actual uploads/demo, five final multi boxes,
22observations/10forecasts, selected track, toggles, frame4 hides future,
ESA640x480 detects without forecast, empty/unsupported/registration errors,
zoom/pan/frame navigation, responsive no overflow. Console errors/warnings none.
Evidence: artifacts/reports/original_consolidation/{http_live,cv_track_01,browser,yolo_smoke}.

Verified process/port checkpoint: backend launcher10948 at
E:\Fusion\.venv\Scripts\python.exe; listener18108 is that environment's Python
child, serving127.0.0.1:8000. FrontendNodePID30892 serves127.0.0.1:5173 from
E:\Fusion\frontend; esbuildchild29536 executable resides in that frontend's
node_modules. Port5175 has no listener. Previous approved15912/28032 PIDs were
already absent; no current process was terminated. Runtime imports and startup
working directories verify this source, not another checkout. PIDs are transient.

YOLO: originalbest.pt SHAa019175e841b8842cd84cf395b7eda9585df4f9e306c60e42c27d15a3ff97f03;
fresh original-code/runtime inference5images/3detections,annotations_read=false.
Not sequence/tracking validation, new training or production route selection.

## Backup/recovery and blockers

243 original source files, including untracked work, stored as verified objects
inside .cache/original-consolidation-20261010; HEAD/status and file SHA recorded.
Inspect one exact original byte snapshot:
```powershell
& E:\Fusion\.venv\Scripts\python.exe E:\Fusion\.cache\original-consolidation-20261010\recover_file.py --file frontend/src/App.tsx
# Only if intentionally reverting this one exact file, add --apply.
```
No Git restore/reset/clean is used. New integrated files are listed explicitly;
recovery does not silently delete them. Existing external Recovery retains older
workspaces/history; no data/model/report directories were copied wholesale.

No unresolved source conflict. Scientific limitations remain: in-memory jobs,
translation registration, missing timestamps, false persistent artifact tracks,
ESA84no fits/ESA438failure; optional YOLO selector/FITS HTTP unsupported. No orbit
or debris certification. Next dependency: review exact allowlist, then explicit
Subham publication instruction; cleanup remains separate review-only approval.

## Audit-time source Git states

| Workspace | Branch/head | Modified/untracked source |
|---|---|---|
| E:\Fusion | Subham / b07fe987 | 3/33 |
| E:\Fusion-integration | detached / da28ab8b | 31/15 |
| E:\Fusion-latest-dev | detached / 61e38106 | 23/15 |
| E:\Fusion-t08-live | detached / da28ab8b | 33/23 |
| E:\Fusion-cv-track-publication | Subham / 922fb937 | 0/13 |
| E:\Fusion-member2-post-round2 | detached / 61e38106 | 0/6 |
| E:\Fusion-member2-publication-check | detached / 922fb937 | 0/6 |
| E:\OrbitTrace-Final | Subham / 8c7b61b3 | 29/62 |
