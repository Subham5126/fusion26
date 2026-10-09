# Handoff: CV-T04 — OrbitTrace false-positive reduction

Owner: Computer Vision and Dataset Engineer, explicitly assigned by user.
Backlog ownership: continuation of **T03 (Data/CV)**. The user calls this CV
milestone T04; repository BACKLOG T04 is tracking. This separate CV-T04 report
does not claim or change that tracking task.
Base commit: `fa593cf5052f96d311d049f2b84949f588a99407`.
Date: 9 October 2026 (Asia/Calcutta).
State: **ready_for_review**. Implementation, real development sweep, frozen
held-out regression evaluation and applicable tests completed. Integration review
and end-to-end tracking acceptance remain separate work.

## Result and measured tradeoff

An independent detector rejects one-pixel spikes and elongated raw neighborhood
support, while a lower proposal threshold restores useful faint-source recall.
T03 remains unchanged and callable. On the original 128-sequence ESA checkpoint,
precision rose from 13.21% to **39.24%**, recall from 53.67% to **58.72%**, F1 from
21.20% to **47.04%**; FP/frame fell from 6.006 to **1.548** (74.22% fewer FP).
Mean detect time increased from 61.48 to **71.84 ms** in the same evaluation run
(16.86% overhead). This is a quality improvement with additional computation,
not a demonstrated speedup or calibrated classification result.

## Exact repository files changed

Added:

- `src/astrotrace/detection/diagnostics.py`
- `src/astrotrace/detection/optimized.py`
- `src/astrotrace/preprocessing/optimized_candidates.py`
- `scripts/spotgeo_optimize.py`
- `tests/detection/test_optimized.py`
- `src/astrotrace/detection/OPTIMIZATION.md`
- `docs/handoffs/CV-T04.md`

Updated: `src/astrotrace/detection/README.md` (links to the optional detector and
this report; original T03 instructions/measurements retained).

No edits to backend, frontend, tracking, schemas, root config/dependencies,
lockfiles, STATUS or BACKLOG. No packages/imports were renamed. No downloads,
training, branch creation, commits, pushes or automatic delegation occurred.
Previous T14/T03 uncommitted modules, tests, scripts and handoffs remain; these
are not new CV-T04 work. The pre-existing PROBLEM_STATEMENT edit was preserved.

Generated evidence is under already-gitignored `artifacts/reports/`:

- `cv_t04_analysis/`: preserved hashes/config, original development predictions,
  candidate features/quantiles, image hashes, 24 original five-frame overlays,
  and `feature_examples.png` (separately generated native-intensity crop montage).
- `cv_t04_development/`: retained incomplete first attempt; not final evidence.
- `cv_t04_development_v2/`: declared experiment plan, all 35 trial JSON files,
  completed development.json, frozen selected_config.json, selected predictions,
  image hashes, 24 selected overlays and precision_recall.svg.
- `cv_t04_evaluation/`: frozen evaluation plan, benchmark.json, both detector
  predictions, 640 original PNG hashes, six selected held-out overlays,
  reproduction_audit.json and match_change_audit.json.
- `cv_t04_inference84/`: image-only detections.json/candidates.png example.

`git check-ignore` confirmed the analysis/config/benchmark paths. No ESA pixels
are added to Git. Panels are local inspection evidence, not redistributed data.

## Baseline preservation, dataset and split provenance

Read root AGENTS, STATUS, PROJECT_BRIEF, CONTRACTS, TEAM, architecture, role/task
guidance, dataset/detector docs, T03 handoff, existing implementation/tests and
historical benchmark before changing the algorithm. Source is the actual local
extracted root **data/raw/SpotGEOv2**, not the absent spotgeo_v2 spelling.
Existing T03 validation decoded all 32,000 images at 640x480 grayscale uint8;
that is historical validation, not an exhaustive rerun this milestone.

