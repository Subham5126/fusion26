# OpenCV compact candidate baseline (T03)

The optional OrbitTrace [CV-T04 context-filtered detector](OPTIMIZATION.md)
preserves this T03 implementation and its measurements. See that guide and the
[CV-T04 handoff](../../../docs/handoffs/CV-T04.md) for integration and comparisons.
The [Member 3 guide](MEMBER3.md) and [CV-T05 handoff](../../../docs/handoffs/CV-T05.md)
provide verified real samples and current tracking/backend readiness.

Implemented: independent CPU single-frame proposals, five-frame inference,
candidate panels, separate development/held-out point evaluation, a minimal
comparator and CLI. T14 loading is reused; interface.py, shared schemas and
backend/frontend/tracking stay unchanged. Candidates do not certify GEO/debris
identity. No registration, cross-frame identity, tracking or training occurs.

## Exact callable interface

Put src on PYTHONPATH; install the existing backend for its shared Detection type.
The CLI bootstraps both source paths without modifying packaging.

```python
from astrotrace.datasets import SpotGeoDataset
from astrotrace.detection.baseline import OpenCVBaselineDetector, BaselineConfig
from astrotrace.detection.interface import FrameContext, Detector
from astrotrace.detection.runner import detect_sequence

sequence = SpotGeoDataset("data/raw/SpotGEOv2", split="test").load_sequence(10)
detector: Detector = OpenCVBaselineDetector()
config = BaselineConfig(threshold_sigma=5.5, denoise_sigma=0.6, max_elongation=2.5).to_dict()
frame = sequence.frames[0]
context = FrameContext(frame.frame_index, frame.width_px, frame.height_px, "spotgeo", frame.timestamp_s)
detections = detector.detect(frame.pixels, context, config)  # list[existing Detection]
result = detect_sequence(sequence, detector, config)  # optional five-frame wrapper
payload = result.to_dict()
```

The agreed signature remains `detect(pixels: np.ndarray, context: FrameContext,
config: Mapping[str,object]) -> list[app.schemas.result.Detection]`. No proposals
returns []; invalid input/context/config raises ValueError. Input arrays are never
mutated and detection has no filesystem or annotation access. Accept nonempty
2D uint8/uint16, or finite normalized float32/64 in [0,1], up to 4,000,000 pixels.
Context dimensions must agree. Unknown timestamps remain None. Undeclared config
keys, including paths/truth, are rejected. Each call is stateless.

The wrapper returns a local SequenceDetections with sequence_id, split, five
FrameDetections, timings and warnings. Its JSON is a local evidence envelope,
not a replacement AnalysisResult/API schema. sequence_id and coordinate_system
are inherited from the envelope; each existing Detection contains frame_index,
detection_id, x_raw_px, y_raw_px and quality_score. Reference coordinates are None.
IDs include a split/sequence hash and frame-specific proposal rank; they are unique
within the sequence and do not establish persistent cross-frame identity.

## Algorithm and coordinate handling

1. Normalize unsigned grayscale by dtype maximum into a new float32 image. Float
   inputs must already be [0,1]. No min/max stretching is used for inference.
2. Mild Gaussian denoising (default sigma 0.8 px) minus broad Gaussian background
   (sigma 8 px) enhances compact peaks and subtracts smooth illumination. No
   temporal median or morphological opening is used to erase slow/faint sources.
3. Global noise is `1.4826 * median(abs(response-median(response)))`, floored at
   half the native quantization step. A Gaussian window (sigma 12 px) estimates
   local RMS after clipping residuals to +/-3 global noise scales. Local noise
   is floored at half the global scale.
4. Threshold `response > threshold_sigma * local_noise`, then use OpenCV
   8-connected components. Compute positive-response-weighted centroids and boxes.
5. Filter area (default 3..150 pixels) and elongation (default <=4). Elongation is
   the square root of the weighted covariance eigenvalue ratio after adding
   1/12 px² quantization variance. Long streaks generally fail; fragments can pass.
6. Sort by score then raw y/x; cap at 200/frame. CandidateLimitWarning reports
   truncation; the wrapper records it. No held-out frame reached this cap.

