> Provenance: substantive findings below are retained from the supplied planning pack. This bootstrap did not re-run its web research or inspect dataset archives. The original catalog mentioned by the pack is not included in this repository; its requirement summary is inherited, and official rules/rights remain unverified.

# Project brief and judge-facing requirements

## Requirement source

The attached FUSION catalog names SPACE-02 as **Ground-Based Optical Detection and Tracking of Orbital Debris**. Its expected output is a detector operating on real or synthetic telescope imagery, linking candidates across frames and estimating a rough trajectory. This summary comes from the supplied catalog; we have not independently authenticated the portal's issuing-organization claims.

## User and workflow

Our prototype user is an optical-observation analyst reviewing a short sequence. They need to see which detections belong to the same candidate, inspect uncertain associations, and export the observations for follow-up. The prototype reduces manual review effort; it does not operate a telescope or make collision-avoidance decisions.

The analyst loads an ordered sequence, chooses an appropriate image profile, runs analysis, plays the annotated frames, clicks a track, checks observations versus predictions, and exports a report. A deterministic synthetic example works without internet.

## Minimum useful product

| Requirement | What we build | Evidence judges can inspect |
|---|---|---|
| Input telescope images | Ordered PNG/JPEG sequence; manifest describes frame order and optional timestamps | Raw sequence visible; corrupt inputs rejected |
| Identify candidates | Lightweight blob/streak proposal extraction using image processing | Overlay and evidence crop for each proposal |
| Track across frames | Motion-gated assignment with persistent IDs | Same ID across frames; association provenance |
| Rough trajectory | Constant-velocity image-plane fit with short extrapolation | Measured observations, dashed predictions, units and fit error |
| Work in noise | Seeded noisy sequences plus artifact and missed-detection cases | Held-out benchmark, negatives, baseline comparison |
| Demonstrable output | Offline viewer and JSON/CSV report | Fresh rerun using recorded config and seed |

## Priorities

**P0:** synthetic end-to-end pipeline, single-frame baseline, stable IDs, trajectory estimate, one difficult case, export, clear provenance and reproducible evaluation.

**P1:** camera alignment, richer synthetic cases, missing-observation recovery, real spotGEO adapter and separate evaluation, polished comparison UI.

**P2:** optional trained streak detector, FITS input, prediction covariance and advanced association. Implement only when P0 works and the next feature improves evidence.

**Out of scope for this hackathon:** debris removal, real orbit determination, collision probability, global object cataloging, automated telescope control, physically calibrated speed without adequate metadata, claiming confirmed debris identity, or production deployment.

## What judges likely expect

This is our interpretation of the PS, not an official rubric:

1. The full chain works: raw images → detections → associations → trajectory.
2. The system handles a nontrivial noisy case, rather than merely drawing boxes on obvious objects.
3. There is a measurable baseline and an explanation of limitations.
4. Inputs, algorithms and results can be reproduced.
5. The team understands the astronomy enough to avoid confusing stars, artifacts and orbiting objects.

Provide source-image inspection and a clean failure example. If the evaluator exposes an association error, explain the gate or noise condition instead of hiding it.

## Differentiation that is achievable

Our proposed contribution is an integrated **sequence-based evidence workflow**: geometry and appearance proposals, temporal confirmation, one missed-frame recovery, original-image coordinate exports, and a robustness comparison. None of these individually establishes research novelty. Our claim is that the team implemented and evaluated this combination for the PS, with explicit limitations.

## Definition of done

- A clean checkout can install, generate a seeded sequence, analyze it and launch the viewer using documented commands.
- Inference reads images and metadata only; it does not read synthetic truth coordinates or test labels.
- A confirmed track contains at least three actual observations; predicted points are not counted as detections.
- At least one target in a suitable controlled case remains associated through one missed observation.
- A held-out synthetic report includes detection precision/recall, false positives, track coverage, ID switches, localization error and runtime, with denominator and configuration.
- Empty frames and zero-target sequences work normally.
- Exports distinguish synthetic/real data, observed/predicted positions and pixel/frame versus pixel/second units.
- The final presentation shows measured results or says “not measured.” No planned target appears as an achieved result.
