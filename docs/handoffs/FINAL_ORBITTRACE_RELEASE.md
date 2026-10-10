# Final OrbitTrace release handoff

Task: T19 integration continuation under the final master release request. Date: 2026-10-10. Root: `E:\Fusion`. Branch: `Subham`. Base commit: `1bad730757f2183985595d6ecee911c1179925e9`.

## Verdict and scope

**PARTIAL.** The local upload, processing, selected-track replay, native overlays, real reports and optional supervised scoring are implemented and tested. Supplied bright/faint/multiple-target demonstrations work with experimental Motion mode. Registration still rejects the supplied trails/artifacts sequence and 12 of the 32 evaluated ESA sequences. Motion mode is worse on ESA; it is explicitly experimental and Standard remains default. No registration failure is replaced with an invented identity transform or successful empty result.

No stage, commit, push, merge, rebase, branch switch, deployment or resource creation was performed. Existing unrelated changes, datasets and YOLO experiments remain intact. Shared AnalysisResult 0.1.0 and Member 3 tracking source were not changed. No dependency or lockfile changes were needed. Historical `docs/STATUS.md` describes an older verification run; the evidence below is for this release.

## Implemented changes and reused interfaces

The existing upload client, job polling, frame retrieval, schema, OpenCV detector, T13 registration, Member 3 minimum-cost gated association and trajectory fitter remain the application backbone. `POST /api/analyze/upload` accepts additive form field `analysis_mode=standard|temporal`, default `standard`; invalid modes return 422. The frontend passes it through `runUpload(sequence, files, signal?, mode='standard')`. Results, diagnostics and native images continue through the existing job routes. Public requests accept no model, label or arbitrary filesystem paths.

`src/astrotrace/detection/temporal.py` adds `detect_temporal_sequence(frames, registration, *, sequence_id, profile, timestamps_s, config)`. It requires five images and verified registration, forms a registered temporal median, excludes invalid warp support, erodes the support border and runs the existing optimized detector on positive residual images. It returns native-image detections. Original candidates remain in `diagnostics.original_detections`. Inference reads no ground truth. Slow/stationary objects and streak backgrounds can be suppressed or mishandled; this is not a universal detector upgrade.

Standard retains the 20 px association gate. Experimental Motion uses 25 px because the supplied bright sequence moves about 20.6 px between observations. Both retain genuine minimum-cost gated matching and explicit unmatched states. No tracker algorithm or registration threshold was relaxed.

The UI now defaults to one selected track's path, with optional Show all tracks. Current detections remain visible by default, including uncertain candidates; hiding uncertain candidates is an explicit display choice. Stationary repeated candidates are no longer presented as supported motion just because they were repeatedly associated. Backend association status and UI evidence classification remain distinct. Compact labels for other detections appear on hover/focus.

Observed points come only from actual associated detections, sorted and clipped to the current timeline frame. Rewind removes later observations. Missing detections preserve earlier history without inventing a point. Current native boxes have glow and corner brackets. Reference history and forecasts are inverse-transformed into the displayed raw frame; the image and SVG share zoom/pan. Pixel centers, the half-pixel display convention and exclusive-upper-bound boxes are retained. Native coordinates remain finite and unrounded internally.

Only genuine fitted forecasts render, using purple dashed lines, hollow markers and a Predicted label. The viewer limits the future display to the next frame; reports retain all backend forecast points and explain that difference. Visible forecast counts follow track selection. The enlarged path panel no longer leaks future observed positions at earlier timeline frames.

## Measured detector comparison

Exact sequence membership, annotation hashes and counts are in `FINAL_DETECTOR_EVALUATION.json`. Five supplied folders were evaluated independently from ESA; labels were used only after inference for one-to-one matching within 5 px.

| Cohort / mode | Precision | Recall | F1 | FP/frame | Localization RMSE px |
|---|---:|---:|---:|---:|---:|
| Supplied, Standard | 0.936% | 87.50% | 1.852% | 111.15 | 0.199 |
| Supplied, Motion | 57.50% | 95.83% | 71.875% | 0.85 | 0.167 |
| ESA, Standard | 50.862% | 67.429% | 57.985% | 1.14 | 0.329 |
| ESA, Motion | 26.097% | 64.571% | 37.171% | 3.20 | 0.368 |

