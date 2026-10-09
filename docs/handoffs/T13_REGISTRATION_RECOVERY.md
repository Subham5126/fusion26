# T13 — Verified registration recovery for real uploads

Base commit: `e9b308f`, branch `Subham`. Implemented and tested locally on
2026-10-10 in the original `E:\Fusion`. No shared schema, detector, tracker,
trajectory, frontend or dependency changes. Public contract remains 0.1.0.

## Reported sequence and actual failed input

The user identified `data/raw/SpotGEOv2/test/138`. All five native images in that
folder passed the original registration policy and a fresh HTTP upload before
this fix. The latest failed upload, job
`job-fc53599e69194e1fb9f2d00ca80243a4`, was retrieved from the local backend before
restart. Decoded pixel hashes of all five frames match `test/1003/1..5.png`, not
138. No dataset files or annotations were modified. Inference uses image arrays
only; ground truth is not read.

For 1003, frames 0..3 aligned successfully; frame 4 failed with only seven verified
matches. Its coarse phase correlation found the wrong streak at reference-to-raw
shift `(34.52, -90.17)` rather than approximately `(-197.21, 132.52)` pixels.
Registration failure correctly blocked tracking; the UI was displaying the real
backend error.

## Implementation and coordinates

Changed files (the complete publication allowlist):

- `src/astrotrace/preprocessing/registration.py`
- `src/astrotrace/preprocessing/REGISTRATION.md`
- `tests/detection/test_registration_recovery.py`
- `docs/handoffs/T13_REGISTRATION_RECOVERY.md`

`register_sequence(frames, config=None)` keeps the original direct frame-0
alignment first. On failure, it can make one bounded attempt using the nearest
previous successfully aligned frame. That adjacent pair must independently pass
the original phase, flow, fit and reserved-point validation checks. Its composed
translation provides only the initial optical-flow guess for a new direct fit
between the current native image and frame 0. The returned matrix is that fresh
direct fit, never the composed matrix.

Successful original fits still use a 25px flow window. The retry uses a declared
21px window. Final acceptance remains at least 12 fit inliers, 60% fit consensus,
four reserved validation inliers, 60% validation consensus, validation-inlier
RMSE <=0.8px, 20% spatial coverage on both axes, 45% overlap and <=250px shift.
A wrong global phase seed may be replaced by the independently verified neighbor
seed; final support/residual thresholds are not reduced. Each failing frame gets
at most one adjacent pair and one direct retry, adding bounded CPU work.

Supplemental diagnostics add `initialization`, `seed_frame_index`,
`flow_window_px`, and `direct_failure_reasons`. Shared AnalysisResult is unchanged.
`raw_to_reference` still maps native current-frame pixels to `reference_frame_0`;
`reference_to_raw` is its inverse. Failed usable matrices remain null.

Rollback is available through `RegistrationConfig(neighbor_retry=0)` or
`register_sequence(frames, {'neighbor_retry': 0})`. `neighbor_retry` accepts
integer 0/1; `retry_flow_window_px` accepts odd integers 15..35. Normal direct fits
are unaffected by the retry setting.

## Actual verification

- New recovery tests: 9 passed. These cover a deliberately wrong coarse seed,
  independent final coordinates, inverse round trip, finite JSON, unmodified raw
  images, forbidden file access during registration, bounded configuration,
  rejection of rotated/unrelated final frames, and the actual current pipeline
  using real 138/1003 images. Real data tests skip only if the optional files are
  absent; both ran locally.
- Targeted registration/robustness/pipeline suite: 114 passed, 2 skipped in 75.59s.
- Full Python suite: **539 passed, 2 skipped, 6 warnings in 151.69s**. Skips are
  historical Member 3 snapshot checks with unavailable optional configuration;
  actual current tracker compatibility ran. Warnings concern Starlette/httpx,
  deprecated 422 naming, and an intentionally invalid FITS BLANK test fixture.
- `scripts/verify_final_http.py` exited 0 against the live Vite proxy on 5173.
  Nine actual jobs exercised synthetic demo/upload, changing multi-object counts,
  valid empty results, unsupported daylight, uncertain noise, deliberate rotated
  registration failure, ESA train/84 and ESA train/438. Expected invalid input
  errors remain errors; train/438 still fails frames 3/4. Count/type/byte limits,
  CORS, result/diagnostics/frame retrieval and exports were checked.
