# Vercel frontend handoff — Railway V1

10 October 2026. Backend publicly deployed and HTTPS upload/analysis verified. **Frontend not deployed by this task.** No frontend source changes were necessary; existing API-origin support was reused and tested.

| Vercel setting | Exact value |
| --- | --- |
| Repository | `Subham5126/fusion26` |
| Branch | **Subham** |
| Root directory | **frontend** |
| Framework | Vite |
| Install command | `npm ci` |
| Build command | `npm run build` |
| Output directory | `dist` |
| Node | **24.x** in Vercel project settings; Node 24 used locally and compatible with existing engines |
| Production environment name | **VITE_API_BASE_URL** |
| Production value | **https://orbittrace-api-production.up.railway.app** |

Set the value before building; Vite embeds it at build time. Redeploy after changing it. Include it in Preview only if previews are needed and their exact origins are allowed separately. The existing frontend calls Railway directly for health, upload, polling, result, manifest, binary frames, diagnostics and JSON/CSV exports. **No Vercel API rewrite/proxy is required.** Client-side page routing uses hashes; no route rewrite is necessary for current routes. The Azure-specific `staticwebapp.config.json` is not a Vercel configuration requirement.

Platform references: [Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite), [Node 24 support](https://vercel.com/changelog/node-js-24-lts-is-now-generally-available-for-builds-and-functions). Node 20 was deprecated for new Vercel builds on October 1, 2026; choose 24.x for this handoff rather than relying on the broader local engine range. No package.json modification was necessary.

Important publication boundary: the latest frontend and parts of its T19/T20 foundation are still local uncommitted/untracked files. Selecting GitHub's Subham branch alone will build only published source. Review the existing T19/T20 allowlists and explicitly approve publication before expecting a Git-import build to contain this version. This deployment task did not stage/commit/push. The owner may instead deploy the current local frontend manually; backend-only Railway upload excludes it.

## Add your actual Vercel hostname to backend CORS

Current actual backend value:

```text
ORBITTRACE_CORS_ORIGINS=https://orbittrace-api-production.up.railway.app
```

Once Vercel supplies its real production domain, replace `YOUR-ACTUAL-PROJECT.vercel.app` below with that exact hostname. Do not leave the example value, use `*.vercel.app`, include a path or enable wildcard CORS. Each custom/preview domain needs an explicit origin.

```powershell
Set-Location E:\Fusion
E:\Fusion\scripts\Railway.cmd link --project 8eb7c103-8fd3-43f5-9340-49b8903a9f2b --service orbittrace-api --environment production
E:\Fusion\scripts\Railway.cmd variable set --service orbittrace-api --environment production "ORBITTRACE_CORS_ORIGINS=https://orbittrace-api-production.up.railway.app,https://YOUR-ACTUAL-PROJECT.vercel.app"
E:\Fusion\scripts\Railway.cmd deployment list --service orbittrace-api --environment production --json
```

Changing the variable normally triggers a backend redeploy: export existing results first, because jobs are in memory. Confirm SUCCESS before testing the frontend. No paid plan/payment attachment is authorized.

The production-origin CORS change has **not** been performed because the Vercel domain is unknown. Current CORS preflight was verified against the actual Railway origin; a full Vercel-to-Railway browser workflow remains untested.

## Verify after manual deployment

Open the Vercel workbench, check Backend connected, select five images, confirm their order and analyze. Test polling, frame 1→5 navigation, track selection, toggles, zoom/pan and JSON/CSV exports. Synthetic multi-object should show detections `[5,3,4,5,5]`, five confirmed tracks and ten forecast points. ESA84 should show 34 detections and **no fitted forecasts**. Empty input results should render no geometry; unsupported/uncertain/registration failures should display explicit errors.

The images/actual outputs for reproduction are under `E:\Fusion\.cache\railway-v1\http-public`. Do not upload raw datasets/checkpoints to Git/Vercel. In browser developer tools, API traffic should go to the Railway HTTPS domain with no mixed content or CORS errors.

Actual local verification: 104 main frontend tests + 19 overlay tests passed; TypeScript/Vite production build passed with the real Railway origin, written to `.cache/railway-v1/frontend-validation-dist`. This bundle was not published. Large landing-page chunk warning remains non-blocking.

Trial backend: approximately $4.53 credit and seven trial days remained at verification. Runtime is one worker/replica and 1 GB maximum RAM. Restarts/eviction lose jobs. See `docs/RAILWAY_DEPLOYMENT.md` for complete public HTTP results, source changes, redeploy and exact stop commands.
