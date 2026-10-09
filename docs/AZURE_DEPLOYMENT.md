# OrbitTrace V1 Azure deployment preparation

Task: T19 release/deployment integration. Base commit: `b07fe9873a39cd8897374078a7729cb4a50d6737`, branch `Subham`. All project source and evidence remain in `E:\Fusion`. No staging, commit, push, merge, worktree or cloud deployment occurred.

## Actual state — 2026-10-10

**PARTIAL: local preparation tested; cloud deployment cancelled before resource creation.** The user instructed cancellation if payment is needed. The proposed always-on Container Apps backend and Basic registry incur recurring charges. Student credit coverage was not verified; no claim of free hosting was made.

- Azure CLI 2.91.0 installed from Microsoft's official winget/MSI distribution (MIT). The user completed Microsoft's sign-in flow.
- Active subscription: Azure for Students, enabled. Sensitive subscription/tenant identifiers and authentication tokens are omitted.
- Read-only permission enumeration returned subscription-wide actions without exclusions. Policy and service quotas still apply.
- Explicitly approved registration requested for Microsoft.App, Microsoft.Web, Microsoft.ContainerRegistry and Microsoft.ManagedIdentity. Registration is a subscription configuration change, not an application hosting deployment.
- Before registration, Container Apps managed-environment quota was zero in Central India, East US 2, East Asia and Southeast Asia. After registration, Central India reports **one** allowed environment, zero used. No quota increase was requested.
- No hosting resource was created by this task. Actual frontend Azure URL: **none**. Actual backend Azure URL: **none**. Planned names below are not deployed resources.
- Current sanitized Azure access snapshot: `.cache/azure-v1/azure-access.json`. Authentication remains in Azure CLI's standard user credential store, outside Git.
- Original working demo remains `http://127.0.0.1:5173/`, backend `http://127.0.0.1:8000/`. Temporary separate-origin validation used frontend 5192 and backend 8030; these are local test services, not Azure URLs.
- Final audit verified **zero resource groups and zero resources**. Temporary 8030/5192 test sessions were stopped with Ctrl+C after testing; original backend/frontend remained running.

## Files changed by this deployment preparation

Created:

- `Dockerfile`
- `.dockerignore`
- `backend/requirements.production.txt`
- `backend/app/core/deployment.py`
- `frontend/.env.example`
- `frontend/src/api/baseUrl.ts`
- `frontend/src/vite-env.d.ts`
- `frontend/public/staticwebapp.config.json`
- `frontend/tests/deployment.test.ts`
- `tests/api/test_deployment.py`
- `scripts/Azure.cmd`
- `scripts/azure_prices.py`
- `docs/AZURE_DEPLOYMENT.md`

Modified existing working files, including previously untracked T19/T20 files:

- `backend/app/main.py`: explicit deployment CORS origins, preserving local defaults.
- `backend/app/api/analyze.py`: public invalid manifests no longer echo validation inputs.
- `backend/app/services/job_manager.py`: public unexpected errors omit internal exception details.
- `frontend/src/api/client.ts`, `frontend/src/api/transport.ts`: use configured API origin for uploads, JSON, diagnostics and binary frames.
- `frontend/src/components/workbench/LocalWorkbench.tsx`: exports use the same configured API origin.
- `frontend/tests/run-data-tests.mjs`: include deployment tests and define the test environment.
- `scripts/verify_integration_http.py`, `scripts/verify_final_http.py`: accept the actual frontend `--origin` for cross-origin HTTP verification.

No shared schema, detector, registration, tracking or trajectory algorithms changed. Pre-edit backups and the initial Git status are in `.cache/azure-v1/before` and `.cache/azure-v1/git-status-before.txt`. All earlier uncommitted work was preserved. This list is a deployment delta; a clean publication also needs the existing T19/T20 foundation and its reviewed allowlists.

## Runtime configuration

