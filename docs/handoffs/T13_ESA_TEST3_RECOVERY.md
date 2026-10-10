# T13 follow-up — ESA test/3 registration recovery

Role: CV / registration. Base: `9e26eb08479d2b558bed565817dd7b75a1fb3ef3`,
branch `Subham`. State: implemented and tested locally; detector accuracy
improvement remains unproven. No shared schema, tracking, detector, dependencies,
UI, deployment configuration or model weights changed.

## Actual failure and correction

The latest failed upload was `job-3a04a81498b84b939e21051cb1426871`.
All five native API frames matched decoded ESA `data/raw/SpotGEOv2/test/3`
pixels exactly. This is a different sequence from the earlier test/1003 recovery.
Frame index 4 failed: global phase response 0.075303; the verified frame-3 pair
seed was valid, but its direct frame-0 optical-flow retry retained only 10 fitting
inliers (12 required). The ordinary 25px window retained 11. Detection/tracking
were blocked before running; this error was image registration, not model inference.

Keep the existing retry and its successful results. If its **only** failure is
`weak_translation_consensus`, perform one direct fit using a fixed 17px flow
window, provided the configured first retry window is larger than 17. Do not
retry reserved-validation failures or search a window grid in inference.
The reference features and original every-fifth-feature reserved partition stay
the same. The neighbor transform only initializes a fresh frame-0 fit.
No final chained transform or identity substitute is accepted. All support,
forward/backward, validation residual, spatial coverage, shift and overlap gates
remain unchanged. `neighbor_retry=0` disables both retry stages.

Actual recovered fifth frame:

```text
seed_frame_index: 3; flow_window_px: 17
fit_inliers: 12; fit_inlier_ratio: 0.857143
validation_inliers: 5; validation_rmse_px: 0.670869
raw_to_reference translation: (+178.655800, -69.696014) px
reference_to_raw translation: (-178.655800, +69.696014) px
```

Live API input SHA-256: `543e2cc3d4f0e9e82b9ebc30847cbf157a09f9b6f5c3cf59f4e159f41cab908a`.
Reported configuration SHA-256: `887caab9290c6fceaf93e5b8e1fa9f71bffc14c9e7a681608e50c0ee9ce1f620`.
API code_commit/dataset_version are null; base commit plus this working diff
identify the tested source, rather than treating missing provenance as a version.

The window was investigated on this failure. This is a regression repair, not a
held-out registration benchmark or evidence of improved detector precision.

Changed/staging allowlist:

- `src/astrotrace/preprocessing/registration.py`
- `tests/detection/test_registration_recovery.py`
- `docs/handoffs/T13_ESA_TEST3_RECOVERY.md`

## Tests actually executed

- Full Python suite: **541 passed, 2 skipped, 6 warnings**, exit 0, 110.33s.
  This run preceded adding the second parameterized support/validation guard
  case. The final targeted registration-recovery run covers both guard cases:
  **12 passed**, 6.22s. Another registration/recovery run: **48 passed, 2 skipped**.
- Real pipeline regression: test/3, test/138 and test/1003 all succeed. Synthetic
  transform direction, inverse, finite diagnostics, no file/truth access and
  input preservation are checked; rotated and unrelated frames remain rejected.
- Frontend tests: **119 data tests + 19 overlay tests passed**. TypeScript and
  Vite production build passed. Existing landing-page chunk >500kB advisory remains.
- `verify_final_http.py`: **9 genuine HTTP jobs** with expected outcomes passed:
  synthetic demo, synthetic one-object upload, multi-object upload, supported
  empty, unsupported bright input, uncertain noise, rotated registration failure,
  ESA train/84 and expected train/438 failure. Upload bounds and CORS passed.
- Browser upload of the actual five test/3 PNGs: **succeeded**, genuine job
  `job-8752af54de1e474d97c902cf8a574665`; actual result saved separately.
  18 detections, 17 tentative/short track records, **0 confirmed/fitted tracks,
  0 forecasts**. The default supported view hides unverified candidates.
