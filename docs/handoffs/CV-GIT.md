# Handoff: CV-GIT — safe detection publication

Owner: Computer Vision + Dataset Engineer, OrbitTrace / FUSION SPACE-02.
Task: continuation of BACKLOG T03; local Git handoff requested by the user.
Base commit: fa593cf5052f96d311d049f2b84949f588a99407, branch main.
Date: 9 October 2026. State: ready_for_review; publication and shared packaging
approval pending. No staging, branch creation, commit, push, merge, rebase or
source deletion was performed. A read-only inspection fetch updated the local
Member 3 remote ref; no branch was checked out. Original source work was retained.

## Changes made by this audit

Modified: backend/orbittrace/detection/example.py. Its optional snapshot check
now locates Git through Path.cwd(), rather than an installed module's parent
directory. Run the CLI from the repository root. Algorithms and schemas did not
change. Added:

- tests/detection/test_example.py: reproduces the wheel-location failure.
- docs/handoffs/CV-GIT.md: this report and approval-dependent commit plan.
- docs/handoffs/CV-GIT-files.txt: exact 46-file publication allowlist.
- docs/handoffs/CV-GIT-packaging.patch: proposed root pyproject.toml, unapplied.
- docs/handoffs/CV-GIT-PR.md: reviewable PR body.

The allowlist also includes 41 existing CV source/test/doc files that remain
unpublished, covering T14, T03, CV-T04, CV-T05 and CV-T06. It includes this audit's
five added files. There are no datasets or generated report files in that list.
The tracked detection initializer change is earlier CV-T06 work; the unrelated
tracked docs/PROBLEM_STATEMENT.md change is preserved and excluded. There were
no staged changes at audit start. Unchanged bootstrap files already tracked by
Git supply app schemas/configuration, backend packaging/lock and API tests.

Publication dependencies:

| Source group | Why it is required |
|---|---|
| src/astrotrace/datasets, preprocessing, detection | Loader, image validation, both algorithms, shared interface, runner, independent evaluation and visualization |
| backend/orbittrace/detection | Actual backend import bridge, flattened Detection lists and example CLI |
| scripts/spotgeo*.py | Dataset inspection/preparation, baseline benchmark, optimization and historical handoff utilities |
| tests/detection | Synthetic fixtures generated at runtime, scientific bounds/leakage tests and actual tracker compatibility |
| Owned handoffs and guides | Configuration, coordinate/score semantics, measured historical tradeoffs and reproduction instructions |
| Existing backend/app and backend/requirements.lock.txt | Integration-owned schema 0.1.0 and pinned runtime/test dependencies; already tracked, no edits |

## Git audit and team coordination

Remote: https://github.com/Subham5126/fusion26.git.
Read-only ls-remote found main, development, Rohit, Subham and Yogesh at the base
commit. **dev does not exist.** The contribution guide calls for dev; this is an
actual target-branch blocker, not permission to silently substitute development.
Member 1 must confirm/create the intended integration branch.

Member 3's feature/tracking-trajectory advanced from 8edb6ea to
c7227e9f00cc50a1b480f6d257dd1367bc589aec. The newer delta adds evaluation harness
work; tracker.py and fit.py have the same hashes as the earlier tested source.
No incoming changed paths overlap the 46-file CV allowlist. This is a path/content
audit, not a trial merge or a guarantee about future commits. Member 1's packaging,
pipeline, health and STATUS/BACKLOG files remain integration-owned and unchanged.
No unseen/unpublished teammate changes can be ruled out.

Actual Member 3 callable is Tracker.process_sequence(detections,
frame_indices=None, frame_timestamps=None), using app.schemas.result.Detection
and PipelineConfig. Old branch handoffs mentioning app.schemas.sequence.Detection,
TrackerConfig, update or finalize are stale. No tracker/evaluator files were
changed or added to the CV publication list.

## Commit safety evidence

