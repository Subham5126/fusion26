# Algorithms: implementation recipes and failure handling

All numeric values below are initial engineering defaults, not scientific constants or achieved results. Tune on development/validation data only and store the chosen configuration.

## 1. Load and normalize

Require 3–30 frames for the proposed upload path. Five frames is a useful real-data case; twelve frames supports a clearer synthetic demo. Validate dimensions, decode safely, retain original files and sort by manifest indexes rather than ambiguous lexicographic names. Normalize intensity for processing while preserving untouched originals for inspection. Contrast stretching for display must not secretly change input to the detector.

For monochrome data use float32 intensity. Convert color input using a documented rule. Background subtraction can use a coarse median background or a large-scale filter. Estimate noise with a robust statistic such as MAD on suitable background pixels; handle near-zero variance without division by zero. Avoid aggressive smoothing that erases subpixel/faint sources.

## 2. Profile and alignment

**`synthetic_static_stars`:** stars are stationary apart from generated camera jitter; target moves relative to this background. Identity alignment is allowed only when the manifest says there is no jitter. Otherwise estimate translation/rotation on background features using robust correspondences or ECC with an appropriate motion model. [S11]

**`ground_static_star_streaks`:** ground-static exposures can streak stars while targets may be compact. Propose compact objects from the original frames and use acquisition-aware consistency. Do not delete every persistent compact signal as a “static star.”

**`spotgeo`:** optional real-data profile. Camera rotation and sidereal star motion make naive differencing inappropriate. Inspect sample morphology first. Match reliable background structures to estimate the relevant transform, then verify residuals. Start with compact-source proposals plus temporal geometric support. If registration fails, report an unsupported alignment condition; allow per-frame detections but do not claim a reliable cross-frame trajectory. [S2, S4]

Keep a validity mask for warped image borders. Test transform direction explicitly using synthetic known rotation/translation. Raw-to-reference and reference-to-raw operations need round-trip checks. A good ECC score alone does not certify correct astronomy or object correspondence.

## 3. Baseline

Single-frame baseline: robust local threshold → connected components for compact proposals; edge/line detector for streak proposals where the profile supports it. OpenCV provides `HoughLinesP` and line-segment tools. [S10]

Apply configurable area, length and elongation filters without assuming every star is a point. Merge overlapping fragments belonging to the same visible streak. Store centroid, bounding box, optional endpoints, brightness and morphology. Start with a practical proposal cap (200 per frame) and record truncation in warnings.

The baseline uses the same preprocessing and thresholds as the temporal variant when isolating the effect of tracking. It does not get truth labels. Record all candidates, including false proposals, for comparison.

## 4. Temporal evidence

Use aligned differences or an aligned temporal background only in a profile where that operation is meaningful. Include direct compact-source proposals so slow/near-stationary targets are not systematically lost. Combine evidence with deduplication. Median background subtraction can erase persistent targets; evaluate that failure explicitly.

Reject or downgrade isolated flashes using lack of temporal support. Handle detector-fixed hot pixels using known sensor-coordinate persistence and morphology, not just “seen in three frames.” A hot pixel can also persist; temporal confirmation alone is insufficient. For uncalibrated images, show ambiguous candidates rather than claiming perfect star/artifact separation.

## 5. Association

MVP state: `[x, y, vx, vy]` in the declared tracking reference. Use actual frame intervals when timestamps exist; otherwise use frame indexes with `Δt=1`.

1. Predict active tracks to the next frame.
2. Compute gated costs between predictions and detections. Initial distance gate: 20 px, adjusted only through recorded config. Consider brightness and streak-angle agreement as optional secondary terms.
3. Mark impossible pairs invalid. Use dummy unmatched assignments or equivalent logic so forbidden assignments cannot force incorrect associations.
4. Solve allowed assignments with SciPy `linear_sum_assignment` (minimum-cost assignment; avoid claiming a particular internal algorithm). [S12]
5. Update matched tracks; advance missing tracks without inventing a detection.
6. Start tentative tracks for unmatched detections. Retain a maximum two consecutive misses initially.
7. Confirm only after at least three real observed points with acceptable consistency; one flash cannot become a confirmed track.

A Kalman filter is a reasonable P1 refinement once simple constant-velocity association works. Noise matrices are explicit configuration. Do not use a zero uncertainty prediction after a missed frame. OpenCV supplies Kalman machinery. [S11]

Crossing similar targets remain ambiguous; retain an ambiguity flag and evaluate ID switches. Candidate score can combine observation support, residual and appearance evidence, but call it a heuristic quality score rather than a calibrated probability.

## 6. Trajectory estimation

Fit `x(t)=ax+vx*t`, `y(t)=ay+vy*t` to actual observed coordinates in a chosen common frame. Use a robust fit or outlier check for P1. Require at least three observations for confirmed trajectory display. Show residual RMSE and number of fitted observations. Keep extrapolation short: next one or two frames only by default.

If timestamps are absent, speed is px/frame. If valid elapsed seconds are provided, speed is px/s. Do not infer acquisition timestamps from filenames or use the exposure duration as a guaranteed frame interval. spotGEO PNG sequences do not carry the metadata needed to establish that assumption. [S4]

A predicted point can lie outside the image; mark it out of field rather than clipping it into a plausible detection. Predicted covariance is optional; if shown, it must come from the declared model, not a decorative halo.

## 7. Evidence report

For every confirmed track report actual observation count, missing positions, mean signal evidence, fit residual, supporting crops, coordinate frame, units and ambiguity/registration warnings. Keep observed, interpolated and extrapolated points visually distinct. If a source cannot be classified, label it “candidate; identity unverified.”

## Numerical edge cases

Empty candidate lists, all-black/all-white frames, uneven timestamps, zero time differences, one observation, nearly stationary source, duplicate proposals, border artifacts, extreme noise, and invalid transforms must return defined results or explicit validation errors. NaN/Infinity must never enter exported JSON.
