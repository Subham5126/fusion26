# OrbitTrace CV-T14 — judge feedback evidence

Implemented and tested local CV diagnostics, not deployed backend functionality.
Authoritative current evidence: artifacts/reports/cv_t14/final_review/index.html
and summary.json. Every display uses actual images and program output. Controlled
synthetic cases are labelled synthetic and separate from ESA source samples.

## Five objects, then three: how association works

Actual CV-T04 detections for counts_change: **[5,3,4,5,5]**. The unchanged Member3
tracker uses gated minimum-cost assignment, unmatched cases, constant-velocity
prediction after two observations, three-observation confirmation and retirement
after more than two missed frames. The actual gate is **20px**, not 15px.
It recovered the scripted one-frame and two-frame gaps, retained five confirmed
tracks, and produced 17 correct identity-resolvable links, zero wrong links,
zero switches and zero fragmentation. Raw and registered streams both passed
on this small-motion example. Predictions were not treated as observations.

Open counts_change/tracking_registered.png to see actual Member3 track IDs and
observed trails. candidates.png displays rendered truth separately for scoring.
Do not use changing detection counts as evidence of debris classification.

## What happens with a daylight upload?

The standalone pixel validator returns supported/unsupported/uncertain with
reasons; API integration is a proposal requiring Member1. It checks dimensions,
dtype, clipping, brightness quantiles/occupancy, contrast features, noise, blur
and frame consistency. It does not use one mean-intensity cutoff.

The **synthetic daylight-like** scene returned unsupported with broad_bright_field
and low_feature_evidence. Inference was not run; detection JSON is null and the
overlay states INFERENCE NOT RUN. This is a profile mismatch diagnostic, not
"no debris". No sufficiently labelled independent real daylight/cloud negatives
are available. No real daylight classification accuracy is claimed. Controlled
labels agree with output on all 11 authored cases; renderer and rules were
developed together, so this is a demonstration rather than independent accuracy.

Actual ESA train/84, train/438 and test/1107 all returned supported. Supported
means usable telescope-profile input, not successful detection of all targets.
Valid star backgrounds with no targets remain supported; low features are
uncertain, never silently certified empty.

## How does noise avoid becoming debris?

CV-T04 shape/context/hot-pixel/noise gates remain frozen; quality is an
uncalibrated candidate score. The five **synthetic iid noise** frames produced
zero candidates in an explicitly marked uncertain-guard diagnostic bypass.
Production-style validator behavior would request review rather than declare
empty success. These five frames do not prove universal noise rejection.

A deliberately persistent compact artifact produced **five unmatched detections
and one false confirmed track** across five frames. In a deliberately blurred
scene, bypassing the uncertain validator produced **280 false detections and
56 false confirmed tracks**. The blur rule flagged possible_blur, so normal
guarded processing would block it. These failures show why track confirmation
and candidate confidence cannot certify physical debris identity.

## Camera motion, crossings and missing objects

| Controlled case | Actual candidate counts | Registered TP/FP/FN | Association outcome |
|---|---|---|---|
| counts_change | 5,3,4,5,5 | 22/0/0 | 5 confirmed; 2/2 gaps recovered; 0 switches/fragments |
| entry_exit | 2,2,2,2,2 | 10/0/0 | 3 distinct tracks, 2 finally confirmed; entry/exit represented |
| crossing | 2,2,1,2,2 | 9/0/1 | 6 correct scored links; coincident truth excluded at crossing |
| nearby (4px) | 0,0,0,0,0 | 0/0/10 | Both targets suppressed; association fraction undefined |
| camera_motion | 5,8,5,5,6 | 25/4/0 | Raw 20 switches/20 fragments; registered 0/0 |
| artifacts | 6,6,6,6,6 | 25/5/0 | 1 false confirmed track |
| empty_targets | 0,0,0,0,0 | 0/0/0 | 0 tracks; undefined detection precision/recall |
| registration_failure | 5,5,0,5,5 | registered blocked | Raw diagnostic recovered 5/5 blank-frame gaps |
| noise_only | 0,0,0,0,0 | registered blocked | Raw diagnostic 0 candidates/tracks |
| daylight_like | inference blocked | unscored | Unsupported, no successful empty inference |
| blurred | 61,61,61,61,61 | 25/280/0 | Uncertain bypass: 56 false confirmed tracks |

