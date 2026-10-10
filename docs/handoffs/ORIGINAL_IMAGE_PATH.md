# T19 follow-up — original-image path versus registered motion

2026-10-10, E:\Fusion, Subham, base 1bad730757f2183985595d6ecee911c1179925e9. Implemented/tested; no commit, push or deployment.

The user explicitly requested that F1 stay at its original screen/image position and that the connecting path show the displacement visible across the source images. The previous path used reference coordinates projected through the displayed frame's inverse registration. That correctly removes camera movement, but shifts historical markers when changing images and produces a much shorter, sometimes oppositely directed path. These are two distinct visualization questions, not a registration sign reversal.

Added Path view in uploaded results, default Original image path. It draws each actual observation at its per-frame raw x/y, preserving earlier positions as recorded in each source image. It includes camera motion and labels historical positions accordingly. Registered motion remains selectable and retains the original current-frame inverse projection. No backend transformation, detection, association or forecast algorithm changed.

Actual ESA test/4 track-0001:
- F1 raw/reference: (582.517366,370.518536).
- F4 raw: (488.313302,271.643643); reference: (590.036110,375.666155).
- Original-image path: (-94.204065,-98.874893) px, upper left; F1 stays fixed through F5.
- Registered displacement: (+7.518744,+5.147620) px, lower right, relative to the aligned scene.
- There are two actual observations only. F2/F3/F5 are not fabricated. F1-to-F4 is the connector between the two available measurements, not a measured intermediate curve.

Track direction and enlarged path panel now use the selected coordinate view. Heuristic quality remains the backend value. Reports retain clearly labeled raw and reference coordinates and the existing reference-coordinate summary. Current boxes stay in their own displayed frame's raw coordinates. Forecast positions and their origin remain correctly projected into the displayed image; they are not anchored to a historical raw-image marker from another frame. Original history with differing source dimensions is suppressed with an instruction to use Registered motion.

Changed files: frontend/src/viewer/uploadOverlay.ts; frontend/src/viewer/resultReview.ts; frontend/src/viewer/trackReport.ts; frontend/src/components/workbench/LocalWorkbench.tsx; frontend/src/components/workbench/TrackQualityPanel.tsx; frontend/src/components/workbench/TrackPathDetail.tsx; frontend/tests/upload-integration.test.ts; this handoff; FINAL_RELEASE_ALLOWLIST.txt.

Actual commands in frontend: node tests/run-data-tests.mjs — 127 passed; node tests/overlay.test.mjs — 19 passed; npm run build — TypeScript and Vite passed, existing >500 kB landing chunk warning. New tests cover raw-history persistence under changing camera transforms, actual current boxes, forecast origin integrity, original versus registered direction, timeline limits, no result mutation and 1x/2x/4x/8x scaling. Backend unchanged; Python suite not rerun for this display change.

Browser: uploaded the five actual data/raw/SpotGEOv2/test/4 PNGs; observed F1 at the exact same raw coordinate on frames 1-5, added actual F4 and its solid line on frame 4, retained the full line in frame 5, and removed future F4 on rewind to frame 2. Confirmed original-view direction upper left and registered-view direction lower right. Zoom preserved source coordinates. No console warnings/errors. Screenshot .cache/final-release/test4-original-image-path.png; receipt test4-original-image-path-browser.json. Evidence stays excluded from publication.

Open http://127.0.0.1:5173/#/workbench, analyze ESA test/4 with Standard, select track-0001 and use Original image path. Path view changes do not rerun analysis. Existing real-data false-positive/registration limitations remain unchanged. Publication still requires approval under the master request.
