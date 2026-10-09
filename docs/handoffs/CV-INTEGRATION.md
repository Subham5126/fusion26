# CV integration readiness after T13/T14

Task ID: CV-INTEGRATION, user-assigned CV review continuing Data/CV T13/T14.
Owner: Member 2 / Computer Vision Engineer. Date: 9 October 2026, Asia/Calcutta.
Base/required branch: **Subham**, `c802622800ed14739bd841ee840ec16cf905e4cd`.
State: **ready_for_review** for CV publication; backend adoption remains blocked
on Integration work. No algorithms, schema, tracker, pipeline or dependencies in
the repository were changed. No staging, commit, push, merge, rebase or checkout.

## Deliverables and ownership

Created exactly four publication files:

- This handoff: `docs/handoffs/CV-INTEGRATION.md`.
- [Member 1 integration checklist](CV-INTEGRATION-MEMBER1.md).
- [Separate Member 3 message draft](CV-INTEGRATION-MEMBER3.md).
- [Exact pending-file staging allowlist](CV-INTEGRATION-files.txt).

Changed four CV-owned files to fix a demonstrated report-viewing blocker and a
documentation inconsistency:
`scripts/spotgeo_robustness.py` now links Stars after to the renderer's actual
`star_overlay.png` instead of absent `star_overlay_after.png`;
`tests/detection/test_robustness.py` adds a real accepted/rejected-case report
generation test checking every local href/src resolves inside its output folder.
`docs/handoffs/CV-T13.md` and `src/astrotrace/preprocessing/REGISTRATION.md`
correct the stale15px claim to the actual20px gate. The handoff notes that no
gate tuning occurred.
No detection/registration/association algorithm changed. Other existing T03
through T14 implementations and historical handoffs were inspected, not edited.
The new checklist supersedes stale readiness wording without rewriting historical
results. STATUS/BACKLOG/TEAM, AGENTS, backend packaging/schema/config/pipeline,
tracking/trajectory, frontend, lockfiles and unrelated edits remain untouched.
No external messages were sent. No additional detector or registration algorithm
was invented. All new environments, wheel builds, probes and evidence live in
ignored `.cache/cv_readiness/` and `artifacts/reports/cv_readiness/`.

Read AGENTS, STATUS, PROJECT_BRIEF, CONTRACTS, TEAM, BACKLOG, Data-CV role,
ALGORITHMS/DATASETS, CV_TO_TRACKING, T13, T14 and T14-JUDGE, actual source,
schema/pipeline/API and Member3 Git source. STATUS/BACKLOG still describe bootstrap
readiness; these are Integration-owned and not silently updated by this audit.

## Repository and concurrent-work findings

Local Subham and read-only remote Subham both resolve to the base commit above.
T03/CV-T04/CV-T05/CV-T06 and the earlier CV-GIT source list (**46 files**) are
already tracked in that published commit; the old handoff's original "untracked"
observations are historical, not today's Git state. T13/T14 add18 untracked files
plus one modified preprocessing README, currently absent from remote Subham.
Member3 cannot receive these new modules through Git until publication is approved.

Member3 remote/local fetched ref is
`a015cc949955d0438c8a16789b23746c3206f3d1`; read-only ls-remote confirmed this
without fetch/merge/index changes. Its history includes the earlier CV publication.
Current Subham still has tracking/trajectory placeholder initializers. Diagnostic
runners export exact tracker/fit bytes from the Git ref into ignored report
snapshots; those are executable compatibility evidence, not replacement source.
Tracker SHA-256:
`34911026f4f21b47006ad5cb0c2893e9ca2b746ec3a7f1f11a35839edd3a57b3`.

Concurrent CV-T15 files under experiments/yolo, tests/yolo and CV-T15.md are
excluded from this publication. At inspection its handoff says ready_for_review,
five completed epochs and separated evaluation in an isolated runtime. No YOLO
source/runtime/checkpoint was modified or training rerun here. Its21 utility and
notebook tests happen to be collected in the current full suite; they are not
part of the CV-T13/T14 staging list. Source fingerprints were taken to detect
concurrent edits; a stable observation is not authorization for shared index work.
Do not stage while another agent is changing the approved files or using the index.