Existing ignore rules cover data/raw, external/synthetic/truth data, ZIP/archive
and model extensions, artifacts/reports, artifacts/jobs, .cache, .venv, bytecode,
build/egg-info and common credential files. Representative actual data, report,
environment and hypothetical archive/secret paths passed git check-ignore.
The 137 already tracked files contain no file over 1 MiB and no archive, weight,
private-key or audit-generated data/environment path. .env.example contains
localhost bootstrap placeholders; it has no API credential.

The explicit list is the commit boundary: ignore rules do not justify git add -A
or git add -f. The local publication audit records each path, size and SHA-256,
plus credential-pattern and incoming-path checks. Pattern scanning is a bounded
check, not proof against all possible secret formats. Review the final staged
diff before committing. Reports remain under artifacts/reports/cv_git_handoff;
the isolated build/environment live under .cache/cv_git_handoff. Neither is staged.

## Packaging: current failure and tested proposal

backend/pyproject.toml currently discovers app* and orbittrace* only. A fresh
non-editable wheel installation plus python -I -c "import astrotrace" fails with
ModuleNotFoundError, exit 1. The current source-based tests/CLIs can mask this by
inserting source paths. The existing installation is not teammate-ready.

[Packaging proposal](CV-GIT-packaging.patch) adds a root manifest using explicit
app=backend/app, orbittrace=backend/orbittrace, astrotrace=src/astrotrace mappings
and namespace discovery over backend and src. It copies existing dependency
ranges and optional extras; no runtime dependency or lock change is proposed.
After approval, install from the repository root rather than ./backend.
backend/pyproject.toml remains unchanged; Integration should make the root
manifest canonical and review the duplicated metadata in its own follow-up.

**AGENTS.md explicitly says shared root-config/dependency changes go to
Integration via handoff.** Therefore the proposed manifest was tested in an
isolated source copy and has not been applied to the shared checkout.

Actual validation: fresh CPython 3.12.14 venv with system-site-packages disabled,
the existing pinned lock, setuptools84/wheel0.48, built/installed non-editable
proposal wheel. Isolated-mode imports resolve app, orbittrace and astrotrace
under that new environment's site-packages, without PYTHONPATH. pip check passes.
The wheel contains 17 astrotrace Python modules and 46 total entries, with no
bulk data/environment paths. sdist includes the astrotrace implementation and
builds successfully; its minimal source copy warned that README was absent.
Windows/Python3.12 is tested; other operating systems/Python versions are untested.

Wheel hashes (build artifacts only, not stable cross-machine promises):
current backend cb6ff9eec01f420593ef9ec7df5cf17cc950a411fbb6e947fe088f61057719a1;
proposal d2f10ceeac23aca098286ca8abdab3f6d7a14be1ef24465f890aba037881c7c0.

## Data and detector checks actually run

Extracted ESA root: E:\Fusion\data\raw\SpotGEOv2. Explicit installed-wheel runs
read train/84/1.png..5.png and test/1107/1.png..5.png. Real compatibility tests
also read test/57/1.png..5.png: 15 distinct ESA PNGs in total this audit, with
repeat passes. Native decode/order is 640x480 uint8, official frame1..5 mapped
to internal0..4. No ESA annotation JSON was required for these inference runs.
Other unit tests generate small authored images/annotation/ZIP fixtures in
temporary directories. No dataset was downloaded or distributed.

| Current installed-wheel check | Actual result |
|---|---|
| CV-T04 train/84 | 34 detections; per-frame7,7,6,8,6; finite shared schemas and native bounds validated |
| CV-T04 test/1107 | 0 detections; five frames processed, zero tracks |
| Preserved T03 train/84, class defaults | per-frame42,40,40,35,36; baseline callable succeeds |
| Member 3 c7227e9 consumption | Both CV-T04 sequences pass schema/observed-ID checks; train/84 has23 tracks,3 confirmed,3 fitted trajectories |
| Frozen T03 source audit | All8 recorded source/test SHA-256 values match |

