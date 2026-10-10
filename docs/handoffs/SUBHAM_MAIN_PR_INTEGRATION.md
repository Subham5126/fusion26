# T19 — Subham-to-main PR integration

2026-10-10, original E:\Fusion, publication branch Subham. User explicitly authorized PR creation, conflict resolution and merging to main. Base Subham d0bbb43ccce298e189e36ca626f2813a50e90963; main d499254. PR: https://github.com/Subham5126/fusion26/pull/15.

Ten frontend files conflicted. Both sides were inspected. The premium Member 4 styles were already integrated into Subham; main's older conflict blocks would remove the newer PDF reporting, gap history, detector mode selector, live-only default workspace and truthful diagnostic descriptions. Those newer behaviors were retained. Original versus registered coordinates, current boxes, actual observations and labeled camera-propagated estimates remain distinct. No schema or tracking algorithm changed in this merge.

Conflict files: CapabilitySection.tsx, AnalysisPanel.tsx, LocalWorkbench.tsx, OpticalViewer.tsx, SystemDiagnostics.tsx, WorkbenchShell.tsx, WorkbenchPage.tsx, interactions.css, workbench.css (under frontend/src), and frontend/tests/live-visualization.test.ts. main's nonconflicting final-forecast shortcut, empty-sequence styling and obsolete standalone fixture-control removal were retained. The main Dockerfile uses the official ECR Python mirror; no new deployment-resource changes were made.

Actual validation after resolution:

- Python full suite: 570 passed, 2 optional historical tracking-snapshot tests skipped, 6 warnings, 91.19 seconds.
- Frontend: 128 passed. An initial merge regression hid Analyze and expected the old standalone synthetic workflow; the live upload control and prior behavioral assertions were restored before the final green run.
- Overlay: 19 passed.
- TypeScript/Vite production build passed; existing >500 kB landing chunk warning remains.
- HTTP verification through frontend5173/backend8000: nine genuine jobs and expected outcomes, including synthetic, changing counts, empty, unsupported, uncertain, registration failure, ESA84, ESA438 expected failure and five-image synthetic upload. ESA84 has 31 detections, 28 track records, zero fits; no forecasts fabricated.
- Browser: genuine retained ESA test/4 five-image upload completed. F1 remained fixed, F2/F3 estimated gap markers accumulated, F4 added the second actual observation, F5 retained history; rewind and estimates toggle passed, observation count stayed two. Fresh page reload then Synthetic Demo1 completed with two tracks, five observations each, two current neon boxes and four genuine forecast points. No warnings/errors after the fresh reload. Vite had transient hot-reload errors while merge conflict markers were present; those were resolved, not runtime analysis failures.

Reproduction in E:\Fusion: `.\.venv\Scripts\python.exe -m pytest -q -rs`; in frontend run `node tests/run-data-tests.mjs`, `node tests/overlay.test.mjs`, `npm run build`. Live runner: `.\.venv\Scripts\python.exe -X utf8 -I scripts/verify_final_http.py --url http://127.0.0.1:5173 --origin http://127.0.0.1:5173 --output .cache/final-release/pr-http-reproduce`. Existing services were reused, not restarted. Logs and screenshot under .cache/final-release/pr-* are excluded from Git.

Unrelated tracked local edits were preserved in a named Git stash before merging; untracked Railway files, Vercel helper and Ultralytics directory were untouched. Restore and verify the stash after integration, retaining its recovery copy. No force push, source-branch deletion or independent hosting deployment is authorized/performed here. Real-data detector/registration limitations and optional model deployment packaging remain documented in FINAL_ORBITTRACE_RELEASE.md.