Excluded unrelated `docs/PROBLEM_STATEMENT.md` edit and untracked Ultralytics/
remain as found. The latter is an earlier CV-T15-generated settings artifact,
not CV source. No cleanup or attempt to bypass its earlier approval rejection
was performed in this review.

## Verified data flow and boundaries

Exact imports/signatures and a concise adoption checklist are in the Member1
handoff; runtime signatures were independently captured from a clean installed
wheel under Python `-I` in `.cache/cv_readiness/proposal_installed.json`.

Order: bounded read/decode and manifest validation -> suitability -> raw-image
CV-T04 proposals and independent T13 registration -> reference-coordinate bridge
-> actual Tracker.process_sequence -> trajectory attachment -> contract export.
Detection and registration can be computed independently AFTER input acceptance.
Image loading never reads annotations; registration never reads labels/detections.
Truth is used only by separate synthetic scoring after inference.

- Shared object is `app.schemas.result.Detection`, not sequence.Detection.
- Loader is grayscale PNG only: native read-only uint8/uint16, 4Mpx bound,
  default ESA640x480. It is not a streamed upload service or JPEG/RGB adapter.
- Suitability is an internal five-array rule set, independent of HTTP. Supported
  means processing permitted, not correct detection/debris certification.
  Unsupported AND uncertain normally block inference and surface review reasons.
  Current3..30 public SequenceInput and this five-frame validator do not have
  matching scope; other frame counts must be explicitly restricted/reviewed.
- CV-T04 bridge config=None uses frozen threshold4.5/context elongation2.0 and
  cap200; bare OptimizedConfig defaults5.5/2.5 and PipelineConfig threshold5.0
  differ. Shared candidate_cap is not the detector's max_candidates key. Integration
  must review numeric mapping rather than pass an entire PipelineConfig dump.
- Pixels remain raw for detection. Raw positions use top-left origin, integer
  centers, unrounded floats; boxes have positive exclusive upper limits. Reference
  coordinates are translation into frame0; preserve raw fields, inverse matrices,
  warnings and aligned-preview validity masks. Do not clip reference positions.
- Any failed registration, including an empty frame, blocks the whole registered
  tracking call. Failed transforms are null. Raw-only diagnostic comparisons are
  separate and labelled; never exploit tracker raw fallback in a partly registered
  stream. Recovery/segmentation policy is a future Member1/Member3 decision.
- Supply every frame index, including empty/trailing frames, for miss handling.
  Keep unknown timestamps null, units px/frame; known times need consistent
  mappings and px/s. Predicted points never count as observations or detections.

### 15px versus20px: resolved by source, not tuning

Tracker.__init__, current shared PipelineConfig, configs/pipeline.yaml and
ALGORITHMS use **20px**. `Tracker(config=...)` consumes the explicit config value.
The initial tracker commit `12b578fb5a7c1127b4b3e679c191949a8e572a1d` already used
20px; inspected c7227e9 and latest a015cc9 do too. CV-T13's earlier15px phrase was
incorrect documentation and is corrected, not evidence of a gate change. No gate
was tuned here.
Member3 should confirm profile/cadence/registration-uncertainty policy for initial
association, particularly large ESA apparent star-relative target displacement.
Its motion predictor uses frame deltas even when timestamps are supplied; irregular
cadence support cannot be inferred merely from px/s trajectory fitting.

## Actual tests and examples

All used existing Python3.12.14 shared `.venv` for regression tests/diagnostics.
No shared environment installation occurred. Fresh native-source evidence:
`artifacts/reports/cv_readiness/final/index.html` and `summary.json`.