CV-T04 reloaded and decoded 120 development frames and 640 held-out frames,
validated exact dimensions/order/types via the existing loader, reparsed both
annotation files via content/split membership, and used unchanged original-image
coordinates. Train contains 325 empty sequences, test 1,301 in the prior full
audit. The selected held-out sample has 36 empty sequences / 180 empty frames.
All development image hashes match the analysis snapshot; all 640 held-out PNG
hashes exactly match the T03 manifest. Annotation SHA-256 is unchanged:

- train: `2727e7c21f1fef229b024dcb00952d0781057661c4ccb64937dce50f08e1fdfe`
- test: `8c3e141fba0b5d3ed220563b458a17b17d73ec8cc762aa46abe40d1016f557f4`

Whole-sequence seed-26 T03 membership is reused unchanged: 24 official train
sequences for development (120 frames / 255 labels), 128 official test sequences
for evaluation (640 frames / 1,090 labels). No held-out frames/cases were used
for CV-T04 tuning. T03 aggregate accuracy was already known; this is therefore
an unchanged **regression set, not a fresh blind test**. Capture-session
independence and semantic near-duplicates remain unverified. Original archive
identity/checksum is still unverified; the local source is user-supplied v2 and
dataset_version stays unknown. Existing ESA/Zenodo CC BY 4.0 attribution from
T14 is retained; no new data acquisition or external code/weights adoption.

`baseline_snapshot.json` froze hashes of baseline.py, interface.py, runner.py,
evaluation.py, preprocessing/candidates.py, spotgeo_baseline.py and historical
benchmark/membership/selected-config JSON before optimization. Every source and
report hash remained unchanged. Baseline rerun detections (coordinates, scores,
boxes, IDs, evidence and warnings, excluding timing) match historical predictions
**exactly on all 128 sequences**, not just their aggregate accuracy.

Key reproducibility hashes:

- original membership: `9ee29f756f71028197aa503984244f23460836638293490432cbed2afb446d63`
- original benchmark: `d06cb2c81cd775687e64d72cd4b4381bc4707230b54fcb4e4465671cccaa0319`
- CV selected config: `66f47213bb37ddd825565cd405a43e694d0e8274b4ab834883d82986c78e976b`
- CV benchmark: `76a1d4c00176d277ed10f63d5ee592a9345dc7b58fe619a1ab85d77ecf979327`

Individual new module/script hashes are in experiment_plan.json,
selected_config.json and benchmark.json. Evaluate rejects changed algorithm code
after the development freeze. No parameters or algorithms changed after observing
held-out outcomes. Test/documentation additions do not alter detector code.

## False-positive analysis and algorithms tested

Baseline development: 127 TP, 796 FP, 128 FN. Evaluation-only crop/feature
inspection grouped FP by image evidence: 116 had raw_peak_fraction >0.55;
549 additional FP had contextual elongation >2.5; 131 remained outside those
groups. These are ordered image-feature groups, not certified physical classes.
Zoomed crops show isolated bright pixels in the first group and faint streak
wings/fragments in the second. Entire-sequence overlays inspected include
train/84 and train/438. Targets and adjacent bright streaks can overlap; some
label positions have little visible signal. Median aperture SNR heuristic was
15.90 for TP, 10.78 for FP, 6.30 at missed labels. Median contextual elongation
was 1.27 for TP versus 3.41 for FP. FN diagnostics use labels only after
inference and are explicitly not predicted observations.

The new module reuses original normalization, proposal response, adaptive mask,
component extraction, centroid, area/elongation and shared Detection construction.
Added raw-image local features:

- Median background/MAD noise from a 3.5..6.5 px annulus in a clipped 15x15 patch.
- Signed radius-2.5 aperture sum divided by noise times sqrt(aperture area),
  with half-quantization noise floor; uncalibrated SNR heuristic.