Supplied metrics cover the four mutually successful sequences, 20 frames: Standard TP21/FP2223/FN3; Motion TP23/FP17/FN1. The trails/artifacts sequence failed registration in both modes and is excluded from accuracy denominators, not counted as success. Mean pipeline time increased 435.7 to 584.2 ms; detection time 197.4 to 377.2 ms per sequence.

ESA metrics cover only 20 mutually registered sequences (100 frames) out of 32 attempted: Standard TP118/FP114/FN57; Motion TP113/FP320/FN62. **12/32 registration failures in both modes** are separate failures. Mean successful pipeline time increased 308.2 to 530.2 ms; detection time 112.8 to 334.5 ms. These results are not a benchmark over all ESA images and do not establish debris identity.

| Supplied sequence, Motion mode | Actual outcome |
|---|---|
| Single bright | 5/5 target observations, zero FP, one stable five-observation track |
| Single faint | 4/5 observations, zero FP, same ID through missing third frame |
| Multiple targets | 14/14 observations, zero FP, three separate tracks with 5/4/5 observations; no matched-target identity switches |
| Trails and artifacts | Registration rejected frames 1, 2 and 4 (zero-based); consensus checks failed; no result fabricated |
| No moving target | 17 false candidates, 16 tentative/ended track records, zero confirmed tracks/forecasts; not a perfect zero-detection result |

The original supplied archive was found in the user's Downloads, not recreated. SHA256: `4a4e78b20f62d62566d5ca3a87ebc3da93a1a51d7cd7c2b35ce6238836aa870e`. Extracted QA files are under `.cache/final-release/supplied`; ground_truth.json is never uploaded. Real ESA train/84 completed with 31 detections and no valid fitted forecasts; train/438 still fails registration. Arbitrary uploaded sequences, including the previously reported test/138 case, are not claimed fixed by these changes.

## Genuine supervised AI assessment

`candidate-logistic-v1` is a CPU logistic model trained using existing SciPy, with ten image-derived candidate features, signed-log transformation, training-only standardization and L2 regularization. Features: peak SNR, area, elongation, aperture SNR, raw peak fraction, context elongation/area, component aspect, normalized local noise and contrast. Runtime inference uses no annotation or truth coordinates.

ESA sequence-disjoint membership is frozen in `FINAL_ML_EVALUATION.json`: 96 training sequences (480 frames, 992 candidates), 32 validation (160 frames, 281 candidates), 64 held-out test (320 frames, 668 candidates). Decoded image hashes prevent cross-split image duplicates. Capture-session metadata is unknown, so session independence is not claimed. Prior evaluation cohorts were excluded from this training selection. Matching labels are annotation matches within 5 px, not physical debris classifications.

| Held-out 320 frames | Precision | Recall | F1 | FP/frame | TP / FP / FN |
|---|---:|---:|---:|---:|---|
| Original candidates | 47.006% | 62.8% | 53.767% | 1.10625 | 314 / 354 / 186 |
| Offline threshold 0.2 | 62.733% | 60.6% | 61.648% | 0.5625 | 303 / 180 / 197 |

The threshold was selected on validation to retain at least 95% of baseline recall while maximizing precision. It loses 11 additional true detections on test. **Automatic filtering is OFF.** Scores are experimental, uncalibrated annotation-match scores, not probabilities of debris. No accuracy claim is made for temporal residual candidates: that detector is explicitly incompatible with this model.

Scoring 668 candidates took 32.73 ms; Python-tracked peak allocation was 148,729 bytes, not whole-process/native RSS. Model JSON is 1,853 bytes, SHA256 `9045842e3e5168f7dcd991829fc71aa8a4eb6571997f50af3ac6d55068103577`. Dataset attribution: Chen et al., SpotGEOv2, DOI 10.5281/zenodo.4432143; local metadata records CC BY 4.0. Archive checksum verification was not completed, and source images are not redistributed.

Enable optionally with operator environment variable `ORBITTRACE_CANDIDATE_MODEL=E:\Fusion\configs\candidate_assessment_v1.json`. Successful model loading is cached. Missing, corrupt, oversized or detector-incompatible models produce unavailable assessment without breaking analysis. The local verified server enables it; deployment/default configuration does not. Existing YOLO work is preserved and is not this feature's live model.

## UI, reports and accessibility

The custom cursor is now mounted and uses on-demand animation without React mouse-position rerenders. It stops when settled/hidden and respects reduced-motion/coarse pointers; native image inspection and inputs retain native cursor behavior. Landing graphics pause offscreen/hidden and support a static reduced-motion state. Duplicate scroll animation machinery was removed. Public conceptual workbench preview and duplicate Optical observations navigation button were removed; synthetic backend fixtures/tests remain. Functional readiness diagnostics remain collapsed rather than being replaced with decorative controls.

