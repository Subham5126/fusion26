# OrbitTrace context filtering (CV-T04)

The independent `OptimizedDetector` extends compact-source proposals with raw
neighborhood evidence. The original T03 detector, runner, preprocessing and
reports remain available unchanged. Use explicit measured settings from the
development report; class defaults are conservative starting settings.

## Tracking callable boundary

```python
import json
from pathlib import Path
from astrotrace.datasets import SpotGeoDataset
from astrotrace.detection.interface import FrameContext, Detector
from astrotrace.detection.optimized import OptimizedDetector, detect_optimized_sequence

config = json.loads(Path("artifacts/reports/cv_t04_development_v2/selected_config.json").read_text())["optimized"]
sequence = SpotGeoDataset("data/raw/SpotGEOv2", split="train").load_sequence(84)
frame = sequence.frames[0]
context = FrameContext(frame.frame_index, frame.width_px, frame.height_px,
                       "spotgeo", frame.timestamp_s)
detector: Detector = OptimizedDetector()
points = detector.detect(frame.pixels, context, config)
result = detect_optimized_sequence(sequence, config)
payload = result.to_dict()
```

Signature is unchanged: `detect(pixels: np.ndarray, context: FrameContext,
config: Mapping[str, object]) -> list[app.schemas.result.Detection]`.
The five-frame helper returns existing `SequenceDetections`. It binds the full
optimized configuration behind the original runner, which validates only baseline
keys. For extended parameters use this helper or call `.detect` directly; do not
pass them directly to the old `detect_sequence`.

Inputs: nonempty 2D uint8/uint16 or finite normalized float32/64 [0,1], maximum
4,000,000 pixels, exact context dimensions, supported acquisition profile,
finite timestamp or None. No annotations, paths, sequence memory or labels enter
the detector. Arrays are not mutated. Invalid input raises ValueError; valid
empty/constant scenes return []. Missing timestamps remain None.

Output: existing Detection objects with frame_index, opaque detection_id,
x_raw_px/y_raw_px, bbox_raw_px, kind, quality_score, detector_name and finite
evidence_statistics; optional reference coordinates/endpoints remain None.
Shared schema is 0.1.0. Sequence metadata supplies sequence_id, split,
`coordinate_system=raw_top_left_xy_px_integer_centers` and
`score_type=uncalibrated_heuristic`. The local envelope is not a public API change.
Origin is top-left, x right, y down; NumPy indexing is [y,x], integer pixel
centers, fractional centroids retained, boxes exclusive at upper bounds.

The helper namespaces IDs by split/sequence and frame. They identify individual
proposals only; ranks/IDs never establish persistent cross-frame identities.
Tracking must estimate image-derived registration independently before filling
reference coordinates. Treat timestamps as unknown and use frame units. No
debris identification, physical speed, orbit or calibrated confidence is inferred.

## Modules, algorithms and parameters

| Module | Inputs | Outputs and limitations |
|---|---|---|
| optimized.py | validated image/context/numeric mapping | stateless filtered Detection list; optional five-frame binding adapter |
| diagnostics.py | already normalized native image, validated candidate centroid/box, quantization | finite raw aperture/ring/shape evidence; internal helper trusts these preconditions |
| ../preprocessing/optimized_candidates.py | normalized native grayscale and bounded settings | response/noise maps at original dimensions; coarse-map approximation is optional |
| scripts/spotgeo_optimize.py | analyze/develop/evaluate/detect local CLI | new result directory with manifests, metrics, predictions and panels; never downloads data |

T03 proposal stages are retained: dtype-range normalization, mild Gaussian
denoising, Gaussian background subtraction, centered residual, global MAD/local
clipped RMS noise, adaptive threshold, 8-connected components, response-weighted
centroid, area and covariance elongation gates. All component coordinates remain
on the original grid. Broad filters cannot certify the physical identity of a
source.

Optional `background_step=2|4` builds broad background and local variance maps
on area-downsampled arrays and bilinearly samples maps back to the original
grid; sigmas are divided by the step. Only nuisance maps are approximated. Mild
denoising, response, mask, components and centroids retain native resolution.
Step 1 calls unchanged T03 preprocessing exactly. Coarse maps can change
component membership; they do not imply exact equality or a geometric transform.