- Brightest positive pixel fraction of local core sum to reject isolated spikes.
- Raw >2-noise support around the core peak, connected within radius 6.5;
  weighted covariance elongation includes faint wings absent from proposal mask.
- Component-box aspect and original area/score gates.
- Optional step-2/4 coarse broad background and local variance maps, sampled
  back to native dimensions. Original mask/centroid pixels are never resized.

No per-image min/max stretching in inference, temporal subtraction/association,
truth-assisted proposals, morphology erasing faint targets or learned classifier.
Visualization alone stretches intensities. Original T03 heuristic quality stays
`(1-exp(-peak_snr/8))/max(1,component_elongation)`; all added evidence is finite.
Scores, SNR and covariance shape are not calibrated probabilities or physical
PSF measurements. Final cap is applied after filtering (bounded 2,000-proposal
work ceiling). No selected development/held-out frame hit either cap; maximum
selected counts were 8 and 14/frame respectively, with zero warning frames.

## Development experiments and selection

The plan was persisted before trials. 35 real-data configurations: unchanged
T03; seven independent area/aspect/spike/context/SNR/score/coarse-map ablations;
24 combinations of map step 1/4, threshold 3.5/4.5/5.5/6.5, context elongation
2/2.5/3 with peak_fraction<=.55; three SNR>=8 combinations. Selection maximized
development F1 subject to recall >=90% of T03's 0.4980392 recall
(floor **0.4482353**), then precision, then fixed grid order.

Representative measured trials (all 120 frames, localization matched-only):

| Variant | Precision % | Recall % | F1 % | FP/frame | RMSE px | Mean ms |
|---|---:|---:|---:|---:|---:|---:|
| Original T03 | 13.76 | 49.80 | 21.56 | 6.633 | 0.6275 | 65.03 |
| Coarse maps only, step 4 | 13.33 | 49.41 | 21.00 | 6.825 | 0.6308 | 45.94 |
| Area 4..50 only | 16.33 | 43.92 | 23.80 | 4.783 | 0.5144 | 63.98 |
| Aspect <=1.5 only | 14.69 | 46.27 | 22.31 | 5.708 | 0.6442 | 64.28 |
| Peak fraction <=.55 only | 15.74 | 49.80 | 23.92 | 5.667 | 0.6275 | 65.61 |
| Context elongation <=2.5 only | 33.33 | 47.45 | 39.16 | 2.017 | 0.3012 | 60.71 |
| Aperture SNR >=8 only | 15.73 | 47.06 | 23.58 | 5.358 | 0.5031 | 70.91 |
| Score >=.45 only | 35.31 | 41.96 | 38.35 | 1.633 | 0.2787 | 69.75 |
| Combined step1 / threshold3.5 / context2 | 12.47 | 61.96 | 20.76 | 9.242 | 0.3996 | 101.73 |
| **Combined step1 / threshold4.5 / context2** | **43.57** | **54.51** | **48.43** | **1.500** | **0.3041** | **22.28** |
| Combined step1 / threshold5.5 / context2 | 56.72 | 44.71 | 50.00 | 0.725 | 0.2854 | 20.78 |
| Combined step1 / threshold6.5 / context2 | 63.09 | 36.86 | 46.53 | 0.458 | 0.2842 | 20.16 |
| Combined step4 / threshold4.5 / context2 | 42.51 | 54.51 | 47.77 | 1.567 | 0.3086 | 17.36 |
| Step4 / threshold4.5 / context2.5 / SNR>=8 | 43.23 | 51.37 | 46.95 | 1.433 | 0.3062 | 17.33 |

The nominal highest F1 trial (threshold5.5/context2) failed the declared recall
floor: 114/255 TP vs required >=115/255. Higher precision at threshold6.5 lost
too much recall. Threshold3.5 admitted numerous compact noise fragments.
Area/aspect alone weakly separated targets; area and score-only choices lost
recall. Contextual wings were the strongest individual separator. SNR gates
suppressed useful faint detections without improving selected F1. Coarse maps
offered a measured development latency alternative but slightly lower F1;
they are implemented/tested but **not enabled in the final configuration** and
have no separately measured held-out performance claim.