Detector heuristic, track quality and optional ML score are separate metrics. Values are genuine and missing observations/scores are explicit. Bars transition on score change with reduced-motion overrides. Generic job progress is indeterminate, not a fabricated processing percentage.

PDF and JSON are generated in the frontend from the actual result plus validated diagnostics; backend CSV remains available. Reports include source, dimensions, per-frame counts, selected track, raw/reference coordinates, actual boxes and scores, missing frames, motion description, forecast model/points, optional AI details and scientific limitations. Unknown timestamps, physical speed and unavailable uncertainty remain unknown. PDF/JSON downloads were exercised; the final two-page PDF was rendered and visually inspected. Samples: `.cache/final-release/verified-report.pdf` and `verified-report.json`.

## Actual verification

| Check | Outcome |
|---|---|
| Full Python suite | **565 passed, 2 skipped, 6 warnings**, 99.23 s |
| Main frontend tests | **123 passed**, zero failures |
| Overlay tests | **19 passed**, zero failures |
| TypeScript and Vite | Passed; lazy landing/Three.js chunk 546.46 kB produces >500 kB warning |
| Genuine HTTP runner | All 9 expected scenarios passed, including expected failures |
| Browser | Actual five-image uploads, all five supplied sequences, ESA84, empty and unsupported input exercised |

Python skips require the optional historical `CV_T06_TRACKING_SNAPSHOT`; current installed tracking is exercised through pipeline/API/browser tests. Warnings: Starlette httpx/422 deprecations and intentional invalid FITS BLANK test. An initial new test expected FastAPI's generic detail envelope; it was corrected to the application's actual sanitized error contract before the final full green run. `npm test` is not defined; the actual repository runners below were used.

HTTP cases: synthetic one-object, changing counts/missed observations, valid empty, unsupported daylight, uncertain noise, registration failure, ESA84, ESA438 expected failure, and actual synthetic image upload. Validation limits, polling, results, native image retrieval and exports were exercised through the frontend proxy. Evidence: `.cache/final-release/http-verified/receipt.json`.

Browser evidence: progressive 1/2/3/4/5 observations and 0/1/2/3/4 solid segments; rewind hides future observations; playback preserves history; current boxes update; missing third-frame observation has no fake box; distinct multi-object IDs; selected-only/all-track toggles; next-frame forecast; independent ML score on real ESA; genuine PDF/JSON downloads; empty/error states; no console errors/warnings recorded. Native box coordinates remain unchanged at browser zoom up to 800%; exact 1x/2x/4x/8x alignment is also unit-tested. Keyboard pan and 390x844 responsive layout were exercised with no horizontal overflow. Mouse-drag pan was not separately repeated in this final browser pass. Cursor and landing scroll/graphics were directly observed. Reduced-motion code/CSS handling is implemented, but OS reduced-motion preference switching was not directly browser-verified; that acceptance item remains manual.

Evidence files: `pytest-verified.log`, `frontend-verified.log`, `overlay-verified.log`, `build-verified.log`, `browser-evidence.json`, `final-multi-object.png`, `mobile.png`, `esa-ai-panel.png`, and `verified-report-1.png`/`verified-report-2.png`, all under `.cache/final-release`. These generated artifacts stay out of publication.

## Reproduction in Windows PowerShell

Services are currently running. At final verification, backend listener PID **33216**, frontend PID **19296**; backend venv launcher PID **14188**. Source roots and launcher paths are under E:\Fusion. Do not start duplicate services or terminate unrelated listeners. The launch scripts refuse occupied ports.

Backend, when stopped:

```powershell
Set-Location E:\Fusion
$env:ORBITTRACE_CANDIDATE_MODEL = 'E:\Fusion\configs\candidate_assessment_v1.json'
.\scripts\Start-Backend.ps1
```

Frontend, in another terminal when stopped:

```powershell
Set-Location E:\Fusion
.\scripts\Start-Frontend.ps1
```

Open http://127.0.0.1:5173/#/workbench (API http://127.0.0.1:8000). Select five PNGs, confirm order, use Motion for supplied compact-target QA and Standard for ESA, then Analyze. Use track selection, Play, timeline, overlay toggles, zoom/fit and keyboard pan. Final-frame purple markers are forecasts only when the backend supplies them. Download Report produces PDF; Report JSON includes machine-readable values.

