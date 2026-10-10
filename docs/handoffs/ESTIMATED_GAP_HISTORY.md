# T19 follow-up — estimated positions for missed frames

2026-10-10; E:\Fusion; Subham; base 1bad730757f2183985595d6ecee911c1179925e9.

Implemented and tested display-only gap history. The actual ESA test/4 track-0001 has only two detections, F1 and F4. There are no nearby associated detections in F2/F3. The UI now offers estimated intermediate positions rather than inventing measurements or joining unrelated track IDs.

In Original image path, Show estimated gap positions defaults on. Each missing frame between the first and last actual observations uses the preceding observation's reference position and that missing frame's measured reference-to-raw camera translation. Estimates assume no additional object movement since the preceding observation; they are not recovered detections. Later observation coordinates do not determine earlier estimates. Invalid transforms and positions outside the native image are omitted. No positions are added beyond the last actual observation.

Actual observations remain filled track-colored dots. Estimated F2/F3 markers are hollow amber circles labeled `F2 est.` / `F3 est.`, joined with dashed amber lines. The timeline reveals them progressively and removes future markers on rewind. Turning estimates off restores the connector between available actual observations. Registered motion does not show these estimates. Current detection boxes, observation counts, confidence, backend trajectory predictions and exports remain based on actual backend data. No schema, detector or association changes were made for this follow-up.

Changed files: frontend/src/viewer/scientificOverlay.ts; frontend/src/viewer/uploadOverlay.ts; frontend/src/components/workbench/LocalWorkbench.tsx; frontend/src/components/workbench/T08Overlay.tsx; frontend/tests/t08-overlay.test.ts; this handoff; FINAL_RELEASE_ALLOWLIST.txt.

Verification: node tests/run-data-tests.mjs — 128 passed; node tests/overlay.test.mjs — 19 passed; npm run build — TypeScript and Vite passed, existing >500 kB landing chunk warning. Regression coverage includes progressive gaps, rewind, disabling estimates, registered view, no added forecasts, no result mutation and independence from later observation coordinates.

Earlier local browser verification used a genuine five-image Standard upload from data/raw/SpotGEOv2/test/4. Track-0001 showed: F1 one observed/zero estimated; F2 one observed/one estimated; F3 one observed/two estimated; F4 and F5 two observed/two estimated with three dashed connectors. Rewinding to F2 removed the later markers. Backend forecast count remained zero. The toggle's on/off behavior is unit-tested; a separate browser toggle pass was not completed before publication.

Reproduce: start the existing backend/frontend using scripts/Start-Backend.ps1 and scripts/Start-Frontend.ps1 when their ports are free. Open http://127.0.0.1:5173/#/workbench, upload the five test/4 PNGs, confirm order, run Standard, select track-0001, choose Original image path and enable Show estimated gap positions. Inspect frames 1 through 5, then rewind. Backend detection recovery for missing frames remains a separate task; these markers do not improve measured detection accuracy.

Publication was explicitly authorized by the user after the master release review. Only FINAL_RELEASE_ALLOWLIST.txt entries are selected; datasets, caches, large weights and unrelated deployment edits remain excluded. This handoff records local behavior, not a production deployment claim.

Publication recheck: `.\.venv\Scripts\python.exe -m pytest -q -rs` — 570 passed, 2 optional tracking-snapshot tests skipped, 6 warnings, 93.20 seconds. Frontend runners again passed 128 and 19 tests; TypeScript/Vite build passed with the existing landing chunk warning. Logs are excluded under .cache/final-release/publication-*.log. Branch and origin/Subham matched before publication; the index was initially empty. The exact 55-file allowlist passed whitespace and bounded-file checks, with no private-key/GitHub-token/AWS-key pattern matches. No dataset, checkpoint, generated browser artifact or unrelated deployment change was staged.