Development latency changed sharply during the run (early ~60–100 ms versus
later ~15–25 ms), so its numbers are measured wall time, not reliable paired
speedup evidence. A brief unit-test run and local image diagnostics also occurred
during development. Final runtime comparison is the same-session alternating
held-out run below; no validation/test jobs ran concurrently with that benchmark.

Selected explicit settings:

```python
{
    "denoise_sigma": 0.6, "background_sigma": 8.0, "noise_sigma": 12.0,
    "threshold_sigma": 4.5, "min_area_px": 3, "max_area_px": 150,
    "max_elongation": 2.5, "max_candidates": 200, "background_step": 1,
    "min_aperture_snr": 0.0, "max_peak_fraction": 0.55,
    "max_context_elongation": 2.0, "max_component_aspect": 20.0,
    "min_score": 0.0
}
```

This yielded development TP139 / FP180 / FN116. Defaults intentionally differ
(threshold5.5/context2.5); use the explicit selected mapping for these results.
All 35 measured trial metrics/configs and the
[PR plot](../../artifacts/reports/cv_t04_development_v2/precision_recall.svg)
are available locally.

## Frozen held-out regression results

Inclusive 5-pixel Euclidean raw-coordinate gate, same-frame maximum-cardinality
one-to-one matches followed by minimum distance; explicit unmatched cases.
Counts pooled over all frames, including empty scenes. Localization uses matched
predictions only. No cross-frame annotation-index identity assumption or official
ESA challenge score.

| Measurement: 640 frames / 1,090 labels | Unchanged T03 rerun | Selected CV-T04 |
|---|---:|---:|
| TP / FP / FN | 585 / 3844 / 505 | 640 / 991 / 450 |
| Precision | 13.2084% | 39.2397% |
| Recall | 53.6697% | 58.7156% |
| F1 | 21.1995% | 47.0415% |
| Matched mean localization error | 0.2808 px | 0.2860 px |
| Matched localization RMSE | 0.3844 px | 0.3621 px |
| False positives/frame | 6.00625 | 1.54844 |
| FP/empty frame, 180 frames | 3.9000 | 1.0167 |
| Mean detect time | 61.4762 ms | 71.8400 ms |
| p95 detect time | 74.3708 ms | 90.6706 ms |

All T03 accuracy values match its historical results exactly. Historical T03
mean time was 53.9938 ms during concurrent exhaustive validation; use the
**61.4762 ms same-session rerun** for the optimization's 16.86% runtime overhead.
Timing surrounds actual detect calls (preprocessing/features/shared schema),
excludes IO/namespacing/plotting/evaluation, uses one OpenCV CPU thread and
alternates method order by sequence. This is a single wall-time comparison, not
an isolated/repeated latency confidence study.

546 frame-label matches were retained, 94 recovered and 39 lost relative to
T03, net +55 TP. These are same-frame annotation indices for evaluating match
changes, never persistent identities. Thus higher aggregate recall does not mean
every faint target survived. Lower RMSE also compares changed match populations;
mean error increased slightly. Remaining FP991 and FN450 are material limits.
No synthetic-only accuracy is mixed into these real-data metrics.

Reports: [benchmark](../../artifacts/reports/cv_t04_evaluation/benchmark.json),
[selected config](../../artifacts/reports/cv_t04_development_v2/selected_config.json),
[development](../../artifacts/reports/cv_t04_development_v2/development.json),
[preservation audit](../../artifacts/reports/cv_t04_evaluation/reproduction_audit.json).

## Actual commands, tests and failures

All Python commands used `.\.venv\Scripts\python.exe` (Python 3.12.14).

