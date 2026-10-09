# User interface specification

## Main screen

Mission-workbench layout: sequence source and controls at top, image viewer as the largest area, track list/evidence at right, frame timeline below, optional benchmark tab. Dark background helps grayscale inspection, but preserve readable contrast and visible warning text. Do not spend P0 on an animated 3D Earth.

## Controls and states

- Select an installed demo or upload an ordered image sequence with manifest.
- Show source type, frame count and chosen acquisition profile before analysis.
- Run analysis; show queued/running stage; disable repeated submits while busy.
- Play/pause, step forward/back, scrub timeline and choose playback speed.
- Toggle raw view, candidate overlay, confirmed tracks, predictions and evidence.
- Click a track to inspect observed frame count, coordinate units, quality evidence, residual and warnings.
- Download JSON/CSV. Benchmark tab is available only when a measured report exists.

States: no sequence, validating, queued, analyzing, success with tracks, success with no tracks, failed analysis, unsupported registration. “No candidates found” is a valid result, not a crash.

## Overlay rules

Use stable colors per track. Observations use solid markers/segments; predicted points use hollow markers and dashed segments. Tentative candidates are visually distinct. Do not draw a prediction as if the detector observed it. Mark out-of-field predictions.

Canvas must scale with the image while keeping a consistent native coordinate transform. Account for letterboxing and device pixel ratio. Picking a track should work after resize. Raw-image view overlays raw coordinates; reference view overlays reference coordinates. Never mix them.

## Evidence and score wording

Label “candidate quality” with a tooltip: heuristic support score, not calibrated debris probability. Explain support from actual observations, morphology and fit residual. Label object identity unverified. Speed shows px/frame or px/s, never an invented physical unit.

Do not display accuracy from a user's unlabeled upload. The benchmark tab shows the source split, number of sequences, baseline, matching gate and runtime environment. A demo fixture must say “illustrative fixture.” A cached report must say “cached result.”

## Usability check

Run the viewport at laptop width, resize it, select tracks near borders, scrub to a missing-observation frame and inspect empty results. All essential actions should be obvious during a two-minute live demonstration. No mandatory sign-in, external map, API key or internet request in the offline demo.