| Check actually executed | Result |
|---|---|
| Initial tests/detection suite with exact tracker snapshot | **291 passed**,0 failed/skipped,133.30s |
| Initial full root suite with same snapshot | **338 passed**,0 failed/skipped,70.54s |
| Post-fix focused robustness tests | **43 passed**,0 failed/skipped,17.18s |
| Final full suite after link fix/regression test | **339 passed**,0 failed/skipped,210.73s |
| Final generated HTML href/src validation | **93 local links resolve**; initial14 absent overlay links fixed |
| Fresh stress runner | Exit0;11 synthetic cases and3 ESA sequences, actual schema-validated tracker outputs |
| ESA train/84 detector+registration+tracker | Supported;[7,7,6,8,6], all transforms accepted;31 registered tracks,0 confirmed |
| ESA train/438 failure policy | Supported;[6,8,5,3,5], frames3/4 registration failed; registered tracker blocked |
| ESA test/1107 | Supported;zero detections/tracks; registration estimated |
| Synthetic counts_change | [5,3,4,5,5];22TP/0FP/0FN;5 confirmed tracks;17 correct links,0 switches/fragments;2/2 gaps recovered |
| Synthetic camera_motion |25TP/4FP/0FN;raw20 switches/fragments,registered0/0;5 confirmed true tracks |
| Synthetic persistent artifact |25TP/5FP/0FN;**1 false confirmed track**, preserved failure |
| Synthetic nearby4px |0TP/0FP/10FN;all targets missed, not association success |
| Unsupported daylight-like input | inference_allowed=false;detections=null, no tracker call/empty success |
| Uncertain noise/blur/blank-frame diagnostics | Deliberately labelled bypass; not production input acceptance; blur yielded56 false confirmed tracks |
| Clean backend wheel + all pinned dependencies, Python-I | Expected missing `astrotrace`; existing distribution is insufficient |
| Existing root packaging proposal in ignored copy | Wheel built/installed, no source PYTHONPATH; train/84 detection+registration+snapshot tracking passed,31 tracks; unsupported guard passed |
| Clean package dependency check | No broken requirements found |
| Real TCP HTTP against temporary unchanged uvicorn app | Health200/bootstrap_only; POST analysis/demo404,POST analysis/upload404,GET demos404; child server stopped afterward |

One existing Starlette/httpx deprecation warning in each suite; no dependency
migration applied. Final339 includes26 contract and21 excluded YOLO utility tests
in addition to292 CV cases. The classical CV/contract publication has318 cases;
the extra case checks real generated report links. Timing includes concurrent
diagnostics and is not a throughput benchmark.
No isolated production tracker installation, analysis HTTP success, UI upload,
job/export flow or new blind real tracking-accuracy benchmark was claimed.

Synthetic scoring uses5px raw-point gate, excludes coincident truth from identity
scoring and never scores predictions as observations. Real ESA sequences have no
supplied persistent truth IDs here;31 registered tracks vs23 raw on train/84 is
code behavior, not improved association accuracy. These are previously used
diagnostics, not an independent scientific generalization test.

### Clean packaging evidence and setup failure

An isolated `.cache/cv_readiness/clean_venv` installed the existing
backend/requirements.lock.txt plus build-only setuptools84.0.0/wheel0.48.0.
Backend and src Python/config files were copied into `.cache/cv_readiness/
packaging_source`, with the EXISTING proposed root pyproject text only in that
copy. Both backend and proposal wheels built with --no-deps/--no-build-isolation.
The probe used `python -I`, and resolved adapter.py from clean_venv/Lib/site-packages;
all core dependency pins match the repository lock, not the separate YOLO runtime.
Canonical tracking import remained absent; only the explicitly recorded source
snapshot was consumed. The proposal solves CV distribution, not tracker merging.

