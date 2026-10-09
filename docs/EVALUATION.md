# Evaluation protocol

No results exist yet. All proposed values are engineering defaults or target checks. The evaluation owner must populate a separate measured report after running the implementation.

## Prevent leakage

Split by complete sequence. Generate different scene seeds/star fields for development, validation and test. Frames, crops and augmentations of one scene stay in one split. Fit/tune thresholds on development/validation only. Freeze the test manifest before final analysis.

The inference entry point receives only images and allowed metadata. Test labels and true camera transforms are evaluator-only. For synthetic camera-jitter benchmarks, inference estimates transforms; it must not consume the generator's exact transform and then claim registration accuracy. A known-transform diagnostic may be run separately if explicitly labeled oracle.

## Per-frame detection matching

Evaluate point localization with minimum-cost one-to-one gated matching in raw coordinates. Initial localization gate: 5 px for synthetic data; list sensitivity at 3 and 10 px. For spotGEO inspect the official scoring implementation before claiming comparability. Our 5 px protocol is not the official ESA metric. [S5]

Use dummy unmatched rows/columns or equivalent gated matching that maximizes admissible match count before minimizing distance. Match only within the declared gate. A greedy or forced assignment that hides unmatched objects is unacceptable.

TP = accepted matches, FP = unmatched detections, FN = unmatched eligible truth objects. Precision `TP/(TP+FP)`, recall `TP/(TP+FN)`, F1 where defined. Aggregate counts over the full benchmark before computing micro metrics. If the denominator is zero, return `null` and a reason; explicitly report zero-object and zero-detection counts. Avoid reporting perfect precision on an empty negative scene.

Localization RMSE is calculated over matched **observed** points, with number of matches and recall beside it. Low localization error with low recall is not sufficient. Do not evaluate interpolated points as observed detections.

## Tracking metrics on synthetic identity ground truth

- **Coverage:** eligible visible target-frames recovered with the appropriate associated track, divided by eligible visible target-frames. State whether per-object or aggregate.
- **ID switches:** using a deterministic per-frame one-to-one match, count changes of assigned predicted ID for a true target across its matched observations; declare the gap rule. Use both absolute count and scenes evaluated.
- **Fragmentation:** interrupted recovered segments for one true target, with a declared missing-frame tolerance.
- **False confirmed tracks:** confirmed predicted tracks without adequate true-object correspondence; include negative scenes.
- **Missed-frame recovery:** identity continuity before and after a generated hidden observation; predicted gap point is not a detection TP.

spotGEO's documented coordinates are not an identity annotation guarantee. Do not report true IDF1/MOTA or verified ID switches there by assigning IDs from array order. Report per-frame localization and qualitative temporal consistency unless identity labels have been independently established and reviewed.

## Trajectory and prediction error

Fit on the first eligible observations and evaluate the next held-out future frame(s), or use a declared walk-forward protocol. Never fit using all frames and call its residual a future prediction error. On synthetic data, compare predicted position with true latent position, including occluded intervals separately. Report RMSE, prediction horizon, unit and sample count. Keep fit residual, interpolation error and future extrapolation error separate.

## Runtime

Measure pipeline wall time excluding and including disk I/O separately if practical. Record CPU, memory, image dimensions, sequence length, config, code commit and dependency versions. State whether a cached run, cold run or warm run. Use median and p95 over the measured sample set when sufficient samples exist; otherwise list raw runs. Do not advertise “real-time” without latency and acquisition constraints.

## Ablation matrix

| Run | Method change | Fair comparison |
|---|---|---|
| A | Single-frame candidate baseline | Same images and preprocessing |
| B | A + temporal confirmation/association | Same candidate threshold; compare false detections/tracks and recall |
| C | B + registration | Same jitter scenes; record alignment failures |
| D | C + missed-frame handling | Same one-gap scenes; report ID continuity and ambiguity |

Train a model only in an additional experiment. Do not silently change thresholds, sample membership and algorithm simultaneously, then attribute all gains to one feature.

## Required report table

Use columns: method, split, profile, sequence count, eligible target-frames, precision, recall, false positives/frame, localization RMSE px, ID switches (where labeled), false confirmed tracks, prediction RMSE px at horizon, runtime, failures. Populate only actually computed values. `Not measured` is acceptable; a fabricated figure is not.

## Cases to show judges

One clean track, one noisy track with a missed frame, one negative/artifact scene, and one honest failure (such as crossing targets or unsupported camera motion). Presentation examples can be chosen for clarity, but benchmark averages come from the frozen manifest rather than only successful examples.