Backend image uses Python 3.12 slim, headless OpenCV, CPU dependencies, non-root UID 10001 and a Docker health check. It installs the root Python package so `app`, `orbittrace` and `astrotrace` imports do not rely on Windows working directories. The image build context excludes datasets, experimental checkpoints, environments, Git, fixtures and secrets. No dataset or model download runs at startup. CV-T04 remains the deployed detector candidate; experimental YOLO is excluded.

Startup:

```powershell
python -I -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log
```

Production backend environment:

- `ORBITTRACE_PUBLIC_MODE=1`
- `ORBITTRACE_CORS_ORIGINS=https://<actual-static-web-app-hostname>` — required, explicit HTTPS origin; no wildcard or credentials. Invalid configuration fails startup.
- `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`.

Frontend build environment:

- `VITE_API_BASE_URL=https://<actual-container-app-hostname>` — actual HTTPS origin, no path/query/credentials. An empty value deliberately preserves the local Vite `/api` proxy; it must not be left empty for a separately hosted Azure frontend.
- `SWA_CLI_DEPLOYMENT_TOKEN` is a temporary deploy-process environment secret only. Never print it, put it in Git, pass it in a public command example or send it in chat.

Native-image endpoints, result/diagnostics and JSON/CSV exports all use this API origin. Schema 0.1.0, raw-frame detection boxes, reference-coordinate tracks, inverse registration transforms and predictions/observations remain unchanged.

Existing upload bounds remain exactly five grayscale PNG/JPEG frames, 10 MiB/file, 50 MiB aggregate, 51 MiB streamed request and 4 million decoded pixels/frame. Existing jobs are held in memory: one analysis executor, 100 retained completed jobs and 500 MiB decoded-frame retention. Restart loses jobs. The proposed deployment therefore uses one worker and min/max one replica; persistent job storage is a V2 dependency.

## Actual verification

Evidence is stored under `.cache/azure-v1`, ignored by Git.

| Operation | Result | Evidence |
| --- | --- | --- |
| Full Python suite | 511 passed, 6 warnings; collection preceded the final additional wildcard case | `python-tests.log` |
| Final deployment-specific tests | 12 passed, 2 warnings, including wildcard CORS rejection and error confidentiality | `deployment-tests.log` |
| Main frontend tests | 104 passed, no failures/skips | `frontend-tests.log` |
| Retained overlay tests | 19 passed, no failures/skips | `overlay-tests.log` |
| TypeScript + Vite production build | Passed; large landing-page chunk warning | `frontend-build.log` |
| Built frontend with separate API origin | Build passed against loopback backend 8030 | `separate-origin-build.log` |
| Actual local HTTP | Nine fresh jobs and CORS, uploads, result schema, native frames, diagnostics, manifests and exports verified | `http-tests.log`, `http-separate-origin/receipt.json` |
| Actual local browser | Compiled frontend 5192 submitted five images to backend 8030; succeeded, final frame had 5 boxes, 22 observed points, 17 connecting segments and 10 predictions; exports used backend origin; zero captured warning/error logs | `local-browser.png` |
| Docker build | Failed before image build: Docker Desktop Linux engine pipe unavailable | `docker-build.log` |
| Azure image/build/startup | Not attempted; no cloud resources created | `azure-access.json` |
| Public HTTPS/browser workflow | Not run; no deployed URLs | — |

The initial deployment test fixture failed because `JobState.warnings` was omitted; the fixture was corrected and all deployment tests passed. Existing warnings concern Starlette/httpx and HTTP 422 deprecations, plus deliberate malformed FITS metadata. SWA CLI 2.0.10 (MIT) installed only under `.cache/azure-v1/swa`; npm reported deprecated transitive packages and an unapproved optional keytar install script. SWA deployment was not tested. No frontend lockfile changed in this deployment task.

Browser proof: `.cache/azure-v1/local-browser.png`, job `job-8b4d5be445f44811921d03ab6e5fbeb6`. The observed final-frame DOM reported succeeded, 5 neon boxes, 22 observed points, 17 observed segments and 10 predicted markers. Both export links pointed to backend 8030, and captured warning/error logs were empty. This verifies a local cross-origin browser workflow only, not HTTPS or Azure. Browser zoom/pan, empty/error UI and real ESA UI were previously tested for T20 but were not rerun in this deployment preparation; real ESA and empty/error cases were rerun over HTTP.