Initial proposal-build command omitted `./` before packaging_source, so pip
interpreted it as a distribution name and failed. Explicit `./packaging_source`
retry passed. This command error is retained in build_proposal.log and is not a
failing algorithm/test or a successful initial build. Evidence:
`.cache/cv_readiness/backend_only.json`, `proposal_installed.json`, build/install
logs, and `artifacts/reports/cv_readiness/http_boundary.json`.

## Exact PowerShell reproduction and viewing

Use an unused output directory; the runner refuses overwrite. The tracker commit
is already fetched locally. If absent on another machine, an explicit read-only
`git fetch --no-tags origin feature/tracking-trajectory` is needed before the run.
No automatic fetch, truth loading or dataset download occurs in the runner.

```powershell
Set-Location E:\Fusion
if ((git branch --show-current).Trim() -ne 'Subham') { throw 'Required branch is Subham; do not switch automatically' }
$env:PYTHONPATH = 'E:\Fusion\src;E:\Fusion\backend'
$cvReadinessRun = 'artifacts/reports/cv_readiness/reproduce_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
& .\.venv\Scripts\python.exe scripts/spotgeo_robustness.py --source data/raw/SpotGEOv2 --output $cvReadinessRun --tracking-ref a015cc949955d0438c8a16789b23746c3206f3d1
if ($LASTEXITCODE -ne 0) { throw 'Evidence run failed' }
$env:CV_T06_TRACKING_SNAPSHOT = (Resolve-Path "$cvReadinessRun/tracking_snapshot").Path
& .\.venv\Scripts\python.exe -m pytest -q -rs -c backend/pyproject.toml tests/detection
if ($LASTEXITCODE -ne 0) { throw 'CV tests failed' }
& .\.venv\Scripts\python.exe -m pytest -q -rs -c backend/pyproject.toml
if ($LASTEXITCODE -ne 0) { throw 'Full suite failed' }
Invoke-Item "$cvReadinessRun/index.html"
Invoke-Item "$cvReadinessRun/train_84/candidates.png"
Invoke-Item "$cvReadinessRun/counts_change/tracking_registered.png"
Get-Content "$cvReadinessRun/summary.json"
Get-Content "$cvReadinessRun/train_84/tracking_registered.json"
Get-Content "$cvReadinessRun/daylight_like/suitability.json"
```

The initial audit used output `artifacts/reports/cv_readiness/run`; its HTML link
failure is preserved in `initial_link_failure.json`. Use the corrected fresh
`artifacts/reports/cv_readiness/final` output for viewing. Initial unit/full logs
are `.cache/cv_readiness/unit_tests.txt` and `full_tests.txt`; final logs are
`final_robustness_tests.txt`, `final_full_tests.txt`, `final_diagnostics.log`.
`artifacts/reports/cv_readiness/final_link_validation.json` records all93 link checks.
Initial clean copy,
isolated environment and HTTP scripts are local ignored audit helpers, not runtime
product source. Existing package proposal is supplied for Member1's separate review.
To repeat its wheel build with this audit's prepared copy and environment:

```powershell
Set-Location E:\Fusion\.cache\cv_readiness
$env:PYTHONPATH = ''
& .\clean_venv\Scripts\python.exe -m pip wheel --no-deps --no-build-isolation ./packaging_source --wheel-dir wheels_repro
& .\clean_venv\Scripts\python.exe -m pip install --no-deps --force-reinstall wheels_repro/orbittrace-0.1.0-py3-none-any.whl
& .\clean_venv\Scripts\python.exe -I probe_install.py --output proposal_repro.json
& .\clean_venv\Scripts\python.exe -m pip check
Set-Location E:\Fusion
$env:PYTHONPATH = 'E:\Fusion\backend'
& .\.venv\Scripts\python.exe .cache/cv_readiness/http_probe.py
Get-Content artifacts/reports/cv_readiness/http_boundary.json
```

For a teammate clean checkout, apply the reviewed packaging change through Member1
first and repeat installed-wheel acceptance, then canonical tracking and HTTP
analysis tests. A source-PYTHONPATH demo alone is insufficient packaging evidence.

