# OrbitTrace V1 — Railway backend

Task: T19 release/deployment integration. Verified 10 October 2026 (Asia/Calcutta). Source root `E:\Fusion`, branch `Subham`, base commit `b07fe9873a39cd8897374078a7729cb4a50d6737`. No source was staged, committed or pushed. No frontend deployment or Azure operation occurred.

## Actual deployment

**DEPLOYED: Linux build, startup and nine genuine public HTTPS analysis jobs passed.**

- API origin: **https://orbittrace-api-production.up.railway.app**
- Health: https://orbittrace-api-production.up.railway.app/api/health
- Interactive API: https://orbittrace-api-production.up.railway.app/docs
- OpenAPI: https://orbittrace-api-production.up.railway.app/openapi.json
- Project: `orbittrace-v1` (`8eb7c103-8fd3-43f5-9340-49b8903a9f2b`).
- One service: `orbittrace-api` (`70f42d50-cd01-4b3a-8737-f6f8ef9ceced`).
- Environment: `production` (`dc1805f9-1687-4dc3-a0e0-f33d304a3965`).
- Successful deployment: `eec949af-750a-464a-be2d-9b579593705d`.
- Linux amd64 image digest: `sha256:19a096557183fd2a471d17c78bf375877db9c54033495de733921072a51f422d`.
- Live service inspection reports region **sfo**, one configured/running replica. The initial legacy region setting did not change the actual region; report the inspected region, not the requested Singapore value. No regional switch was made after live verification.

No database, volume, frontend, separate registry or additional backend service was created. Existing Railway projects were preserved. The original local demo remains on frontend 5173/backend 8000; temporary backend 8031 was stopped after testing.

## Account and payment boundary

The human completed official Railway browser login. Read-only account queries confirmed `isVerified=true`, `isTrialing=true`, **7 trial days remaining**, approximately **$4.53 remaining usage credit**, and **no default payment method**. The API plan label is `HOBBY` with trial access; this does not mean this task activated a paid subscription. The user explicitly approved trial-only creation/public exposure. No plan upgrade or payment method was added.

Credits are shared with the account's existing projects. Trial access/credit can run out; this is not a promise of permanent free hosting. Do not upgrade automatically. Official trial resources are limited to 1 GB RAM and shared CPU; actual per-service limits were explicitly set and inspected. See [Railway trial](https://docs.railway.com/pricing/free-trial).