All matching uses an inclusive 5px native raw-point radius. Coincident truths
within 1px are excluded from identity scoring (two observations in crossing);
one crossing track is unscorable for false confirmation. Zero scored identity
errors in nearby do NOT mean success: all ten target observations were missed.
Metric definitions/denominators are in preprocessing/ROBUSTNESS.md and each
report.json. They are diagnostic counts, not official MOT/HOTA/IDF1 scores.

Rendered camera shift is (18,8)px per frame, separate from independent target
motion. Estimated transform maximum error was **0.0083895px** on this authored
example; registered stream retained five confirmed true tracks plus four tentative
false detections. No gate tuning was performed. This is synthetic transform
agreement, not real camera-calibration accuracy.

Registration_failure has a blank frame 2: its transform is null and registered
tracking is blocked for the entire sequence. Raw-only diagnostic tracking is
explicitly separate; no mixed raw/reference fallback or fabricated identity
transform is introduced. Real ESA train/438 failed registration on frames 3/4
and was likewise blocked for registered tracking.

Real diagnostics: train/84 candidates [7,7,6,8,6], 23 raw tracks versus 31
registered tracks; train/438 [6,8,5,3,5], 26 raw tracks, registered blocked;
test/1107 [0,0,0,0,0], zero raw/registered tracks. These previously used sequences
are regression evidence, not blind test data. No persistent truth IDs are supplied
for scoring real tracking; changed track counts alone do not prove correctness.
Star alignment includes sky drift: GEO-staring targets can exceed an initial
tracking gate after compensation. No claim that registration always helps ESA.

## Wider dataset and actual trained YOLO

All requested disk sources inventoried; see CV-T14-DATASETS.md. Streak labels
describe streak morphology, not debris identity. Six invalid labels, unresolved
meaning of 746 missing label files, broken declared YAML paths and missing
license/source evidence require review. CSV classes/coordinates/rights remain
unverified. Encoded hash audit found zero cross-source/split duplicate groups;
perceptual/session leakage is untested.

Working: classical T03 and frozen CV-T04, CV-T06 adapter, T13 registration,
new internal suitability rules and synthetic diagnostic integration.
Unavailable: Torch/Ultralytics imports and any trained checkpoint under models/.
No YOLO training, model adoption, downloads or dependency installation occurred
**in CV-T14**. The concurrently created CV-T15 handoff reports an isolated runtime
and actual CPU/GPU smoke training; that separate model work was not independently
validated by this task and was left untouched. Shared .venv availability does not
describe that isolated environment. Coordinate further model work with CV-T15.
The documented plan first establishes rights, parser/label correctness, negatives
and sequence/session-disjoint splits, then obtains Member1 dependency approval
and trains/evaluates an actual model under a declared budget.

## Integration owners' next actions

Member1: approve internal-status API mapping; unsupported/uncertain must surface
reasons instead of empty successful analysis. Enforce existing bounded uploads,
package src/astrotrace, then implement/select detector and tracker in pipeline.
Subham's backend/orbittrace/pipeline.py still raises NotImplementedError.

Member3: evaluate initial association after apparent star drift with declared
profile/cadence/registration uncertainty, rather than silently widening gates;
implement a reviewed whole-sequence failure policy, quantify nearby/merged-target
ambiguity, improve nuisance rejection and end-of-field flags. Keep raw fields,
timestamps and predicted-point separation. Observe explicit missed frames; do not
interpret the track's confirmed lifecycle status as confirmed debris identity.

Recommended next task: curate real labelled hard negatives and profile-specific
tracking stress sequences, then review safe suitability-to-API and registration
failure policies with Members1/3. No shared integration change was made here.
