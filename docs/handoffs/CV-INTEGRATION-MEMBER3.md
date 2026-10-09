# Message prepared for Member 3 — T13/T14 CV handoff

The CV interfaces are locally verified against your exact tracker/fit snapshot
at `a015cc949955d0438c8a16789b23746c3206f3d1`; no tracking source was changed.
Subham still lacks canonical tracker/fit modules. Member 1 needs to review their
integration and package `src/astrotrace` with backend. This is a draft for human
handoff, not a sent external message.

Use `orbittrace.detection.detect_sequence(frames, sequence_id=..., config=None,
method="optimized")`, then image-only
`astrotrace.preprocessing.registration.register_sequence(frames, config=None)`
and `add_reference_coordinates(raw_detections, registration)`. Detection runs on
untouched native frames. The helper sets only x/y_reference_px on validated copies
of `app.schemas.result.Detection`; all raw fields and IDs are preserved.

Transforms are raw -> reference_frame_0, x_ref=x_raw+tx/y_ref=y_raw+ty, with the
inverse preserved. All frames register directly to frame0, not a chained stream.
Top-left origin, integer centers, float coordinates and exclusive raw upper boxes
apply. Negative/outside reference positions are legitimate after translation;
do not clip them or always mark observed out_of_field=False without checking the
appropriate field geometry. Warped images are display previews with invalid masks.

Your coordinate extractor falls back to raw when references are null. Therefore
the helper refuses the entire registered stream if ANY frame fails, including an
empty frame. Agree any future segment/retry policy with Member 1; do not silently
mix raw and reference detections or substitute identity for a failed transform.
Real train/438 fails frames3/4; registered tracking was blocked as intended.

Pass `frame_indices=range(len(frames))` to `Tracker.process_sequence`, including
empty/trailing frames. One/two misses can recover; more than two retires a track
under the tested defaults. The gap belongs to lifecycle state, not an invented
observation. Start/reset per sequence. Unknown ESA times remain null and px/frame;
known times need the same frame_timestamps mapping for tracking and fit. Your
motion predictor uses frame-index intervals, so irregular seconds cadence needs
explicit review; px/s trajectory fitting alone does not change association timing.

Fresh controlled results at the actual20px gate:

| Case | Actual result |
|---|---|
| counts_change [5,3,4,5,5] | 5 confirmed tracks,22TP/0FP/0FN,17 correct links,0 switches/fragments,2/2 gaps recovered |
| camera_motion | Raw20 switches/20 fragments; registered0/0,5 confirmed true tracks;25TP/4FP/0FN |
| crossing | 9TP/0FP/1FN;2 coincident truth observations excluded from identity scoring |
| nearby4px | 0TP/0FP/10FN; no tracks, not association success |
| persistent artifact | 25TP/5FP/0FN;1 false confirmed track |
| blank-frame registration failure | Registered blocked; separate raw diagnostic recovered5/5 gaps |

Real train/84 gave[7,7,6,8,6] candidates,23 raw tracks versus31 registered tracks
(zero registered confirmed). These are compatibility counts, not real tracking
accuracy. Star alignment includes apparent sky drift; target displacement relative
to the background may exceed the initial gate. No persistent ESA identity labels
were invented. Confirmed status denotes observation support, not confirmed debris.

**Gate question:** your current `Tracker()` and shared PipelineConfig both use20px;
Git history shows20px since the original tracker implementation. The15px statement
in CV-T13 was stale and is now corrected; no15->20 tuning change occurred here. Please confirm the
intended profile/cadence/registration-uncertainty policy for initial association
and how overrides should be recorded. Do not widen it merely to obtain more tracks
on these already-used ESA diagnostics.

Please review persistent sensor-coordinate nuisances, merged/nearby-target
ambiguity, field-exit flags and irregular-cadence association separately. Temporal
confirmation alone allowed the persistent compact artifact to form a false track.
The uncertain blur diagnostic bypass also produced56 false confirmed tracks;
normal suitability gating must prevent that run from becoming accepted analysis.

Fresh evidence: `artifacts/reports/cv_readiness/final/index.html`, with observed track
overlays and separate raw/reference JSON. Final full suite339 passed,0 failed/skipped;
initial291 CV tests and post-fix43 focused tests passed. All93 report links resolve.
Exact reproduction and publication boundaries are in
[CV-INTEGRATION.md](CV-INTEGRATION.md).