Published usage prices are $10/GB-month RAM, $20/vCPU-month CPU and $0.05/GB egress. Approximately 0.13–0.20 GB steady memory alone would use about $1.30–$2.00/month of credit, before CPU/egress and existing projects; this is an estimate, not a billing guarantee. A full-resource workload can consume the remaining credit much faster. See [Railway pricing](https://docs.railway.com/pricing). No workspace-wide usage limit was changed because it would also affect unrelated projects.

## Source and upload safety

The existing root Dockerfile is reused. Build from `E:\Fusion`, not its backend subdirectory: the application installs `app`, `orbittrace` and `astrotrace` from the root Python package. Linux dependency wheels and package installation passed in Railway's actual build; Docker Desktop's local engine remains unavailable.

`.railwayignore` restricts source upload to the root Docker/package files, `backend/app`, `backend/orbittrace`, the production dependency list and `src/astrotrace`. The normal `.gitignore` remains enabled. **Never use `--no-gitignore`.** The CLI uploads filesystem source, including untracked files; it does not require a Git commit. CLI 5.64.2's official upload implementation was inspected to verify its filesystem walk and custom ignore handling.

The local audit found **67 files, 253,446 bytes, including 17 required untracked files**. SHA-256, size and tracked status are recorded in `.cache/railway-v1/upload-manifest.json`. Datasets, checkpoints, experiments, frontend files, caches, credentials and generated outputs are excluded. The successful Linux API proves required unpublished modules were installed.

Railway CLI 5.64.2 (ISC license) is installed only under `.cache/railway-v1/cli`, with the official binary from `github.com/railwayapp/cli/releases`. `scripts/Railway.cmd` supplies a simple launcher. Npm reported deprecated transitive packages; the reviewed official postinstall downloaded the binary. Authentication remains in Railway's normal credential storage, outside Git. Do not print/upload credential files.

Files created in this task:

- `.railwayignore`
- `backend/app/core/server.py`
- `scripts/Railway.cmd`
- `scripts/audit_railway_upload.py`
- `tests/api/test_container_server.py`
- `tests/api/test_frame_retention.py`
- `docs/RAILWAY_DEPLOYMENT.md`
- `docs/VERCEL_HANDOFF.md`

Existing files changed:

- `Dockerfile`: installed Python entry point reads Railway `PORT`; health check reads the same port.
- `backend/app/core/deployment.py`: validated decoded-frame retention budget.
- `backend/app/services/job_manager.py`: consume the budget; evict completed jobs before reserving a new job.
- `scripts/verify_integration_http.py`, `scripts/verify_final_http.py`: record actual HTTP submission/poll timing.

No frontend source, shared contract, detection, registration, tracking or trajectory algorithm changed. The Dockerfile before this task is backed up in `.cache/railway-v1/Dockerfile.before`. Initial/final Git states and all deployment evidence are in `.cache/railway-v1`; these are excluded from Git and Railway upload.

## Runtime settings actually applied

| Setting | Actual value |
| --- | --- |
| Root/Dockerfile | `/`, `Dockerfile` |
| Startup | `python -I -m app.core.server` → exec one Uvicorn worker as PID 1 |
| Bind | `0.0.0.0:$PORT`, current `PORT=8000` |
| Replicas | One configured, one running |
| CPU override | 1 vCPU maximum, shared trial CPU |
| Memory override | 1,000,000,000 bytes inspected through the API |
| Health check | `/api/health`, timeout 120 seconds |
| Restart | `ON_FAILURE`, maximum 2 retries |
| Serverless sleep | Disabled: restarts lose in-memory jobs |
| Public mode | `ORBITTRACE_PUBLIC_MODE=1` |
| CORS | `ORBITTRACE_CORS_ORIGINS=https://orbittrace-api-production.up.railway.app` |
| Decoded-frame retention | `ORBITTRACE_FRAME_RETENTION_MIB=128` |
| CPU libraries | `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1` |

CV-T04 is the CPU detector; T13 registration, Member 3 association and image-plane fitting are included. No YOLO weights/Torch/GPU runtime were deployed. Core scientific dependencies are pinned in `backend/requirements.production.txt`; Python 3.12 slim and headless OpenCV work in the actual Linux image. FITS/Astropy is optional local functionality and is not a public upload route.

Jobs are in memory, one active job, at most 100 retained job records and 128 MiB of decoded-frame storage on Railway. Completed jobs are evicted to maintain the budget; eviction/restart means later frame/result retrieval can return 404. No persistent temporary image directory or disk volume is used; uploads and retained frames are memory bounded. Original local retention defaults remain 500 MiB unless explicitly configured.

Upload bounds remain exactly five grayscale PNG/JPEG files, 10 MiB/file, 50 MiB aggregate, 51 MiB streamed request and 4 million decoded pixels/frame. Reducing retained history did not lower input limits or alter scientific functionality. Maximum-size decoded uploads were not stress tested on Railway, so no blanket OOM guarantee is made.

## Actual verification

| Check | Result |
| --- | --- |
| Final local full Python suite | **529 passed**, 6 known warnings, 0 failed/skipped |
| Targeted startup/CORS/retention/API tests | **43 passed**, 3 warnings |
| Frontend regressions | **104 + 19 passed**, source unchanged |
| TypeScript/Vite build with actual Railway origin | Passed locally; large landing chunk warning; not deployed |
| Railway Linux Docker build | Successful; pinned dependencies installed; image digest above |
| Cloud startup/health | PID 1, one worker, health check successful, deployment SUCCESS |
| Public HTTPS HTTP suite | **9 fresh jobs**, 62.1436 seconds overall, exit 0 |
| API/frames/diagnostics/exports | Health, docs, OpenAPI, uploads, polling, schema validation, native image identity, manifests, JSON/CSV passed |
| Upload rejection | Four files 422, invalid media 422, >10 MiB file 413 |
| CORS | Self-origin preflight 200; unknown Vercel origin must be added before browser use |

Actual public jobs:

| Sequence | Detections per frame | Tracks/fits or expected error | Submission seconds | Poll/result window seconds |
| --- | --- | --- | --- | --- |
| Synthetic demo | 1,1,1,1,1 | 1 confirmed / 1 fit | 0.268 | 0.534 |
| Multi-object counts-change | 5,3,4,5,5 | 5 confirmed / 5 fits | 0.684 | 0.525 |
| Empty targets | 0,0,0,0,0 | 0 tracks / 0 fits, succeeded | 0.423 | 0.505 |
| Daylight-like | — | unsupported_observation | 0.430 | 0.520 |
| Noise-only | — | uncertain_observation | 0.418 | 0.533 |
| Rotation fixture | — | registration_failed | 0.292 | 0.578 |
| ESA train/84 | 7,7,6,8,6 | 31 track records / 0 confirmed / 0 fits | 1.011 | 0.893 |
| ESA train/438 | — | registration_failed | 0.953 | 0.861 |
| One-object five-image upload | 1,1,1,1,1 | 1 confirmed / 1 fit | 1.216 | 0.856 |

The errors above are expected acceptance cases, not failed verification. Successful results validated AnalysisResult 0.1.0 and finite values, preserved image bytes/native dimensions and unknown upload timestamps. Unlabeled uploads have `metrics=null`. Synthetic multi-object returns ten forecast points; ESA84 has no fitted forecasts. Candidate identity/orbit/physical speed remain unverified. Timing includes network, polling and result fetches (the final one-object window also includes diagnostics); it is not isolated detector runtime.

Evidence: `.cache/railway-v1/http-public/receipt.json`, `*_result.json`, `*_diagnostics.json`, original/copy input PNG folders, `http-public.log`, `http-public-timing.json`, `build-final.log`, `startup.log`, `runtime-after-tests.log`, `live-settings.json`, `services-live.json`, and `deployments-final.json`.

Memory: local startup was approximately 99 MiB working set; Windows sample high-water value was 138 MiB. Railway startup samples were about 126 MB; the final sampled maximum/current memory was **200.47 MB** after public testing. The recorded CPU sampled maximum was **0.0359 vCPU**. These are sampled platform values, not a guaranteed instantaneous process peak; the window includes idle/startup periods. SSH process high-water reading was unavailable because no SSH key was configured; no key was created. Evidence: `memory-samples.json` and `cloud-metrics-final.json`. No OOM/restart occurred in tested workloads.

A new retention test initially used numbers below the eviction boundary; its fixture was corrected and targeted/full suites passed. Existing warnings are Starlette/httpx and HTTP 422 deprecations plus deliberate invalid FITS metadata. A read-only regional-field query was rejected because that output field is not in the live schema; the query was corrected. No backend build/runtime defect remains in the tested workflow.

## Reproduction, redeployment and logs

PowerShell, original root only:

```powershell
Set-Location E:\Fusion
git branch --show-current
E:\Fusion\scripts\Railway.cmd --version
E:\Fusion\scripts\Railway.cmd login
E:\Fusion\scripts\Railway.cmd link --project 8eb7c103-8fd3-43f5-9340-49b8903a9f2b --service orbittrace-api --environment production
.\.venv\Scripts\python.exe -I scripts/audit_railway_upload.py
# After reviewing changes and available trial credit:
E:\Fusion\scripts\Railway.cmd up --service orbittrace-api --environment production --detach --json
E:\Fusion\scripts\Railway.cmd deployment list --service orbittrace-api --environment production --json
E:\Fusion\scripts\Railway.cmd logs --service orbittrace-api --environment production --build --lines 80
E:\Fusion\scripts\Railway.cmd logs --service orbittrace-api --environment production --lines 80
E:\Fusion\scripts\Railway.cmd metrics --service orbittrace-api --environment production --since 10m --cpu --memory --json
# Use a new output directory; verifiers preserve previous evidence.
.\.venv\Scripts\python.exe -I scripts/verify_final_http.py --url https://orbittrace-api-production.up.railway.app --origin https://orbittrace-api-production.up.railway.app --output .cache/railway-v1/http-public-rerun
```

`--detach` returning successfully means queued, not healthy; inspect the deployment until SUCCESS and rerun full HTTPS analysis checks. Redeploying restarts the single backend and loses in-memory jobs. Export reports first. `up` uploads reviewed local unpublished source; no Git publication is needed. Do not recreate the project/service or use `--new` on routine redeployment.

No legacy `railway.toml`/`railway.json` was introduced: current Railway docs mark legacy Config as Code deprecated for new services. The Dockerfile and explicit inspected service settings are used. See [CLI upload behavior](https://docs.railway.com/cli/up) and [configuration reference](https://docs.railway.com/config-as-code/reference).

## Stop/remove only this backend

Not executed: these are instructions for the owner when the demo is finished. The backend remains live now. Export any reports first, then remove this deployment to stop compute/credit consumption:

```powershell
Set-Location E:\Fusion
E:\Fusion\scripts\Railway.cmd down --project 8eb7c103-8fd3-43f5-9340-49b8903a9f2b --service 70f42d50-cd01-4b3a-8737-f6f8ef9ceced --environment dc1805f9-1687-4dc3-a0e0-f33d304a3965
E:\Fusion\scripts\Railway.cmd service list --json
```

Verify no running replica/deployment remains. No volume/database was created for this backend. If permanently removing the dedicated project is desired, inspect it contains only `orbittrace-api`, then run `E:\Fusion\scripts\Railway.cmd project delete --project 8eb7c103-8fd3-43f5-9340-49b8903a9f2b` and confirm in the CLI. Do not delete the account's other projects. No stop/deletion command was run against Railway, and no paid plan should be activated without explicit approval.

## Remaining dependencies

- Manual Vercel deployment and exact production-origin CORS registration: see `docs/VERCEL_HANDOFF.md`.
- Latest frontend changes are unpublished; a Vercel GitHub import of the existing Subham branch cannot automatically include local uncommitted files. Review/publication requires separate approval, or the owner can manually upload/build the current frontend.
- In-memory jobs, one active job, trial expiry, translation-only registration, absent upload timestamps and maximum-image RAM uncertainty remain limitations. A persistent-artifact false confirmed track is an existing scientific limitation; it was not hidden or rewritten.
- Recommended next task: publish/review the existing frontend on Subham with approval, manually deploy it to Vercel, add its exact origin, and run the complete cross-origin browser workflow. No full hosted website/browser visualization success is claimed yet.