| Command/check actually run | Actual outcome |
|---|---|
| `python -u scripts/spotgeo_optimize.py analyze --output artifacts/reports/cv_t04_analysis` | Exit0; all 24 real development sequences decoded; baseline metrics/features, original panels/hashes saved |
| First `develop ... --output artifacts/reports/cv_t04_development` | Exit2: exclusive JSON writer rejected repeated development.json progress write; partial output retained |
| Logger corrected to new per-trial files; `python -u scripts/spotgeo_optimize.py develop --analysis artifacts/reports/cv_t04_analysis --output artifacts/reports/cv_t04_development_v2` | Exit0; all35 trials completed; selected config frozen before held-out inference |
| Initial `pytest ... tests/detection/test_optimized.py` | 32 passed, 1 failed: NumPy lazy assertion import accessed package metadata under the test's filesystem guard; inference itself had completed without IO |
| Assertion changed to eager `np.array_equal`; targeted test rerun | 33 passed in0.41s; detector unchanged |
| `python -u scripts/spotgeo_optimize.py evaluate --analysis artifacts/reports/cv_t04_analysis --development artifacts/reports/cv_t04_development_v2 --output artifacts/reports/cv_t04_evaluation` | Exit0; all128 sequences /640 unchanged PNGs, both detectors evaluated, table above |
| `python scripts/spotgeo_optimize.py detect --split train --sequence 84 --config artifacts/reports/cv_t04_development_v2/selected_config.json --output artifacts/reports/cv_t04_inference84` | Exit0; [7,7,6,8,6] candidates; annotations_read=false; candidate JSON/PNG saved |
| Added independent aspect/area test; `python -m pytest -q -c backend/pyproject.toml` | **175 passed, 0 failed in20.82s**, one existing Starlette/httpx deprecation warning;34 new tests plus141 previous tests |
| Original prediction audit, excluding timing | Exact equality on128 sequences; all preserved file hashes also unchanged |
| Installed runtime metadata/license check | Existing NumPy2.5.3, OpenCV wheel4.14.0.94 (cv2 4.14.0), SciPy1.18.1, Pillow12.3.0, Pydantic2.14.0; no installation/new requirements |
| Generated result ignore check | analysis/config/benchmark paths ignored |
| `python -m compileall -q` on all new Python modules/script/tests | Exit0 |
| `python -m pip check` | No broken requirements found |
| `python scripts/check_docs.py` | 50 local links in54 Markdown files resolved |
| Owned-file whitespace/link/frozen-hash verification | 8 changed files,16 owned-document links,0 issues; original T03 and selected algorithm hashes verified |
| `git diff --check` | Passed; Git only noted pre-existing PROBLEM_STATEMENT line-ending normalization |

Tests cover multiple thresholds, area/aspect/context shape, isolated spike versus
spread source, noise-only and constant frames, faint independently moving target,
multiple and boundary/subpixel targets, dtype coordinate agreement, valid finite
shared schema/evidence, unchanged T03 geometry with disabled gates, repeatability,
no image mutation/no disk or label access, final cap after rejection, five-frame
output/unique proposal IDs, malformed images and bounded/unknown config keys.
Tests use tiny generated NumPy images, not full ESA dependencies. Full suite also
retains prior safe ZIP/decoding/annotation/matching/contract/API bootstrap checks.

## Tracking handoff and reproducible call

Full guide with module inputs/outputs, config bounds, CLI options, failure modes
and reproduction commands: [OPTIMIZATION.md](../../src/astrotrace/detection/OPTIMIZATION.md).
Existing Python environment and backend shared schemas are reused. For direct
PowerShell imports set `$env:PYTHONPATH="E:\Fusion\src;E:\Fusion\backend"`.
No new dependencies: OpenCV headless Apache2, NumPy's installed multi-license
metadata, SciPy BSD/bundled notices, Pillow MIT-CMU and Pydantic MIT.