## Safe publication plan — prepared, not executed

The23-file allowlist contains only the18 new T13/T14 files, the owned modified
preprocessing README, and the4 readiness handoffs. Earlier46 CV files are already
tracked/published, verified present and audited separately; they need no redundant
commit. The complete reviewed CV inventory has68 unique files.

Excluded: experiments/, tests/yolo/, CV-T15.md, Ultralytics/, PROBLEM_STATEMENT edit,
all raw/external/synthetic scientific data, reports/images, checkpoints, archives,
environments/caches/secrets, root packaging/config/dependency/lock/schema changes,
tracking/trajectory/frontend and all other unrelated changes. No `git add .`, `-A`,
`-u` or force-add. Ignore rules were checked; all generated evidence remains ignored.
Staging allowlist/content fingerprint and source-preservation audits are in
`artifacts/reports/cv_readiness/publication_audit.json` and `preservation_audit.json`.

1. Human reviews the exact23 paths and diff/content, coordinates, failure policy,
   packaging dependency and both team handoffs. Confirm concurrent work is quiet.
2. Obtain explicit approval for staging/commit/push before each requested action.
   Recheck branch/HEAD, approved-file hashes and index contents at action time.
   Stop if someone added other staged content; never unstage/reset their work.
3. AFTER approval only, stage the exact pathspec file and inspect staged names/diff.
   Confirm no disallowed or changed-since-review files were included. Do not stage
   the unapplied packaging patch as a root configuration change.
4. Commit only the approved scope, suggested message
   `feat(cv): prepare T13 registration and T14 robustness for integration`.
   Push Subham only after explicit push approval and a read-only remote recheck;
   if the remote advanced, stop for integration review rather than force/rebase.
5. Member1 separately reviews packaging and Member3 integration/pipeline changes.
   Publication of source is not successful backend or API adoption.

Proposed future staging command, **NOT EXECUTED**:

```powershell
git add --pathspec-from-file=docs/handoffs/CV-INTEGRATION-files.txt
git diff --cached --name-only
git diff --cached --stat
git diff --cached --check
```

Current branch/HEAD unchanged; staged file list empty; no commit/push. An
index tree-content fingerprint was recorded at start for the empty staged diff;
no staged source changes were introduced. Concurrent source fingerprints were
rechecked at completion. No shared-index staging or mutation is part of this plan.

Final audit passed:23 allowlisted paths,68 unique reviewed files,46 earlier files
already tracked. Of121 existing files fingerprinted at start, only the4 deliberate
CV-owned link/test/gate-documentation fixes changed; the other117 files, including
all concurrent CV-T15 source and shared/backend files, remained byte-identical.
AST, file-size/bulk-path exclusions and selected credential/private-key signature
checks passed (the latter is not a universal secret-detection guarantee).
Documentation checker resolved79 local links across67 Markdown files; generated
report link verification separately resolved93 targets. Git whitespace check passed
with existing LF/CRLF notices in PROBLEM_STATEMENT and the older preprocessing
README edit. Untracked allowlisted text was checked for trailing whitespace too.

## Remaining blockers and next task

Member1: approve/install multi-root packaging, integrate actual Member3 source,
review five-frame suitability scope and status mapping, explicit frozen detector
config/override mapping, whole-sequence registration failure policy, safe artifact
transport, bounded uploads, pipeline/jobs/exports and a real successful HTTP
analysis test. No existing shared-schema change is requested by CV.

Member3: confirm20px profile/cadence/uncertainty-aware gating, coordinate policy,
irregular-cadence association, observed out_of_field handling, missed-frame policy,
nearby/crossing ambiguity and persistent artifact false-confirmation handling.

Recommended next task: **Member1 T07 installed-package synthetic end-to-end
integration**, followed by bounded T09 analysis HTTP tests. Preserve the current
detector settings and failure evidence; wider real hard-negative/session validation
and separate YOLO review follow without replacing CV-T04 automatically.
