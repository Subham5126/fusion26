# Synthetic demo presets — T19 follow-up

2026-10-10. Root E:\Fusion; branch Subham; base commit 1bad730757f2183985595d6ecee911c1179925e9. User requested four sub-demos under Synthetic demo. Implemented and tested; no commit, push or deployment.

## Behavior

Select Detection mode > Synthetic demo. A Demo sequence selector appears; selecting a preset immediately starts a new backend job. Run demo again repeats the currently selected preset. Busy requests disable selectors and retain cancellation. Uploaded-image selection remains independent.

| Preset | Generated motion | Observed API/browser result |
|---|---|---|
| 1 | Two horizontal paths in opposite directions | 10 detections, 2 confirmed tracks, 4 forecast points |
| 2 | Two diagonal paths | 10 detections, 2 confirmed tracks, 4 forecast points |
| 3 | Three objects moving in different directions | 15 detections, 3 confirmed tracks, 6 forecast points |
| 4 | Three curved paths | 15 detections, 3 confirmed tracks, 6 forecast points |

Each preset generates five deterministic 640x480 grayscale images. All target tracks contain genuine detections in frames 0 through 4; these are synthetic demonstration results, not real-data accuracy evidence. Backend OpenCV detection, association and trajectory fitting run on the rendered images, without supplied truth detections. Curved motion is observed; forecasts retain the existing linear fit, with that limitation explained in the UI.

`POST /api/analyze/demo?preset=1` through `preset=4` are bodyless and return the existing 202 job envelope. No shared schema change. Unknown presets return 422 before creating a job. Bodyless requests without a preset retain the original five-frame 64x48 single-object behavior, preserving existing clients. Existing job/result/manifest/native PNG routes supply the viewer. No detector or tracking algorithm changes.

## Files for this follow-up

Created: backend/orbittrace/demo_scenes.py; tests/api/test_demo_presets.py; this document.

Modified: backend/app/api/analyze.py; frontend/src/api/transport.ts; frontend/src/api/client.ts; frontend/src/state/analysisJob.ts; frontend/src/hooks/useAnalysisJob.ts; frontend/src/components/workbench/LocalWorkbench.tsx; frontend/src/components/workbench/AnalysisPanel.tsx; frontend/tests/analysis-jobs.test.ts; docs/handoffs/FINAL_RELEASE_ALLOWLIST.txt.

## Actual verification

- `.\.venv\Scripts\python.exe -m pytest tests/api/test_demo_presets.py tests/api/test_t09_api.py -q`: 13 passed, 3 existing deprecation warnings. Verified every preset's detections, track count, five associations per track, image dimensions and PNG retrieval, plus invalid-preset rejection and existing upload behavior.
- In frontend: `node tests/run-data-tests.mjs`: 124 passed; `node tests/overlay.test.mjs`: 19 passed.
- `npm run build`: TypeScript and Vite passed. Existing landing/Three.js chunk warning remains.
- Initial new frontend test found the URL validator intentionally rejects query-bearing paths. Fixed the transport to validate the unchanged endpoint and append only the enumerated preset query; final tests passed. The URL validator was not weakened.
- Actual browser submitted all four presets through the selector, received distinct backend jobs, displayed native images and correct multi-object counts. Final frame showed all five observations per object and forecasts; selecting track-0003 updated its details. Console warning/error collection was empty.
- Screenshot: `.cache/final-release/demo-four-paths.png`; receipts: `.cache/final-release/demo-presets-browser.json`. These generated artifacts remain excluded from Git.

Verified E:\Fusion backend was restarted to load the additive API behavior. New listener PID 7588 at verification; frontend remained on 5173. Startup scripts remain scripts/Start-Backend.ps1 and scripts/Start-Frontend.ps1. No production deployment occurred. Earlier real-data registration/accuracy limitations remain unchanged.

Open http://127.0.0.1:5173/#/workbench. Select Synthetic demo, then Demo 1/2/3/4. Use Inspect final frame & forecasts, track selector, timeline, playback and zoom. Switching to Standard returns to uploaded-image mode. Publication remains subject to the earlier no-automatic-push instruction.
