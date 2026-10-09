> Provenance: substantive findings below are retained from the supplied planning pack. This bootstrap did not re-run its web research or inspect dataset archives. The original catalog mentioned by the pack is not included in this repository; its requirement summary is inherited, and official rules/rights remain unverified.

# Research findings and recommended decisions

## Verified findings

| Source | Finding | Consequence for our project |
|---|---|---|
| Supplied FUSION catalog | Synthetic telescope sequences are allowed | Do not make the first demo depend on external data |
| spotGEO record and ESA pages [S1–S4] | Five-frame GEO observations, point annotations, rotating camera; stars and target morphology differ | Use a separate adapter and acquisition profile |
| StreaksYoloDataset [S6] | Astronomical streak annotations in YOLO format | Useful for an optional per-frame streak detector; tracking labels must not be assumed |
| Related GitHub repo [S7] | Blender/YOLO workflow; tracking appears under future work; atmospheric scattering is listed as absent | Study it as related work, not a drop-in ground-telescope pipeline |
| satmetrics [S8] | FITS streak analysis project | Relevant classical-method reference, not proof of debris identity |
| Frigate author repo [S9] | FITS preprocessing and difference-image tools; automatic annotation described as in development | Advanced optional validation; do not assume a ready benchmark |

Full links and verification limits are in [SOURCES.md](SOURCES.md).

## Why the existing repository is not the same solution

The README describes rendered images of recognizable debris bodies and model training. It explicitly lists motion tracking as future work and records positional-bias and atmosphere limitations. Ground telescope candidates can be unresolved points or streaks rather than detailed spacecraft shapes. Our inference must therefore be designed around telescope imagery and temporal evidence. These conclusions are based on its published documentation, not an independent reproduction of its results. [S7]

Do not copy its reported mAP into our pitch. Do not use its sample images as if they were our independent real-world results. If reusing code, record exact origin, commit and license; its displayed current license is GPL-3.0. Review the actual license before redistribution. [S7]

## CPU-first approach

Start with OpenCV, NumPy and SciPy. Extract candidate blobs and line-like structures; associate candidates using gated minimum-cost assignment; estimate motion with a small constant-velocity state model or robust fit. OpenCV documents line detection, image alignment and Kalman primitives; SciPy provides `linear_sum_assignment`. [S10–S12]

This avoids waiting for model training and makes failures interpretable. A generic pretrained YOLO model must not be presented as already trained on faint telescope targets. Add YOLO only if suitable annotations, compute, licenses and validation time are available. [S15]

## Three important scientific boundaries

**Candidate identity:** morphology and short motion tracks alone generally do not establish whether an orbiting source is operational debris or an active satellite. Our label means candidate for review.

**Trajectory:** use a short path in a declared image coordinate system. Orbit fitting needs additional calibrated observations and metadata. Do not convert pixels to altitude or km/s using an invented scale. Optional WCS conversion requires a valid calibration. [S13]

**Acquisition mode:** a background-subtraction method suited to a stationary star field may remove slowly moving targets or fail on a rotating camera. In spotGEO, stars are streaked and GEO sources are comparatively compact under the documented exposure regime. Registration to stars also changes the meaning of target motion. Preserve the reference transform and describe what coordinate frame is used. [S2, S4]

## Chosen innovations and how to substantiate them

| Proposed addition | Implementation | What we measure |
|---|---|---|
| Temporal candidate confirmation | At least three actual observations plus association checks | Confirmed false tracks on negative and artifact scenes |
| Missed-frame continuity | Prediction gate and bounded track lifetime | Coverage and ID switches on a controlled one-gap scene |
| Explainable review | Source crop, morphology, frame count, residual, alignment warning | Judge can trace track to actual observations |
| Noise robustness | Local background estimate, modest denoising, configurable thresholds | Precision/recall under fixed noise tiers |
| Camera-awareness | Transform estimation, quality checks, original-coordinate export | Alignment and localization error on held-out jitter cases |

These are hypotheses to test. A feature stays only if it works or contributes an honest diagnostic. No metric improvement is guaranteed by this plan.

## Stop rules

- No GPU/model-training dependency before a CPU pipeline works.
- No advanced dataset integration while synthetic tracking is broken.
- No hard 3D orbit animation before measurable core functionality.
- Freeze the interface after hour 2 and scope at hour 18.
- At hour 10, if alignment is unreliable, restrict the supported mode and display a warning; do not report transformed raw coordinates as accurate.
