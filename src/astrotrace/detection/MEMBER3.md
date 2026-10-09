# OrbitTrace — Member 3 detection handoff (CV-T05)

The CV-T04 detector is verified as a standalone image-only source of shared
Detection objects. The active checkout's `backend/orbittrace/tracking/__init__.py`
is a placeholder and exports no callable tracker. A byte-identical snapshot from
the already locally fetched Member 3 branch passed read-only data compatibility
on all five real samples; scientifically valid ESA tracking and backend API
integration remain unverified. The pipeline selects neither detector; the
separately authored CV-T06 standalone backend adapter defaults to CV-T04.
This guide provides real outputs for Member 3 to consume without changing the
existing detector contract or fabricating successful end-to-end processing.

## Use the existing interface

```powershell
Set-Location E:\Fusion
$env:PYTHONPATH = 'E:\Fusion\src;E:\Fusion\backend'
```

```python
from astrotrace.datasets import SpotGeoDataset
from astrotrace.detection.interface import FrameContext
from astrotrace.detection.optimized import OptimizedConfig, OptimizedDetector, detect_optimized_sequence

config = OptimizedConfig(threshold_sigma=4.5, max_context_elongation=2.0).to_dict()
sequence = SpotGeoDataset("data/raw/SpotGEOv2", split="train").load_sequence(84)
frame = sequence.frames[0]
context = FrameContext(frame.frame_index, frame.width_px, frame.height_px,
                       "spotgeo", frame.timestamp_s)
one_frame = OptimizedDetector().detect(frame.pixels, context, config)
result = detect_optimized_sequence(sequence, config)
by_frame = [list(frame_result.detections) for frame_result in result.frames]
```

Exact existing signature:
`OptimizedDetector.detect(pixels: numpy.ndarray, context: FrameContext,
config: Mapping[str, object]) -> list[app.schemas.result.Detection]`.
Existing helper `detect_optimized_sequence(sequence, config) -> SequenceDetections`
processes all five frames with validation, timings and ID namespacing. Do not pass
extended filter keys directly to the original T03 `detect_sequence`: its config
validation accepts baseline keys only. No new tracker wrapper is needed to obtain
`by_frame`. The fetched Member 3 source already implements the flat-list callable
documented below; installation/wiring into this checkout remains its owners' work.

Input pixels: nonempty native 2D uint8/uint16 or finite normalized float32/64
[0,1], maximum4M pixels, exact context dimensions. ESA samples are 640x480 uint8.
Context contains zero-based frame_index, width_px/height_px, profile="spotgeo",
timestamp_s=None. Invalid image/context/config raises ValueError. Empty detections
are normal empty lists, not failed frames; keep all five frame entries.

For saved results use the existing shared model, not dictionaries assumed to
be a new API result:

```python
import json
from pathlib import Path
from app.schemas.result import Detection

payload = json.loads(Path("artifacts/reports/cv_t05_member3/train_84/detections.json").read_text())
by_frame = [[Detection.model_validate(d) for d in frame["detections"]]
            for frame in payload["frames"]]
```

## Output and coordinate interpretation

Each Detection has the existing v0.1.0 fields: detection_id, frame_index,
x_raw_px, y_raw_px, bbox_raw_px, kind, quality_score, detector_name, nullable
reference/endpoints and finite evidence_statistics. The helper's local evidence
envelope supplies sequence_id/split, coordinate_system and score_type. It is
neither SequenceInput nor AnalysisResult and must not be sent directly as a
replacement public API contract.

Coordinates are original-image pixels: top-left origin, x right, y down,
NumPy [y,x], integer pixel centers, unrounded fractional centroids. No half-pixel
shift, axis swap, resize or alignment is applied. Boxes use exclusive upper
limits. ESA annotations preserve their original half-pixel edge bounds; annotations
are separate evaluation inputs. Native coordinate agreement was checked between
direct `.detect` and the five-frame helper on all package frames.

Reference coordinates remain null. ESA camera orientation can change across
frames. Registration must estimate raw/reference transforms from images and
report failures; do not silently fill reference coordinates with raw points or
invent identity alignment. Unknown timestamps remain null; use frame units.
Opaque proposal IDs include sequence/frame/rank, never persistent object identity.
Tracking assigns its own identities and counts actual detections as observations;
interpolated/extrapolated points must not become detections.

Quality is the unchanged heuristic
`(1-exp(-peak_snr_heuristic/8))/max(1,component_elongation)` in [0,1]. It rewards
contrast and compactness, not a calibrated probability of debris or a physical
classification. Local aperture SNR, support shape and spike concentration are
also uncalibrated. See [OPTIMIZATION.md](OPTIMIZATION.md) for formulas, bounds
and known filtering tradeoffs.

