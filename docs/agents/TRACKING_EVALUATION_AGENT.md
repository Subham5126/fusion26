# Tracking and evaluation agent prompt

```text
You own tracking/evaluation for OrbitTrace SPACE-02. Read AGENTS.md, STATUS, CONTRACTS, ALGORITHMS, EVALUATION and your assigned tasks. Restrict edits to backend/orbittrace/tracking, trajectory, evaluation and their tests. Integration owns shared contracts, config and pipeline glue.

Implement T04/T05 using a declared common coordinate frame. Start with a constant-velocity predictor, bounded distance gates, minimum-cost one-to-one assignment and explicit unmatched handling. Impossible pairs must not force a match. Track status is tentative/confirmed/ended. Confirm after at least three actual observations; advance gaps as predictions and retain at most configured misses. Use timestamps when actually available; otherwise motion units are pixels/frame. Keep ambiguity visible at crossings.

Trajectory fit uses observed points only. Keep residual, interpolation error and held-out future prediction error separate. Limit predictions to short horizons; do not invent altitude, orbital speed, full orbit or calibrated probability. Handle empty candidates and invalid time intervals without NaN output.

For T06/T10/T12/T15, implement the frozen protocol: sequence-based splits, gated one-to-one localization matching, TP/FP/FN aggregates, negative scenes, localization RMSE with match count and recall, synthetic identity coverage/ID switches, false confirmed tracks and runtime provenance. Unknown denominators return null with reason. Do not infer spotGEO identities from annotation order.

Use identical held-out scenes for ablations, tuning only on development/validation. No access to labels or oracle camera transforms from inference. Do not report interpolated gap points as detection true positives. Prediction tests must withhold future observations from the fit.

Targeted tests: forbidden assignments remain unmatched; one-gap identity continuity; empty/no-target scenes; crossing ambiguity; matching denominators; timestamp units; deterministic metrics; no inference label access. Include an honest failure case.

Write a per-task handoff with actual commands, measured values/config/hardware where available, changed paths, known limits and dependency needs. Do not copy reported accuracy from an external repo or convert planned goals into results.
```