Exact unchanged signature:
`OptimizedDetector.detect(pixels: np.ndarray, context: FrameContext,
config: Mapping[str,object]) -> list[app.schemas.result.Detection]`.
Call `detect_optimized_sequence(sequence, config) -> SequenceDetections` for
existing five-frame validation, timing, warnings and namespacing. The original
runner validates only baseline keys; the new helper binds extra filter parameters
behind it. Direct `.detect` accepts the full extended numeric mapping. There is
no shared interface/API contract change and none is requested.

Small real-data invocation without dependence on ignored config files:

```python
from astrotrace.datasets import SpotGeoDataset
from astrotrace.detection.optimized import OptimizedConfig, detect_optimized_sequence

sequence = SpotGeoDataset("data/raw/SpotGEOv2", split="train").load_sequence(84)
config = OptimizedConfig(threshold_sigma=4.5, max_context_elongation=2.0).to_dict()
result = detect_optimized_sequence(sequence, config)
by_frame = [list(frame.detections) for frame in result.frames]
```

Input: nonempty 2D uint8/uint16 or normalized float32/64 [0,1], bounded at4M
pixels, context dimensions must match; unknown timestamps None. Zero proposals
returns []; invalid arrays/context/config raise ValueError. All proposals are
original-image fractional x/y, top-left origin and integer pixel centers; box
upper limits exclusive. No half-pixel adjustment or axis swap. Reference fields
are None until registration. Helper metadata supplies sequence ID and coordinate
system; each Detection provides original schema fields and finite local evidence.

Actual train/84 first proposal (selected fields; full nullable fields/evidence in
cv_t04_inference84/detections.json):

```json
{
  "sequence_id": "84",
  "split": "train",
  "coordinate_system": "raw_top_left_xy_px_integer_centers",
  "score_type": "uncalibrated_heuristic",
  "detection": {
    "detection_id": "sc0ce3e0d9b28b19f-f0-c0",
    "frame_index": 0,
    "x_raw_px": 61.35224346723875,
    "y_raw_px": 427.97201121585204,
    "bbox_raw_px": [59.0, 426.0, 65.0, 431.0],
    "quality_score": 0.8320982666451765,
    "kind": "compact",
    "detector_name": "opencv_context_filtered_v2",
    "x_reference_px": null,
    "y_reference_px": null
  }
}
```

IDs are unique frame-specific proposal ranks, not persistent object IDs. Tracking
must create identities from image-derived geometry; predictions/interpolations
must never become observed detections. Inference reads pixels/context only;
labels, file paths and ground-truth coordinates are never passed to it.

## Failures, limitations and next dependencies

Selected development overlays inspected include train/84; held-out test/57 was
inspected only after the freeze/evaluation. Train/84 still misses overlapping or
very faint labels. Test/57 frame4 retains11 FP, showing remaining streak/noise
fragments despite improved overall precision. Label positions may be unobservable
in a single frame, but still incur FN. Compact stars, hot-pixel neighborhoods and
noise peaks can pass; no physical identity claim is supported.

Short/smeared/overlapping or unusually narrow targets may fail new gates; local
ring contamination and near-border clipping bias shape/SNR. Matching lost39
formerly matched label positions. Quality is uncalibrated and raw-image only;
camera motion, alignment, temporal confirmation and track metrics remain other
owners' work. Runtime increased; the optional coarse-map path requires separate
fresh validation before replacing the final choice in production.

Recommended next work: freeze a fresh sequence-level validation set (prefer
capture-session grouping if metadata exists); audit faint/overlap/border misses
and the39 match losses; assess repeat-run latency at the tracking pipeline's CPU
budget; coordinate registration/temporal confirmation with their owners. Retain
these T03/CV-T04 checkpoints rather than tune further on this held-out set.
Integration owns package/pipeline/health/config wiring and STATUS/BACKLOG updates.
No shared changes are requested. This detector improvement does not complete
tracking T04 or the overall end-to-end P0 prototype.