T03 class defaults differ from its historical tuned benchmark settings; these
counts are an availability smoke check, not a accuracy/precision comparison.
CV-T04 configuration hash is
50e48c61052883ad8a2b8906911d931001652cb6cb8c688d8e14f39c70a61595.
It uses threshold_sigma4.5, denoise_sigma0.6 and max_context_elongation2.0 with
the existing remaining defaults. train/84 detection calls total409.713ms;
test/1107 total303.484ms. These single-run timings exclude loading/rendering/
tracking and are not a new throughput benchmark. Prior precision/recall figures
are historical; no benchmark, tuning or independent blind validation was rerun.

Member 3 source hashes: tracker.py
34911026f4f21b47006ad5cb0c2893e9ca2b746ec3a7f1f11a35839edd3a57b3;
fit.py fa4f02be0bd005c38d429132621f8dd4626bf4a3d860da068cf23791728b1658.
Raw/reference alignment was not estimated. Saved AnalysisResult declares failed
registration with an explicit diagnostic warning; those tracks do not prove
scientifically correct ESA identities or physical trajectories.

## Exact interface and integration readiness

```python
from astrotrace.datasets import SpotGeoDataset
from orbittrace.detection import detect_sequence

sequence = SpotGeoDataset("data/raw/SpotGEOv2", split="train").load_sequence(84)
frames = [frame.pixels for frame in sequence.frames]
detections = detect_sequence(frames, sequence_id="train-84", method="optimized")
# Member 3, after that separately reviewed branch is installed:
# tracks = Tracker().process_sequence(detections, frame_indices=range(len(frames)))
```

Signature: detect_sequence(frames: Sequence[np.ndarray], *, sequence_id: str,
profile="spotgeo", timestamps_s=None, config=None, method="optimized")
-> list[app.schemas.result.Detection]. Ordered equal-size nonempty grayscale
uint8/uint16 or normalized finite float32/64 frames;0..30 arrays accepted by the
adapter, while public SequenceInput requires3..30. Empty scenes return []; pass
all frame indexes to tracking. Timestamps are unknown or strictly increasing
seconds; cadence is not guessed. Invalid inputs/config raise ValueError.

Flat outputs contain frame_index, unique proposal detection_id, x_raw_px,
y_raw_px, exclusive-upper bbox_raw_px, kind, quality_score, detector_name and
nullable reference/endpoints/evidence fields. Top-left origin, x right/y down,
integer pixel centers, subpixel floats preserved. Sequence identity belongs to
the call/evidence envelope; no schema field was invented. Proposal IDs are not
persistent object IDs. The score (1-exp(-peak_snr/8))/max(1,elongation) is a
normalized uncalibrated contrast/compactness heuristic.

Member 3 can consume this interface after publication and reviewed installation;
the actual latest source was tested. The local backend's canonical tracker is
still absent, pipeline.analyze raises NotImplementedError, health flags detection/
tracking false, and analyze/demo returns404. Full-suite readiness tests verify
these actual absences. **Backend pipeline currently selects neither T03 nor
CV-T04**, although the standalone adapter defaults to CV-T04. No API integration
success is claimed. No YOLO/model weights or learned detector are implemented.

## Commands run and outcomes

Commands use E:\Fusion as cwd unless explicitly noted. Console outcomes and
generated JSON are local evidence, excluded from publication.

| Actual check | Outcome |
|---|---|
| git status/branch/remotes/index, ls-files, ls-remote, fetched Member 3 diff | Base/main and empty index verified; no dev; no changed-path overlap |
| New regression before fix | 1 failed, exposing site-packages Git lookup |
| Full pytest with latest snapshot, command below | 236 passed,0 failed,0 skipped,1 existing Starlette/httpx warning;180.76s |
| Current backend wheel isolated import | Expected failure: astrotrace missing |
| Proposed root wheel build/install/isolated imports and pip check | Passed; current working environment not replaced |
| Installed CLI real/empty/baseline runs and schema revalidation | Passed, as above |
| Source distribution build/content audit | Passed; minimal-copy README warning |
| Initial extra content/sdist command | Failed because relative interpreter path used the candidate cwd; rerun with absolute interpreter succeeded |
| Existing venv pip check | No broken requirements |
| Existing documentation check before audit docs | 67 local links in57 Markdown files resolved |
| git diff --check and packaging git apply --check | Passed; unrelated PROBLEM_STATEMENT newline notice only |
| Final publication/whitespace/credential audit and staging dry run | All46 files exist;384,714 bytes;0 whitespace/credential findings;0 incoming path overlaps; index stays empty |
| Final documentation check | 70 local links in59 Markdown files resolved locally |
| Installed-module and compilation checks | All27 non-initializer Python modules in the proposal wheel import from its site-packages; compileall passes for the changed CLI/new test |