`peak_snr_heuristic = max(response/local_noise)` over component pixels.
`quality_score = (1-exp(-peak_snr_heuristic/8))/max(1,elongation)`.
This finite [0,1] heuristic rewards contrast/compactness; it is not a calibrated
probability. Evidence contains area_px, elongation and peak_snr_heuristic. kind is
compact for elongation <=2, otherwise unknown.

The native grid is unchanged: top-left origin, x right, y down, NumPy [y,x],
integer pixel centers. No axis swap, half-pixel shift, resizing or registration
is applied. Boxes have exclusive upper limits and contain the centroid. Dtype
quantization floors may slightly change component boundary pixels; tests verify
subpixel agreement for equivalent uint8/uint16/float intensities.

BaselineConfig validates all declared numeric parameters and rejects unknown
keys. It is worker-owned and changes no root config. MinimalThresholdDetector
uses median/MAD global thresholding, no denoising/local background model, the same
component/centroid code, and benchmark area 3..1000 / elongation <=20. Both methods
use the same proposal cap and get development-only threshold selection.

Primary references: [OpenCV filtering](https://docs.opencv.org/4.x/d4/d13/tutorial_py_filtering.html),
[components](https://docs.opencv.org/4.x/d3/dc0/group__imgproc__shape.html),
[SciPy assignment](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html).
Original implementation uses already-installed CPU dependencies; no third-party
detector/weights were adopted. See [dataset guide](../datasets/README.md) for
Python setup, versions and license attribution.

## Module inputs and outputs

| Module | Inputs | Outputs / scope |
|---|---|---|
| baseline.py | pixels, FrameContext, declared mapping | existing Detection objects; main detector and comparator |
| runner.py | image-only Sequence, Detector, config | five FrameDetections and local finite JSON envelope |
| evaluation.py | saved predictions and separate labels; radius | one-to-one point matches and pooled metrics; no inference imports it |
| visualization.py | Sequence, predictions, optional labels | five native-grid PNG panels; green candidates, optional red GT |
| scripts/spotgeo_baseline.py | validate/detect/benchmark CLI | new local result directories; exit 0 or error/missing exit 2 |

## Reproducible commands

From E:\Fusion, use existing Python 3.12 .venv. artifacts/reports is already
ignored by Git. All output directories must be new; previous evidence is preserved.
The CLI explicitly sets OpenCV to one CPU thread; the library changes no global
OpenCV settings.

```powershell
.\.venv\Scripts\python.exe scripts/spotgeo_baseline.py validate --output artifacts/reports/new_validation
.\.venv\Scripts\python.exe scripts/spotgeo_baseline.py detect --source data/raw/SpotGEOv2 --split test --sequence 10 --config artifacts/reports/t03_spotgeo_benchmark/selected_config.json --output artifacts/reports/new_inference10
.\.venv\Scripts\python.exe scripts/spotgeo_baseline.py benchmark --source data/raw/SpotGEOv2 --output artifacts/reports/new_benchmark --development-count 24 --heldout-count 128 --radius-px 5 --seed 26
.\.venv\Scripts\python.exe -m pytest -q -c backend/pyproject.toml tests/detection
```

If ESA data is missing, use the existing synthetic fixture explicitly:

```powershell
.\.venv\Scripts\python.exe scripts/spotgeo_baseline.py detect --source data/synthetic/spotgeo_fixture --fixture-size --sequence 1 --output artifacts/reports/new_synthetic_inference
```

validate discovers a unique extracted train/test root within two folder levels
of data/raw unless --source is supplied. Actual local name is SpotGEOv2, not
spotgeo_v2. Root JSON contents must match the split ID set: filenames are not
assumed. It writes validation.json, image_hashes.json and GT panels including
empty examples. Missing data writes a concrete missing report and exits 2; no
automatic download occurs. Original archive MD5/version identity is unverified.

The actual full validation completed successfully: 32,000 frames, all 640x480
uint8, zero failures, 1,626 empty sequences across both partitions. See the
[validation report](../../../artifacts/reports/t03_spotgeo_validation/validation.json).
Exact PNG hash comparison found no shared files across train/test and no shared
complete sequences between the selected development/held-out samples; semantic
near-duplicates and capture-session correlation were not audited.

detect writes detections.json/candidates.png and prints annotations_read=false.
It reads images only. --config accepts a <=64 KiB JSON object containing a numeric
mapping, or selected_config.json;
without it, validated defaults apply, which differ from the selected benchmark.

benchmark freezes membership.json and parameter grids before tuning, then writes
development.json, selected_config.json, benchmark.json, predictions.json,
heldout_image_hashes.json and two comparison panels. The main grid contains 12
combinations: threshold 3.5/4.5/5.5, denoise 0.6/0.9, elongation 2.5/4.0. Comparator
thresholds are 3.5/4.5/5.5. Selection maximizes development F1, then precision, then
fixed grid order. The selected configuration is persisted before held-out image
inference. Reports must not be used to tune against that held-out checkpoint.

## Actual held-out ESA benchmark

9 October 2026: seed 26 uniformly selected 24 official train sequences (120
frames) for development and 128 official test sequences (640 frames) for held-out
evaluation. All five frames stay together. Numeric IDs are split-scoped: train/10
and test/10 are different sequences. The held-out sample includes 36 empty
sequences (180 frames). Source is local ESA imagery, not synthetic results.

Match radius is inclusive Euclidean distance of 5 raw pixels. Explicit unmatched
assignment first maximizes valid one-to-one matches, then minimizes distance.
Counts are pooled before ratios. Localization uses matched points only; false
positives/frame includes empty scenes. Undefined ratios/errors are null with a
reason. This is a local per-frame detection metric, not official ESA challenge
scoring or a tracking metric. Labels can include unobservable frame positions;
this single-frame detector still incurs false negatives for them.

| Held-out measurement | OpenCV compact | Minimal global threshold |
|---|---:|---:|
| TP / FP / FN | 585 / 3844 / 505 | 77 / 7774 / 1013 |
| Precision | 13.2084% | 0.9808% |
| Recall | 53.6697% | 7.0642% |
| F1 | 21.1995% | 1.7224% |
| Mean matched localization error | 0.2808 px | 0.5808 px |
| Matched localization RMSE | 0.3844 px | 1.0025 px |
| False positives / frame | 6.0063 | 12.1469 |
| False positives / empty frame | 3.9000 | 7.8111 |
| Mean detect call | 53.9938 ms | 20.7309 ms |
| p95 detect call | 72.7233 ms | 28.8907 ms |

Selected OpenCV: threshold=5.5, denoise=0.6, background=8, noise window=12,
area=3..150, elongation<=2.5, cap=200. Comparator: threshold=5.5, area=3..1000,
elongation<=20, cap=200. Timing includes preprocessing and Detection construction,
excludes loading/wrapper ID namespacing/evaluation, and was measured while full
validation ran concurrently. It is observed wall-clock call timing, not isolated
production throughput.

[Benchmark JSON](../../../artifacts/reports/t03_spotgeo_benchmark/benchmark.json),
[frozen membership](../../../artifacts/reports/t03_spotgeo_benchmark/membership.json),
[selected config](../../../artifacts/reports/t03_spotgeo_benchmark/selected_config.json),
[T03 handoff](../../../docs/handoffs/T03.md). Runtime evidence is gitignored;
teammates reproduce using the commands above.

## Tracking integration and remaining issues

Tracking receives actual per-frame Detection lists in raw pixels. Timestamp is
None, so use frame units. Proposal rank never establishes persistent identity.
Reference coordinates stay None until image-derived registration provides valid
transforms/failure states. Labels and interpolated positions never become observed
detections. Integration handles package registration, public storage tokens and
root pipeline/config/health wiring; those shared files were not edited here.

The baseline improves on the comparator but has low precision. Star fragments,
compact stars, hot pixels and cloud/noise peaks can survive. Faint/smeared targets,
targets overlapping streaks and short-streak GEO-like objects can be missed.
Bright structures bias broad background estimates. No score calibration or
identity/trajectory claim is supported.

Next: consume this interface in tracking; validate image-derived registration;
improve rejection and sensitivity using new development/validation evidence while
preserving this held-out checkpoint. Integration alone updates STATUS/BACKLOG and
backend health capability flags after review.