For each proposal, a clipped 15x15 native neighborhood uses the 3.5..6.5 px ring
to estimate median background and MAD noise, floored at half the quantization
step. Radius-2.5 aperture signed contrast divided by `noise*sqrt(pixel_count)`
is `aperture_snr_heuristic`. This uses a simple independent-noise approximation;
it is not scientifically calibrated SNR. `raw_peak_fraction` is the brightest
positive-background-subtracted core pixel divided by the positive sum within
|dx|,|dy|<=1.5 px; high concentration flags spikes. Low-threshold raw support above
2 ring-noise scales within radius 6.5 is connected to the brightest core pixel.
Its contrast-minus-noise-weighted covariance eigenvalue ratio (+1/12 px²)
provides `context_elongation`; it includes wings omitted by the high proposal
threshold. This is not a fitted physical PSF. Noise, support area, raw contrast
and component-box aspect ratio are saved for diagnosis.

Gates reject proposals with excessive peak fraction, contextual elongation or
box aspect, or insufficient aperture SNR/score. Exact equality passes each gate.
Minimum/maximum area and original component elongation remain independently
configurable. The score is unchanged from T03:
`(1-exp(-peak_snr_heuristic/8))/max(1,component_elongation)`.
It is a contrast/compactness heuristic, not a calibrated probability, and is not
recalibrated after filtering. Up to 2,000 proposals receive bounded neighborhood
work; CandidateLimitWarning reports that ceiling. The caller's final cap is
applied after rejection so spikes do not consume final candidate slots. Results
keep score/y/x order and receive deterministic frame-specific ranks.

| Added setting | Accepted bounds | Starting default |
|---|---|---:|
| background_step | integer 1, 2 or 4 | 1 |
| min_aperture_snr | finite 0..100 | 0 |
| max_peak_fraction | finite 0.1..1 | 0.55 |
| max_context_elongation | finite 1..20 | 2.5 |
| max_component_aspect | finite 1..20 | 20 |
| min_score | finite 0..1 | 0 |

Inherited defaults: denoise .6 px, background 8 px, noise 12 px, threshold 5.5,
area 3..150, original component elongation 2.5, final cap 200. Unknown mapping
keys, boolean numeric settings, nonfinite or unbounded values fail. Disable
extra gates with peak_fraction=1, context/aspect=20, aperture/score=0; with
background_step=1 this retains T03 proposal geometry and score for ordinary
uncapped scenes.

## Reproduce and inspect evidence

From E:\Fusion, use the existing Python 3.12 .venv and existing backend shared
schema. No extra dependencies or root configuration changes are required.
PowerShell direct imports need `$env:PYTHONPATH="E:\Fusion\src;E:\Fusion\backend"`;
the CLI bootstraps both paths. NumPy, OpenCV headless, SciPy, Pillow and Pydantic
are already installed; versions/license attribution are in the
[T03 handoff](../../../docs/handoffs/T03.md). Original engineering code uses no
external detector/weights. Library calls leave global OpenCV thread settings
alone; CLI benchmarks set one CPU thread.

All output directories must be new, and `artifacts/reports/` is gitignored.
The completed run uses analysis, development_v2 and evaluation directories
with a cv_t04 prefix. Reproduce under different new directory names:

```powershell
.\.venv\Scripts\python.exe scripts/spotgeo_optimize.py analyze --output artifacts/reports/new_cv_analysis
.\.venv\Scripts\python.exe scripts/spotgeo_optimize.py develop --analysis artifacts/reports/new_cv_analysis --output artifacts/reports/new_cv_development
.\.venv\Scripts\python.exe scripts/spotgeo_optimize.py evaluate --analysis artifacts/reports/new_cv_analysis --development artifacts/reports/new_cv_development --output artifacts/reports/new_cv_evaluation
.\.venv\Scripts\python.exe scripts/spotgeo_optimize.py detect --split train --sequence 84 --config artifacts/reports/cv_t04_development_v2/selected_config.json --output artifacts/reports/new_cv_inference
.\.venv\Scripts\python.exe -m pytest -q -c backend/pyproject.toml tests/detection
```