- Optional candidate view: 18 accumulated observed dots, 1 connected observed
  segment, 2 current-frame boxes at frame 5, no invented prediction. Frame
  navigation and native overlay alignment at 225% zoom plus keyboard pan passed:
  image and SVG x/y/width/height agree within 0.01 screen pixels.
- Browser PDF download: real `%PDF-1.4`, 5,404 bytes; current result and selected
  track 0003. Browser console errors/warnings: none captured.
- Initial browser attempt overlapped the single-worker HTTP regression job and
  correctly returned HTTP 429 queue capacity. After that job completed, explicit
  retry succeeded. No queue limit was increased and no error was concealed.

Python warnings: existing Starlette/httpx and HTTP 422 deprecations plus the
intentional invalid FITS BLANK fixture warning. Two optional snapshot tests skipped.
One separate collection-only command piped through PowerShell `Select-Object`
closed its output early and produced an output-flush error; full-suite exit was 0.

## Reproduce and inspect

```powershell
Set-Location E:\Fusion
& .\.venv\Scripts\python.exe -m pytest tests\detection\test_registration_recovery.py -q
& .\.venv\Scripts\python.exe -m pytest -q
Set-Location E:\Fusion\frontend
node tests/run-data-tests.mjs
node tests/overlay.test.mjs
npm run build
Set-Location E:\Fusion
$t13HttpOutput = '.cache/registration-followup/http_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
& .\.venv\Scripts\python.exe -I scripts\verify_final_http.py --url http://127.0.0.1:5173 --origin http://127.0.0.1:5173 --output $t13HttpOutput
```

When the relevant ports are free, separate terminals:

```powershell
Set-Location E:\Fusion
.\scripts\Start-Backend.ps1
```

```powershell
Set-Location E:\Fusion
.\scripts\Start-Frontend.ps1
```

Website: `http://127.0.0.1:5173/#/workbench`. Replace images with test/3 `1.png`
through `5.png`, confirm numeric order, Analyze. Analysis should complete; enable
Show unverified candidates only to inspect unsupported short candidates.
Download Report produces a PDF. No reliable forecast exists for this sequence.

Ignored local evidence under `.cache/registration-followup/`: original failed
native frames and diagnostics, recovered result/diagnostics/manifest JSON,
`esa-test-3-success.png`, `esa-test-3-candidates.png`, `esa-test-3-report.pdf`,
HTTP receipt and full-suite logs. Preserve historical evidence and datasets.

At verification, backend listener PID 1956 on 8000 descends from
`E:\Fusion\.venv\Scripts\python.exe` PID 19200, launcher PID 4356.
Only the verified old local backend was restarted to load the correction.
Existing original Vite PID 19296 on 5173 stayed running. Both use original
E:\Fusion sources. No Railway/Vercel change was made.

## Accuracy and remaining limits

CV-T04 OpenCV remains the live detector; existing experimental YOLO is preserved
and not retrained/selected here. Heuristic quality was not inflated. Seventeen
short candidate records do not mean seventeen real objects. No labels entered
registration/inference; test/3 has not supplied labeled precision/recall evidence.
Historical CV-T04 precision 39.24% / recall 58.72% is not a new result for this fix.

ESA train/438 still fails frames 3/4 under the translation-only policy. Large
rotations, changing streak morphology, sparse/repeated features and poor overlap
can still fail safely. Jobs remain in memory; restart loses prior job URLs.

Recommended next task: evaluate the current CV-T04 and existing YOLO outputs on
a frozen, separately labeled real validation set, including star-streak and
persistent-artifact negatives. Select changes using development data and report
held-out precision/recall, false positives and track support. Do not increase
scores or relax registration/tracking gates to make the UI appear accurate.

Publication: only the three allowlisted files belong to this correction. Existing
Dockerfile, deployment docs, .railwayignore, Ultralytics and Vercel launcher edits
are unrelated and must remain excluded. User authorized publication to Subham;
main/development and remote hosting are outside this change.