HTTP results from fresh inference:

- Synthetic upload: one detection in each of five frames, one confirmed track and fitted trajectory.
- Multi-object: detections `[5,3,4,5,5]`, five confirmed tracks and five fitted trajectories.
- Empty-target sequence: `[0,0,0,0,0]`, zero tracks/forecasts, successful result.
- ESA train/84: `[7,7,6,8,6]`, 34 detections, 31 track records, **zero fitted trajectories**; no forecast should be invented.
- Daylight-like and noise-only inputs produce explicit unsupported/uncertain job failures.
- Rotation fixture and ESA train/438 produce explicit registration failures; tracking is blocked for the sequence.
- Four files and invalid media return 422; a file over 10 MiB returns 413.

Coordinates are image-plane pixels. Candidate detections do not establish debris identity, physical speed, altitude or orbit. Uploaded timestamps remain unknown; display playback speed does not create acquisition timestamps.

## Exact local reproduction commands

Use PowerShell from the original project:

```powershell
Set-Location E:\Fusion
git branch --show-current
E:\Fusion\scripts\Azure.cmd account show --query '{name:name,state:state}' -o json
$env:CV_TRACK_SOURCE='E:\Fusion\data\raw\SpotGEOv2'
$env:CV_T06_REAL_SOURCE=$env:CV_TRACK_SOURCE
$env:CV_T06_TRACKING_SNAPSHOT='E:\Fusion\.cache\original-consolidation-20261010\tracking-snapshot'
.\.venv\Scripts\python.exe -m pytest -q -rs
.\.venv\Scripts\python.exe -m pytest tests/api/test_deployment.py -q
Set-Location E:\Fusion\frontend
node tests/run-data-tests.mjs
node --test tests/overlay.test.mjs
npm run build
```

Separate-origin test, in three terminals (do not stop the original 8000/5173 demo):

```powershell
# Terminal 1
Set-Location E:\Fusion
$env:ORBITTRACE_PUBLIC_MODE='0'
$env:ORBITTRACE_CORS_ORIGINS='http://127.0.0.1:5192'
.\.venv\Scripts\python.exe -I -m uvicorn app.main:app --host 127.0.0.1 --port 8030 --workers 1 --no-access-log
```

```powershell
# Terminal 2
Set-Location E:\Fusion\frontend
$env:VITE_API_BASE_URL='http://127.0.0.1:8030'
npm run build -- --outDir ../.cache/azure-v1/local-dist
node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 5192 --strictPort --outDir ../.cache/azure-v1/local-dist
```

```powershell
# Terminal 3; output path must be new because the verifier preserves earlier evidence
Set-Location E:\Fusion
.\.venv\Scripts\python.exe -I scripts/verify_final_http.py --url http://127.0.0.1:8030 --origin http://127.0.0.1:5192 --output .cache/azure-v1/http-reproduction
```

Open `http://127.0.0.1:5192/#/workbench`, choose the five PNGs under `.cache/azure-v1/http-separate-origin/counts-change`, confirm order and analyze. Inspect final frame for neon boxes, solid observed paths and hollow dashed forecasts. ESA images are also copied into the evidence folder for browser reproduction; original dataset remains untouched. Open `*_result.json`, `*_diagnostics.json` and `receipt.json` to inspect actual backend output. Ctrl+C stops only the temporary test servers in their terminals.

## Proposed cloud plan — NOT executed

| Planned resource | Proposed configuration |
| --- | --- |
| Resource group `rg-orbittrace-v1-261010` | Dedicated group, Central India |
| Registry `orbittracev1subham261010` | Basic, admin disabled, authenticated image access; name availability checked |
| Identity `id-orbittrace-v1` | User-assigned identity, AcrPull scoped only to this registry |
| Environment `env-orbittrace-v1` | Consumption, Central India, no Log Analytics workspace |
| Container App `orbittrace-api-v1` | HTTPS external ingress/8000, 1 vCPU/2 GiB, min=max=1, one worker, health probes |
| Static Web App `orbittrace-web-v1` | Free, East Asia; no GitHub workflow/push |