Source defaults to discovered actual local `data/raw/SpotGEOv2`; override --source
with a local extracted dataset or compatible ZIP root. ESA CLI expects 640x480;
small synthetic tests call the library with explicit dimensions. Missing data
or invalid input exits 2 without fetching anything. Partial failed outputs are
retained for diagnosis; retry with a new directory. detect reads images only and
prints annotations_read=false. analyze/develop/evaluate alone load separate labels
for scoring; predictions at labels in analysis are explicitly missed-label
diagnostics, never proposal inputs or tracking observations.

Analysis freezes SHA-256 hashes of original T03 sources and reports, then writes
feature distributions, baseline predictions, PNG hashes and all 24 five-frame
development overlays. Develop verifies those hashes and freezes the search plan
before measuring 35 trials. Selection maximizes development F1 with a minimum
recall of 90% of T03's development recall; ties use precision then grid order.
There are independent area/aspect/spike/context/SNR/score/coarse-map ablations;
combined threshold 3.5/4.5/5.5/6.5, contextual elongation 2/2.5/3 and map step 1/4;
plus three aperture-SNR combinations. Entire sequences remain together.

The same original 24 official train development sequences and 128 official test
held-out sequences are used. This is a previously measured regression set, not a
fresh blind test: aggregate T03 metrics were already known. No held-out cases are
used for tuning. Freeze selected parameters and algorithm hashes before invoking
evaluate, which rejects changed code, checks every held-out PNG and the annotation
file against T03, and alternates detector execution order for timing. This does
not establish capture-session independence or rule out semantic near-duplicates.

Matching reuses maximum-cardinality, minimum-distance gated one-to-one assignment
within an inclusive radius of 5 raw pixels; unmatched cases remain explicit.
Pooled TP/FP/FN define precision/recall/F1. RMSE uses matched points only, so lower
error can reflect losing hard targets. FP/frame includes empty scenes. Undefined
values remain null with reasons. Timings measure actual detect calls including
preprocessing/features/schema construction, excluding image IO, wrapper ID
namespacing, rendering and evaluation. They are observed wall time, not a repeated
production latency study; development may have incidental local CPU activity.

Comparison panels: green TP, orange FP, magenta cross missed label. Displays use
min/max stretching only for inspection; inference always uses dtype-range
normalization. PR SVG contains measured development points and tooltip settings.

## Limits and next work

Selected measured operating point: threshold_sigma=4.5,
max_context_elongation=2.0, max_peak_fraction=.55, background_step=1; other values
are the starting defaults above. This can be reproduced as
`OptimizedConfig(threshold_sigma=4.5, max_context_elongation=2.0).to_dict()`.
On 128 unchanged ESA evaluation sequences (640 frames), precision=39.2397%,
recall=58.7156%, F1=47.0415%, FP/frame=1.54844, matched RMSE=.3621 px.
Unchanged T03 rerun: 13.2084%, 53.6697%, 21.1995%, 6.00625 FP/frame,
RMSE=.3844 px. Same-session mean detect time rose 61.48 ->71.84 ms (+16.86%).
The full suite passed 175 tests (34 new), with one existing dependency warning.
These are real-data regression measurements; synthetic arrays provide unit-test
evidence only. The alternative coarse-map configuration is not selected.

Raw shape/noise gates can remove short-streak, smeared, overlapping or unusually
narrow faint targets. A noisy local ring or adjacent streak can bias shape/SNR;
near-border apertures are clipped. Compact star fragments, sensor defects and
noise peaks can survive, and annotations are not a physical identity classifier.
Labels that are unobservable in a single frame still count as false negatives.
No camera-motion estimation, temporal association, persistent IDs, tracking,
scientific PSF calibration or large model training is performed.

Use the [CV-T04 handoff](../../../docs/handoffs/CV-T04.md) for actual settings,
development/held-out measurements, failures and test outcomes. Tracking consumes
the unchanged callable boundary; integration reviews this optional implementation
and owns packaging, public pipeline/health wiring, configs and STATUS/BACKLOG.
Next improvements require a fresh sequence-level validation set and a
faint/overlap/border failure audit; coordinate with registration/tracking owners
for image-derived alignment and temporal confirmation.