```powershell
Set-Location E:\Fusion
.\.venv\Scripts\python.exe -m pytest -q -rs
Set-Location E:\Fusion\frontend
node tests/run-data-tests.mjs
node tests/overlay.test.mjs
npm run build
Set-Location E:\Fusion
.\.venv\Scripts\python.exe -X utf8 -I scripts/verify_final_http.py --url http://127.0.0.1:5173 --origin http://127.0.0.1:5173 --output .cache/final-release/http-recheck
.\.venv\Scripts\python.exe -X utf8 -I scripts/verify_release_sequences.py --supplied .cache/final-release/supplied --esa data/raw/SpotGEOv2 --output .cache/final-release/comparison-reproduce
.\.venv\Scripts\python.exe -X utf8 -I scripts/train_candidate_assessment.py --source data/raw/SpotGEOv2 --output .cache/final-release/ml-reproduce
```

Use fresh output names for repeated runs. Training is optional reproduction, not required at application startup. Real images remain in `data/raw/SpotGEOv2`; supplied inputs remain in the ignored extraction directory. No truth files belong in the upload selection.

## Publication and deployment, not executed

The exact created/modified source and evidence file allowlist is `FINAL_RELEASE_ALLOWLIST.txt` beside this handoff. It includes this document, the allowlist itself, the small model JSON, scripts and compact evaluation JSON. All entries are relative to E:\Fusion. The Git index remains untouched.

Explicitly excluded preexisting work: `Dockerfile`, `docs/RAILWAY_DEPLOYMENT.md`, `docs/VERCEL_HANDOFF.md`, `.railwayignore`, `Ultralytics/`, `scripts/Vercel.cmd`. Also excluded: raw data, large checkpoints, environments, caches, generated browser images/reports, secrets and unrelated experiments. An existing whitespace warning in RAILWAY_DEPLOYMENT.md is unrelated and preserved.

After explicit publication approval, inspect before staging:

```powershell
Set-Location E:\Fusion
git branch --show-current
$releaseFiles = Get-Content docs/handoffs/FINAL_RELEASE_ALLOWLIST.txt
git diff -- $releaseFiles
git status --short
# Only after reviewing tracked diffs AND new files and approving publication:
git add -- $releaseFiles
git diff --cached --check
git diff --cached --stat
git commit -m "Improve live tracking visualization and add experimental candidate assessment"
git push origin Subham
```

Stop if branch is not Subham, if the index already contains unrelated work, or if another contributor has changed allowlisted files. No main/development push, force push or automatic merge is authorized.

Read-only production checks returned frontend HTTP 200, backend health HTTP 200/schema0.1.0 and correct CORS for https://fusion26.vercel.app. Its bundle points at https://orbittrace-api-production.up.railway.app. This validates existing V1 connectivity, not deployment of this release. No new remote upload or release deployment was run.

After separate deployment approval: deploy backend from the reviewed Subham commit using the existing Railway service; preserve current limits and CORS. Deploy the frontend from `frontend` with build `npm run build`, output `dist`, and Production `VITE_API_BASE_URL=https://orbittrace-api-production.up.railway.app` (no /api suffix). Verify health, genuine uploads, polling, raw images, exports and browser results again before declaring production success.

Optional ML packaging needs a reviewed additional change: the existing Docker build copies backend/src, not configs. Include only `configs/candidate_assessment_v1.json` in the build context and COPY it into the image, then set ORBITTRACE_CANDIDATE_MODEL to that actual container path. Review Dockerignore allowlisting too. This task deliberately did not overwrite the unrelated Dockerfile changes. Without that packaging/env change, assessment safely remains unavailable; the core pipeline works. Old backend deployments may ignore the additive mode form field; the frontend explicitly reports a requested Motion mode that was not applied.

## Remaining blockers and next dependency

1. Investigate registration robustness with fixed independent real sequences; do not merely lower consensus gates or bypass registration.
2. Motion residual detection is unsuitable as the default for ESA and still produces 17 false detections in the supplied negative case.
3. ML scores are experimental and uncalibrated; session-independent validation, broader recall analysis and deployment packaging are pending. Automatic filtering remains off.
4. Direct reduced-motion preference browser verification and remote release smoke testing remain pending.
5. User approval is required before publication/deployment. Prioritize registration/domain evaluation next, before more visual polish or claims of improved real-world accuracy.