Selected config is fully recorded in the package's detector_config.json:
denoise_sigma=.6, background_sigma=8, noise_sigma=12, threshold_sigma=4.5,
area3..150, max_elongation=2.5, max_candidates=200, background_step=1,
max_peak_fraction=.55, max_context_elongation=2, max_component_aspect=20,
min_aperture_snr=0 and min_score=0. Defaults differ, so use the selected mapping.
The optional faster coarse-map experiment is not enabled. T03 remains available
as `astrotrace.detection.baseline.OpenCVBaselineDetector` with its original code.

## Real sample package and views

Root: `artifacts/reports/cv_t05_member3/`. Five dataset-relative sequence references
are included; original PNGs remain under `data/raw/SpotGEOv2/<split>/<id>/1.png`
through5.png. No archive download or raw-image copy into source/Git occurred.

| Sample | Actual candidate counts, internal frames0..4 | Purpose |
|---|---|---|
| train/84 | 7,7,6,8,6 | multiple candidates; faint/overlap misses |
| train/438 | 6,8,5,3,5 | star-streak interference |
| test/10 | 2,2,1,1,3 | small candidate set; final-frame labeled object missed |
| test/57 | 7,4,7,4,14 | multiple candidates; remaining false-positive example |
| test/1107 | 0,0,0,0,0 | real all-empty detection output, also no annotated objects |

Each split_ID directory contains actual detections.json, raw_frames.png (original
pixels with display-only contrast stretch), candidates.png (image-only green
proposals), comparison.png (separate 5px scoring: green TP, orange FP, magenta
missed labels) and evaluation.json. Labels were first opened after all package
inference finished. sample_evaluation.json is illustrative-case evidence, not
a representative accuracy benchmark. samples.json contains image SHA-256,
dimensions/dtype/order, dataset references and verification outcomes.

All25 sample frames were verified using actual shared schema parsing, repeat
inference, read-only image hashes, no-filesystem-access guards during inference,
direct/helper coordinate comparison and exact equality to historical CV-T04
detections. Original T03 and CV-T04 frozen source hashes are checked on each run.

PowerShell viewing commands for the existing generated package:

```powershell
Invoke-Item .\artifacts\reports\cv_t05_member3\train_84\raw_frames.png
Invoke-Item .\artifacts\reports\cv_t05_member3\train_84\candidates.png
Invoke-Item .\artifacts\reports\cv_t05_member3\test_57\comparison.png
Invoke-Item .\artifacts\reports\cv_t05_member3\test_1107\candidates.png
Get-Content .\artifacts\reports\cv_t05_member3\test_1107\detections.json
Get-Content .\artifacts\reports\cv_t05_member3\integration.json
```

## Reproduction, dependencies and ownership

Use current Python3.12 .venv. Verified runtime versions are recorded in
environment.json. Required detector/loader/shared-schema libraries: NumPy2.5.3,
OpenCV headless4.14.0.94 (cv2 4.14.0), Pillow12.3.0, Pydantic2.14.0; separate
evaluation needs SciPy1.18.1. Tests need pytest9.1.1 and the existing backend dev
environment; the read-only backend probe uses existing FastAPI/httpx. No new
dependencies or root locks/config were changed. Fresh installs should follow
integration-owned [SETUP.md](../../../docs/SETUP.md), not an invented worker lock.
Source package path `src` remains explicitly on PYTHONPATH or bootstrapped by CLI;
these worker modules are not selected by backend packaging/pipeline yet.

Every generated output directory must be new; previous work is preserved. From
E:\Fusion, these reproduce the same samples and fixed final membership:

```powershell
.\.venv\Scripts\python.exe scripts/spotgeo_handoff.py package --source data/raw/SpotGEOv2 --output artifacts/reports/new_member3
.\.venv\Scripts\python.exe scripts/spotgeo_handoff.py verify --source data/raw/SpotGEOv2 --package artifacts/reports/new_member3
.\.venv\Scripts\python.exe scripts/spotgeo_handoff.py inspect-integration --output artifacts/reports/new_integration_probe
.\.venv\Scripts\python.exe scripts/spotgeo_handoff.py verify-tracking-ref --package artifacts/reports/new_member3 --ref origin/feature/tracking-trajectory --output artifacts/reports/new_tracking_snapshot
.\.venv\Scripts\python.exe scripts/spotgeo_handoff.py final-evaluate --source data/raw/SpotGEOv2 --count 128 --seed 20261009 --output artifacts/reports/new_final_evaluation
.\.venv\Scripts\python.exe -m pytest -q -c backend/pyproject.toml
```