Microsoft Retail Prices API was queried for Central India; exact response is `.cache/azure-v1/retail-prices.json`. Rates checked: active CPU $0.000024/vCPU-second, idle CPU $0.000003/vCPU-second, memory $0.000003/GiB-second and Basic registry $0.1666/day. With fully unused monthly grants, a 30-day 1-vCPU/2-GiB always-on app plus registry estimates **$26.71 idle / $77.36 continuously active**, excluding requests beyond free allowance, builds, egress, taxes and other grant consumers. These are estimates, not a billing guarantee or verified student-credit balance.

Sources: [Container Apps billing](https://learn.microsoft.com/en-us/azure/container-apps/billing), [Static Web Apps pricing](https://azure.microsoft.com/en-us/pricing/details/app-service/static/), [Container Apps quotas](https://learn.microsoft.com/en-us/azure/container-apps/quotas), [managed identity image pulls](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity-image-pull), [SWA CLI deployment](https://learn.microsoft.com/en-us/azure/static-web-apps/static-web-apps-cli-deploy).

## Resuming and redeploying V2

First obtain explicit approval of recurring costs/public exposure and verify student credit if coverage matters. Do not automatically upgrade the subscription. Recheck resource names, quota, CPU allowance and current pricing. Current account permissions do not prove ACR Tasks eligibility. If source build returns `TasksOperationsNotAllowed`, fix local Docker or obtain a separately approved build path; do not silently create another chargeable service.

The following are **prepared commands, not executed or tested cloud deployment steps**. Run only after approval, and stop on the first failure. Preserve any partially created resources and report their costs; do not auto-delete or replace existing resources.

```powershell
Set-Location E:\Fusion
$rg='rg-orbittrace-v1-261010'
$acr='orbittracev1subham261010'
$envName='env-orbittrace-v1'
$apiName='orbittrace-api-v1'
$webName='orbittrace-web-v1'
E:\Fusion\scripts\Azure.cmd group create -n $rg -l centralindia
E:\Fusion\scripts\Azure.cmd acr create -g $rg -n $acr -l centralindia --sku Basic --admin-enabled false --role-assignment-mode rbac
# Build and verify the image BEFORE creating compute hosting resources.
E:\Fusion\scripts\Azure.cmd acr build -r $acr -t orbittrace:v1 --platform linux/amd64 -f Dockerfile .
E:\Fusion\scripts\Azure.cmd identity create -g $rg -n id-orbittrace-v1 -l centralindia
E:\Fusion\scripts\Azure.cmd containerapp env create -g $rg -n $envName -l centralindia --logs-destination none --enable-workload-profiles true
E:\Fusion\scripts\Azure.cmd staticwebapp create -g $rg -n $webName -l eastasia --sku Free
# Capture identity/registry IDs without printing credentials; assign AcrPull on registry only.
$identityId=E:\Fusion\scripts\Azure.cmd identity show -g $rg -n id-orbittrace-v1 --query id -o tsv
$principalId=E:\Fusion\scripts\Azure.cmd identity show -g $rg -n id-orbittrace-v1 --query principalId -o tsv
$registryId=E:\Fusion\scripts\Azure.cmd acr show -g $rg -n $acr --query id -o tsv
E:\Fusion\scripts\Azure.cmd role assignment create --assignee-object-id $principalId --assignee-principal-type ServicePrincipal --role AcrPull --scope $registryId
$webHost=E:\Fusion\scripts\Azure.cmd staticwebapp show -g $rg -n $webName --query defaultHostname -o tsv
E:\Fusion\scripts\Azure.cmd containerapp create -g $rg -n $apiName --environment $envName --image "$acr.azurecr.io/orbittrace:v1" --user-assigned $identityId --registry-identity $identityId --registry-server "$acr.azurecr.io" --ingress external --target-port 8000 --cpu 1 --memory 2Gi --min-replicas 1 --max-replicas 1 --env-vars ORBITTRACE_PUBLIC_MODE=1 "ORBITTRACE_CORS_ORIGINS=https://$webHost"
# Configure explicit startup/readiness/liveness HTTP probes at /api/health:8000
# and verify the created app's replica/revision settings before public testing.
$apiHost=E:\Fusion\scripts\Azure.cmd containerapp show -g $rg -n $apiName --query properties.configuration.ingress.fqdn -o tsv
Set-Location E:\Fusion\frontend
$env:VITE_API_BASE_URL="https://$apiHost"
npm run build
Set-Location E:\Fusion
try {
  $env:SWA_CLI_DEPLOYMENT_TOKEN=E:\Fusion\scripts\Azure.cmd staticwebapp secrets list -g $rg -n $webName --query properties.apiKey -o tsv
  & .\.cache\azure-v1\swa\node_modules\.bin\swa.cmd deploy .\frontend\dist --env production
} finally {
  Remove-Item Env:SWA_CLI_DEPLOYMENT_TOKEN -ErrorAction SilentlyContinue
}
.\.venv\Scripts\python.exe -I scripts/verify_final_http.py --url "https://$apiHost" --origin "https://$webHost" --output .cache/azure-v1/public-http-v1
```

Do not treat default/generated TCP probes as the explicit `/api/health` HTTP probe requirement. Add and inspect the probe configuration through a reviewed Container Apps YAML before release. Docker health checks alone do not configure Azure probes.

For V2, after approval of cloud resource updates, use a unique image tag, run all tests, build with `az acr build`, then `az containerapp update -g $rg -n $apiName --image "$acr.azurecr.io/orbittrace:<unique-tag>"`. Build the frontend with the actual API hostname and deploy through SWA CLI as above. Record actual image digest, revision, URLs and fresh HTTPS/browser results. No GitHub automation is configured. New revision/restart loses in-memory jobs; drain the current analysis first.

## Monitoring, rollback and stopping charges

There is currently **nothing deployed to stop** and no application hosting charge from resources created by this task. Provider registration may remain; it is not a running website or container registry.

For a future approved deployment, inspect `az containerapp show`, `az containerapp revision list`, `az containerapp logs show --type system` and the Azure portal metrics/Cost Management pages. No paid Log Analytics workspace was proposed; persistent logs/alerts require a separate cost decision. Do not expose secrets in logs.

Save the previous image digest/tag and frontend bundle before each release. Rollback after approval by updating to the saved image and redeploying the saved frontend bundle; in-memory jobs will be lost. Re-run HTTPS and browser checks after rollback. Do not roll back by discarding source or resetting Git.

Stop a future app without deleting resources (requires approval; verify the target first):

```powershell
Set-Location E:\Fusion
$appResourceId=E:\Fusion\scripts\Azure.cmd containerapp show -g rg-orbittrace-v1-261010 -n orbittrace-api-v1 --query id -o tsv
E:\Fusion\scripts\Azure.cmd rest --method post --url "https://management.azure.com$appResourceId/stop?api-version=2026-01-01"
```

Verify the app is stopped. Registry storage continues to incur charges even when compute is stopped. To remove all future dedicated-group costs, obtain explicit deletion approval, list and verify **every** resource in the dedicated group, then use `az group delete --name rg-orbittrace-v1-261010`; never delete unrelated groups. No deletion command was run. See [Container Apps stop API](https://learn.microsoft.com/en-us/rest/api/resource-manager/containerapps/container-apps/stop?view=rest-resource-manager-containerapps-2026-01-01).

Next dependency: a hosting plan explicitly acceptable to the user's no-payment constraint, verified credit coverage if relevant, and a working Linux image build. Until then, use the verified original local demo; do not describe this preparation as a public deployment.