- Actual browser uploads of exactly five original images succeeded for both
  test/138 and test/1003. Frame navigation and real detection boxes were inspected.
  Captured browser console errors: none. No frontend source changed this turn;
  the previous frontend suite/build results were 136 passed/build passed, not a
  newly run frontend suite.

1003 frame 4 recovered with 34 matches, 26 fit inliers and eight reserved
validation inliers, validation RMSE **0.6502514px**, raw-to-reference translation
`(+197.2122803, -132.5198059)`. Diagnostics identify seed frame 3 and original
`insufficient_verified_matches`. Direct-only rollback still rejects this frame.

Browser/API results:

| Sequence | Browser job | Detections | Supported tracks | Fitted trajectories |
| --- | --- | ---: | ---: | ---: |
| test/138 | job-410ae607b53e4f90b9586fca7c1468f9 | 7 | 0 | 0 |
| test/1003 | job-e9b4897bb3ed49e6ac93ba79278840c1 | 23 | 0 | 0 |

The actual 1003 result records input SHA-256
`a902f90d423452b662f21c4b234a1905ad9349c620c5ae17215d231cab5b74de`
and config SHA-256
`887caab9290c6fceaf93e5b8e1fa9f71bffc14c9e7a681608e50c0ee9ce1f620`.
Runtime provenance reports `code_commit: null`; the base Git commit above was
read from Git, not inferred from that field.

These contain one-observation candidate track records. This fix establishes
registration success, not target accuracy or successful repeated associations.
The UI shows no fabricated forecast/path. Enable **Show unverified candidates**
to inspect the actual raw detections when supported tracks are absent.

Ignored local evidence is under `.cache/registration-fix/`: `user-job/` contains
the failed uploaded frames/diagnostics, `browser-138-*.json` and
`browser-1003-*.json` contain actual API outputs, `http-regression/receipt.json`
contains the nine-job checks, and `test-138-success.png` /
`test-1003-recovered.png` show browser success. No raw data or generated evidence
belongs in this change's Git staging allowlist.

## Reproduce in Windows PowerShell

```powershell
Set-Location E:\Fusion
& .\.venv\Scripts\python.exe -m pytest tests/detection/test_registration_recovery.py -q
& .\.venv\Scripts\python.exe -m pytest -q
```

When ports are free, start the existing launchers in separate terminals:

```powershell
Set-Location E:\Fusion
.\scripts\Start-Backend.ps1
```

```powershell
Set-Location E:\Fusion
.\scripts\Start-Frontend.ps1
```

Run HTTP checks against those existing servers (a fresh evidence directory):

```powershell
Set-Location E:\Fusion
& .\.venv\Scripts\python.exe -I scripts\verify_final_http.py --url http://127.0.0.1:5173 --origin http://127.0.0.1:5173 --output .cache\registration-fix\http-reproduced
```

Open `http://127.0.0.1:5173/#/workbench`, select `1.png` through `5.png` from
`E:\Fusion\data\raw\SpotGEOv2\test\138` or `test\1003`, confirm their numeric
order, then Analyze. Enable the candidate toggle to inspect detections; select
each frame to see the native boxes. PDF/JSON/CSV controls remain available.

After restart, the verified local listeners are backend PID 22772 on 8000
(launcher PID 27760) and unchanged Vite PID 19296 on 5173. Both launch from
`E:\Fusion`. Runtime logs are `.cache/registration-fix/backend.*.log`.

## Remaining limitations and next dependency

Translation-only registration still rejects unsupported rotations and unresolved
train/438 frames rather than returning identity. No identity fallback or tracking
across failed registration was introduced. Jobs are held in memory; restarting
the backend clears old jobs. A successful registration does not guarantee
repeated target detections or a supported trajectory, as 138/1003 demonstrate.
Next CV/tracking task: evaluate candidate continuity on a labeled real validation
set before changing association gates or asserting accuracy. Public Railway
deployment is not verified by these local tests; Git publication does not itself
prove that the running public service uses this revision. Preserve unrelated
Docker/deployment, Ultralytics and CLI changes outside this allowlist.