The CLI fails with exit2 on missing data/invalid inputs and never downloads.
Package generation includes separate labels for comparison after inference;
verify uses images/config/results only. final-evaluate freezes IDs/config/code
hashes before inspecting selected pixels or labels, checks source PNG hashes and
exact-byte overlap with known-used frames, processes without filesystem access
inside inference, then joins labels for scoring. It never tunes settings.

`scripts/spotgeo_handoff.py` is a local evidence harness: package creates actual
JSON/panels/manifests, verify regenerates and validates saved output,
inspect-integration records actual module/backend checks, final-evaluate runs
fixed-config supplemental scoring. validate_payload deserializes existing schemas
and checks native bounds; verified_inference wraps existing calls with IO guards.
These helpers introduce no public/detector/tracker interface or pipeline logic.

The128 final test sequences are disjoint from recorded tuning/scoring/presentation
examples. They were previously part of the exhaustive T03 image/schema/hash audit.
External/human exposure and capture-session independence cannot be certified.
**Independent blind validation is not available from this provenance.** The new
supplemental measurements must not be described as a fresh independently blind
test, and the previous CV-T04 checkpoint remains regression evidence. See the
[CV-T05 handoff](../../../docs/handoffs/CV-T05.md) for actual results/tests.

Existing dependency license metadata: OpenCV Apache2, NumPy BSD plus bundled
licenses, SciPy BSD/bundled notices, Pillow MIT-CMU, Pydantic MIT. Dataset attribution:
Chen, Liu, Chin, Rutten, Derksen, Maertens, von Looz, Lecuyer and Izzo; ESA spotGEO
v2, DOI10.5281/zenodo.4432143; CC BY4.0 in previously verified publisher metadata.
Prefer dataset-relative references; generated panels stay local/gitignored.
Original archive identity remains unverified. No learned weights are used.

## Integration blockers and next action

Read-only checks show health200/bootstrap_only with detection/tracking/analysis
disabled, analyze/demo404, and pipeline.analyze raising its actual T07
NotImplementedError. This verifies current absence, not successful integration.
The architecture's `associate(detections_by_frame, frame_metadata, config)` is
planned only. The actual fetched source at commit
`8edb6ea778571b08db5cf7217a199dfe8fab9a2a` instead implements
`Tracker.process_sequence(detections: Sequence[Detection], frame_indices=None,
frame_timestamps=None) -> list[Track]`. Flatten the existing by_frame lists and
pass `frame_indices=range(5)` explicitly, including empty/trailing frames.
`frame_timestamps=None` preserves unknown acquisition timing. Shared Detection
objects were consumed unchanged, including IDs/raw coordinates, by this actual
implementation and `attach_trajectories(..., coordinate_frame="raw",
time_basis="frame", frame_dimensions=(640,480))` in a read-only snapshot.
No tracker source was changed or branch merged. The loader reuses the existing
CV-T06 helper and requires that separate worker's example module in this checkout.
See `artifacts/reports/cv_t05_tracking_snapshot/compatibility.json` for real results.

The snapshot's `extract_detection_coords` copies raw to reference when the
detector's reference coordinates are null. That fallback runs and validates
schemas, but does not estimate ESA alignment; reference-frame physical validity
is therefore unverified. Minimal correction is registration transforms plus an
explicit registration status/failure policy agreed with those owners, not a
detector schema change. The old branch handoff examples contain stale imports
and method names; use actual `app.schemas.result.Detection`, PipelineConfig and
Tracker.process_sequence, not app.schemas.sequence.Detection/TrackerConfig/update.

Member3 should integrate/confirm the real association interface using existing
Detection lists, empty frames, explicit unmatched cases and frame-unit timing.
Coordinate with registration owner for raw/reference transforms. Integration
owner must choose the detector explicitly with the measured config and wire
packaging/image storage/API/health/pipeline through reviewed changes. No backend,
tracking, frontend or schema files were modified here.

Known failures: faint/overlapping labeled targets remain missed; compact streak
fragments/noise can survive (test/57 frame4 has11 FP). Test/10 frame4's labeled
position is missed despite3 returned FP. These examples are actual scored
results, not fabricated observations. Local rings and borders can bias features;
some formerly matched faint targets were lost in CV-T04, and runtime increased.
No trajectories, identities, physical speed, debris certification or YOLO model
are implemented by this handoff.