The initial regression failure is resolved, not omitted. A slow full run completed
normally; no successful count was copied from an earlier milestone. Tests include
image/ZIP/annotation bounds, empty/noisy/faint/shape cases, coordinate handling,
finite schemas, leakage guards, adapter repeatability and6 actual snapshot
compatibility cases. Member 3's own entire branch suite was not merged/executed.

## Test and view the current verified installation

These commands work with the isolated proposal already installed by this audit.
Its environment is deliberately not committed. Every output directory must be
new; the example refuses to overwrite evidence.

```powershell
Set-Location E:\Fusion
$cvPython = 'E:\Fusion\.cache\cv_git_handoff\clean_env\Scripts\python.exe'
$cvOutput = 'artifacts/reports/cv_git_handoff/reproduce_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
& $cvPython -I -c "from astrotrace.datasets import SpotGeoDataset; from orbittrace.detection import detect_sequence; print('Installed imports OK')"
& $cvPython -I -m orbittrace.detection.example --source data/raw/SpotGEOv2 --split train --sequence 84 --output $cvOutput --tracking-ref c7227e9f00cc50a1b480f6d257dd1367bc589aec
if ($LASTEXITCODE -ne 0) { throw 'Real detector/tracker compatibility failed' }
$env:CV_T06_TRACKING_SNAPSHOT = (Resolve-Path ($cvOutput + '/tracking_snapshot')).Path
.\.venv\Scripts\python.exe -m pytest -q -c backend/pyproject.toml
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& $cvPython -m pip check
Invoke-Item ($cvOutput + '/candidates.png')
Get-Content ($cvOutput + '/detections.json')
Get-Content ($cvOutput + '/tracking_result.json')
```

Open the actual audit evidence now:

```powershell
Invoke-Item .\data\raw\SpotGEOv2\train\84\1.png
Invoke-Item .\artifacts\reports\cv_git_handoff\real_train84\candidates.png
Invoke-Item .\artifacts\reports\cv_git_handoff\real_empty1107\candidates.png
Get-Content .\artifacts\reports\cv_git_handoff\real_train84\detections.json
Get-Content .\artifacts\reports\cv_git_handoff\real_empty1107\detections.json
Get-Content .\artifacts\reports\cv_git_handoff\real_train84\tracking_result.json
Get-Content .\artifacts\reports\cv_git_handoff\pytest.txt
Get-Content .\artifacts\reports\cv_git_handoff\publication_audit.json
```

Green crosses show actual detector proposals; no labels or tracks are rendered
in these panels. Display scaling is cosmetic. Source PNGs and full coordinates
remain native; the panel was visually inspected across all five frames.

## Clean teammate installation, only after root packaging approval

Integration must approve/apply the exact patch first. These are proposed human
actions; neither git apply nor shared manifest edits were executed here.

```powershell
Set-Location E:\Fusion
git apply --check docs/handoffs/CV-GIT-packaging.patch
if ($LASTEXITCODE -ne 0) { throw 'Packaging proposal needs re-review' }
git apply docs/handoffs/CV-GIT-packaging.patch
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps .
.\.venv\Scripts\python.exe -I -c "import astrotrace.detection.optimized, orbittrace.detection; print('Installed imports OK')"
.\.venv\Scripts\python.exe -m pip check
```

Run the earlier example with .venv's Python. External ESA data remains a separate
prerequisite and must be placed at the documented root by the teammate; there is
no automatic dataset download. Unit tests can run without it, with explicit
real-data skips. Fetch Member 3's reviewed ref to enable the optional snapshot.

