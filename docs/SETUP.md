# Setup and exact reproduction from E:\Fusion

Verified Windows, Python3.12.14, Node24.19.0/npm11.17.0. The existing original
.venv was updated from verified locks and root installed editable. No environment,
node_modules, datasets or build/report trees were copied from another workspace.
Astropy is installed for the FITS tests; HTTP uploads remain PNG/JPEG only.
Torch/Ultralytics remain in the existing optional .cache/cv_t15/venv.

Installation only when needed:
```powershell
Set-Location E:\Fusion
& .\.venv\Scripts\python.exe -m pip install -r backend\requirements.lock.txt -r backend\requirements-astronomy.lock.txt 'setuptools==84.0.0'
& .\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
& .\.venv\Scripts\python.exe -m pip check
Set-Location frontend
npm ci
```
Do not reinstall npm dependencies while a Vite/esbuild process uses this project's
node_modules; the initial npm ci failed with EPERM from the old viewer. On the
approved continuation its PIDs were already absent and all ports free, so no process
was terminated. npm ci then passed. The lockfile is preserved from the latest design.

Exactly two main startup sequences:
Terminal1: `Set-Location E:\Fusion; .\scripts\Start-Backend.ps1`
Terminal2: `Set-Location E:\Fusion\frontend; ..\scripts\Start-Frontend.ps1`
Backend8000, frontend5173, Vite /api proxy8000. No fixture-only API replacement.
The services already run; guards refuse duplicates. In-memory jobs expire on restart.
Session PIDs/logs: .cache/original-consolidation-20261010/services.json.

Actual tests, with a NEW report output folder for each HTTP/scientific rerun:
```powershell
Set-Location E:\Fusion
$env:CV_TRACK_SOURCE='E:\Fusion\data\raw\SpotGEOv2'
$env:CV_T06_REAL_SOURCE=$env:CV_TRACK_SOURCE
$env:CV_T06_TRACKING_SNAPSHOT='E:\Fusion\.cache\original-consolidation-20261010\tracking-snapshot'
# Snapshot files are byte-identical copies of this checkout's unchanged Member3
# modules, used only by the older explicit snapshot tests.
& .\.venv\Scripts\python.exe -m pytest -q -rs
& .\.venv\Scripts\python.exe -I scripts\verify_cv_track_01.py --esa data\raw\SpotGEOv2 --output artifacts\reports\original_consolidation\cv_recheck
& .\.venv\Scripts\python.exe -I scripts\verify_final_http.py --url http://127.0.0.1:5173 --esa data\raw\SpotGEOv2 --output artifacts\reports\original_consolidation\http_recheck
Set-Location frontend
node tests/run-data-tests.mjs
npm run build
node tests/verify-live-results.mjs ../artifacts/reports/original_consolidation/http_recheck
node tests/verify-t08-http.mjs ../artifacts/reports/original_consolidation/http_recheck http://127.0.0.1:5173
```
T15 report was freshly generated with this checkout's scripts/t15_ablation.py.
If absent, run `& .\.venv\Scripts\python.exe -I scripts\t15_ablation.py` first;
the report-consistency test otherwise skips rather than inventing evidence.

View actual outputs:
```powershell
Start-Process 'http://127.0.0.1:5173/#/workbench'
Invoke-Item E:\Fusion\artifacts\reports\original_consolidation\browser\multi-final.png
Invoke-Item E:\Fusion\artifacts\reports\original_consolidation\cv_track_01\index.html
Get-Content E:\Fusion\artifacts\reports\original_consolidation\http_live\receipt.json
Get-Content E:\Fusion\artifacts\reports\original_consolidation\http_live\synthetic-upload_result.json
```
Upload1.png through5.png from http_live/counts-change or http_live/esa-train-84,
confirm order, Analyze local images, choose frame5. Geometry is native image pixels;
accepted inverse T13 transforms project reference forecasts onto the displayed raw
frame. Solid filled=observed; dashed hollow=forecast; neon=current detection.
Unknown uploaded timestamps remain null. ESA84 has no confirmed forecast.

Optional existing YOLO smoke (no new training/production route):
```powershell
Set-Location E:\Fusion
$env:PYTHONPATH='E:\Fusion;E:\Fusion\backend'
$env:CV_T15_CACHE='E:\Fusion\.cache\cv_t15'
& .\.cache\cv_t15\venv\Scripts\python.exe -m experiments.yolo.infer --weights artifacts/reports/cv_t15/train_gpu/run/weights/best.pt --images .cache/original-consolidation-20261010/yolo-smoke-images.txt --output artifacts/reports/original_consolidation/yolo_recheck --device 0 --batch 4 --conf 0.25
```
The five unrelated images are an inference smoke, not a motion or identity test.