Historical CV-T04 analysis and CV-T05 package/final-evaluate commands reference
ignored frozen reports/config/hash snapshots. Those reports are not silently
published in this commit. Production adapter/example inference needs none of
them. Full historical benchmark replay requires the documented local evidence
or regeneration in order from T03; do not describe report-free replay as tested.
Some historical Markdown links point at ignored evidence and therefore will not
resolve in a clean checkout before regeneration. The current local link check
passing is not a clean-checkout documentation guarantee.

## Exact staging and commit plan — approval required

1. Human reviews all46 paths in [the allowlist](CV-GIT-files.txt) and the
   [PR body](CV-GIT-PR.md). Integration approves the root manifest separately.
2. Resolve the missing dev branch with the lead. Do not substitute development
   or rewrite any teammate branch. No pull/rebase/reset is part of this plan.
3. Commit the46 CV source/doc/test files as one coherent publication; then
   commit the approved root manifest as a separate build change. Unrelated
   PROBLEM_STATEMENT work stays unstaged. If a path/HEAD changes, re-audit.
4. Push only the new codex branch and open a reviewed PR to the confirmed dev.

After explicit approval, exact commands:

```powershell
Set-Location E:\Fusion
if ((git rev-parse HEAD).Trim() -ne 'fa593cf5052f96d311d049f2b84949f588a99407') { throw 'HEAD changed; re-audit' }
if (@(git diff --cached --name-only).Count -ne 0) { throw 'Existing staged work; stop and review' }
git switch -c codex/cv-detection-handoff
if ($LASTEXITCODE -ne 0) { throw 'Branch creation failed' }
git add --pathspec-from-file=docs/handoffs/CV-GIT-files.txt
if ($LASTEXITCODE -ne 0) { throw 'Explicit staging failed' }
git diff --cached --check
git diff --cached --stat
git diff --cached --name-only
# Inspect the staged diff manually before proceeding.
git diff --cached
git commit -m "feat(cv): publish spotGEO detectors and tracking adapter"
if ($LASTEXITCODE -ne 0) { throw 'Source commit failed' }
# Only after Integration approval, apply the tested packaging proposal as above.
git add -- pyproject.toml
git diff --cached --check
git diff --cached -- pyproject.toml
git commit -m "build: package astrotrace with the OrbitTrace backend"
if ($LASTEXITCODE -ne 0) { throw 'Packaging commit failed' }
$cvDev = @(git ls-remote --heads origin refs/heads/dev)
if ($LASTEXITCODE -ne 0 -or $cvDev.Count -eq 0) { throw 'Remote dev is absent; lead must resolve PR target' }
git push -u origin codex/cv-detection-handoff
if ($LASTEXITCODE -ne 0) { throw 'Push failed' }
gh pr create --base dev --head codex/cv-detection-handoff --title "Publish OrbitTrace CV detectors and tracking adapter" --body-file docs/handoffs/CV-GIT-PR.md
```

gh is not installed on this machine. Install/authenticate it manually or, after
the approved push and dev exists, open the GitHub compare UI:

```powershell
Start-Process 'https://github.com/Subham5126/fusion26/compare/dev...codex%2Fcv-detection-handoff?expand=1'
```

Paste CV-GIT-PR.md into the description and request Member1/Member3 review. These
commands are a proposed plan, not evidence that a commit/push/PR succeeded.

## Remaining blockers and next dependency

Source publication waits for user approval. Clean production imports wait for
Integration's packaging approval/application; dev is absent; gh is unavailable.
Member 3's tracker remains on its separate branch, and backend/T07 wiring selects
neither detector. Registration/common-frame validity and real association accuracy
are unverified; residual streak/noise false positives and faint/overlap misses
remain. Heuristic scores do not certify object identity or physical/orbital units.

Recommended next task: Member1 approves packaging/branch policy, publishes this
bounded source set, and reviews Member3 integration. Then wire the existing
adapter/Tracker through T07 with explicit empty-frame indexes and registration
failure semantics, and test a synthetic end-to-end API path before making real
scientific trajectory claims. Integration alone updates STATUS/BACKLOG.
