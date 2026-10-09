# Handoff: CV-T15 — experimental YOLO streak training and benchmarking

Owner: Member 2 / Computer Vision and Dataset Engineer, explicitly assigned.
Backlog area: T17 optional trained streak adapter; CV-T15 is the user's experiment
milestone, not BACKLOG T15 tracking ablation.
Base commit: `c802622800ed14739bd841ee840ec16cf905e4cd`, branch **Subham**.
Date: 9 October 2026, Asia/Calcutta.
State: **ready_for_review** — audits, CPU/GPU smoke training, five-epoch GPU
training, separated test evaluation, image-only inference, visual inspection and
shared-schema validation completed. Production integration and Colab execution
are **not tested** and require separate work.

## Scope and parallel ownership

Implementation is confined to `experiments/yolo/`, `tests/yolo/` and this handoff.
Generated datasets, wheels, environment, model weights, log/config caches and
large reports use ignored `.cache/cv_t15/` and `artifacts/reports/cv_t15/`.
Existing backend, schemas, classical detectors, preprocessing, tracking,
frontend, AGENTS, root config/dependencies/locks and CV-T14 files were not edited.
The other agent's work was left untouched. No branch switch, worktree creation,
commit, push, merge, rebase, deployment or large scientific dataset download.

An upstream configuration fallback did create untracked
`E:\Fusion\Ultralytics\settings.json` during the initial model-load probe.
Future runs were corrected to use `.cache/cv_t15/ultralytics/Ultralytics` before
import. Automatic approval review rejected moving/removing the initial generated
root file, returning only “blocked by policy”; it remains for manual review and
must not be included in the integration commit. No automatic retry circumvented
that rejection.

## Hardware and environment: tested

CPU Intel Core i5-12450HX, 8 cores / 12 logical processors. Installed RAM from WMI:
24,866,680 KiB (23.71 GiB); free RAM varied around 9–12 GiB. Initial free space:
E: 507,404,472,320 bytes (472.56 GiB), C: 269,756,030,976 bytes (251.23 GiB).
NVIDIA RTX 3050 6GB Laptop GPU, 6,144 MiB VRAM, driver 581.86. `nvidia-smi`
reported driver CUDA capability 13.0; this was not claimed as an installed toolkit.
Neither Torch nor Ultralytics was installed in the shared Python 3.12.14 `.venv`,
or in default Anaconda Python 3.14.6.

New isolated environment: `E:\Fusion\.cache\cv_t15\venv` (Python 3.12.14).
Final selected runtime: Torch **2.7.1+cu126**, torchvision **0.22.1+cu126**,
Ultralytics **8.4.174**, NumPy **2.2.6**, OpenCV **4.12.0.88**, Pillow **12.3.0**,
SciPy **1.15.3**, PyYAML **6.0.3**, Pydantic **2.14.0**.
`torch.cuda.is_available()` returned **true**; a 64×64 CUDA matrix multiply returned
sum 262144.0. Actual GPU smoke training completed. `pip check` passed.
Run dependency checks with PYTHONPATH unset: adding `backend` exposes its existing
`orbittrace.egg-info` to pip metadata discovery and reports missing FastAPI,
opencv-python-headless, python-multipart and uvicorn in this experiment-only
environment. That contextual check returned warnings; the isolated package check
with PYTHONPATH empty returned “No broken requirements found.” HTTP dependencies
were not installed just to silence this unrelated backend metadata warning.
Package snapshot is `.cache/cv_t15/environment.json`; portable experiment-owned
non-Torch pins are `experiments/yolo/requirements-runtime-lock.txt`.

Disk/driver/package availability was checked before adopting large dependencies.
Initial pip dry-run tried a 3.27GB CUDA12.8 wheel but stalled before receiving its
payload and was interrupted. A supported CUDA12.6 pair was selected from the
[official PyTorch previous-version instructions](https://pytorch.org/get-started/previous-versions/).
The 2,716,918,001-byte Torch wheel was retrieved in bounded ranges; its first
420-second attempt timed out, its missing ranges were resumed, and the whole file
passed publisher SHA-256
`7d897b5ff67e778de4a2a05d4528377003105e29854fd73ecbe965287533f08b` before installation.
The model checkpoint was a separate small download, not part of a new dataset.

The runtime temporarily used CPU Torch 2.14.1 for the CPU smoke while the CUDA
wheel completed. Those CPU outputs record that version. It was then replaced in
the isolated environment only. A briefly overlapping SciPy installation was
interrupted; final dependencies were installed sequentially, pins/versions and
`pip check` verified. An initial metadata probe used `PIL` as the distribution
name and failed; corrected probes use `Pillow`.

## Dataset: inspected read-only

Source: `E:\Fusion\data\raw\StreaksYoloDataset`, with
`train|validation|test/{images,labels}`. Supplied data.yaml has one class,
`0: streak`, but points at nonexistent relative `./data/yolo-streaks-dataset/`
paths. The source YAML was preserved; experiment preparation emits valid YAML.

| Source split | Images | Label files | Valid positive boxes | Missing labels | Invalid boxes |
|---|---:|---:|---:|---:|---:|
| train | 1,722 | 1,193 | 1,189 | 529 | 4 |
| validation | 333 | 224 | 222 | 109 | 2 |
| test | 333 | 225 | 225 | 108 | 0 |

All **2,388** JPEGs decoded fully: 640×640, RGB. No corrupted images, orphan label
files or exact byte/pixel duplicate groups were found. Existing positive labels
contain one normalized YOLO xywh box. Six labels have zero width or height:
train IDs 1028,1141,2092,2108; validation IDs 35,557. They were excluded, not repaired.

Five cross-split pHash≤6 pairs were screened, with thumbnail correlation reported
for inspection; these are similarity candidates, not proven duplicate captures:

- train/1153 ↔ test/813
- train/1876 ↔ validation/56
- train/2141 ↔ test/813
- train/2224 ↔ validation/968
- validation/56 ↔ test/813

Their lower-priority members were conservatively excluded. No test image was
moved into training or validation. Numeric filenames have no reliable
capture-session/sequence/tile identity metadata; residual leakage is explicitly
unknown. Appearance screening does not certify session-independent evaluation.

| Prepared split | Images | Positive boxes | Assumed negatives |
|---|---:|---:|---:|
| train | 1,714 | 1,186 | 528 |
| validation | 330 | 221 | 109 |
| test | 333 | 225 | 108 |

Total exclusions: **11**. A seeded train-only smoke subset has 48 positives and
16 assumed negatives. Source images stay in place: ignored training-view images
are hard links (copy fallback across filesystems), labels are independent copies,
and Ultralytics caches are confined to the view. Every source image, label and
source YAML was rehashed unchanged; no `.cache` file appeared in the original
dataset. Evidence: `artifacts/reports/cv_t15/source_preservation.json`.

Missing label files are assumed negatives following the
[YOLO format convention](https://docs.ultralytics.com/datasets/detect/), not
individually certified negatives. A 12-image positive/negative contact panel was
inspected. Its broad/noisy/near-border boxes are annotations of visible streaks,
not evidence of identity, completeness or physical calibration.

Publisher attribution: Olivier Parisot / LIST, StreaksYoloDataset v1.0.0,
[Zenodo 14047944](https://zenodo.org/records/14047944). The separately retrieved
license.txt identifies CC BY-SA 4.0 and matches the publisher MD5. Details, hashes,
class policy and checkpoint/source links are in
[PROVENANCE.md](../../experiments/yolo/PROVENANCE.md).
The existing ESA dataset was not converted, mixed into training or modified.

## Model, training and inference semantics

Selected architecture: **Ultralytics YOLO26n Detect**, nano scale, RGB input,
end-to-end detection head with P3/P4/P5 outputs. Support was verified in official
documentation and actual installed code; no compatibility fallback was needed.
Pretrained: official `yolo26n.pt`, assets release v8.4.0, **5,544,453 bytes**,
SHA-256 `9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef`.
Actual loaded model: 2,572,280 parameters and 80 COCO classes. Actual one-class
training model: **2,504,190 parameters**, **606/708** checkpoint items transferred.
The trained class is generic `streak`, not debris.
Ultralytics code/pretrained/trained models have AGPL-3.0 by default, with an
Enterprise alternative; production licensing/redistribution remains an
integration decision. PyTorch metadata identifies BSD-3-Clause.

Smoke CPU: 1 epoch, 64 train/330 validation images, input320/batch4, 30.79s total;
16 finite batches, 366 parameter tensors changed, best/last saved and validated.
Smoke GPU: same membership/config, 23.07s total; 16 finite batches, 366 tensors
changed, best/last saved and validated. GPU memory logged about .355GB at320.
Smoke metrics were very poor; they are execution checks, not production quality.
Actual smoke image-only inference processed 64 images, with zero proposals at
fixed confidence .25. That is not a detection-accuracy success claim.

Main experiment plan was frozen before learning in
`artifacts/reports/cv_t15/experiment_plan.json`: **5 requested epochs**, input640,
batch4, GPU0, seed26, AdamW lr.001, no mosaic/mixup, modest geometry/brightness
augmentation, workers0, two Torch CPU threads, no RAM image cache/AMP, 15-minute
soft wall-time budget at epoch boundaries. It starts from pretrained weights
instead of resuming/selecting the smoke checkpoint. Validation chooses best.pt;
test is used for the final frozen run only, not tuning.

## Main experiment and evaluation

**Training completed** all five requested epochs in **378.62s** (6m19s). All
**2,145** training batches had finite losses (summed loss min .69854, max 51.79408).
**366** trainable parameter tensors changed. No CUDA OOM or training exception
occurred; training logged about 1.58GB GPU allocation. Both checkpoints were saved
and the best checkpoint was validated. Best-validation P/R/mAP50/mAP50-95 were
97.17% / 77.70% / 84.65% / 66.11% respectively. This short run is experimental,
not evidence of convergence or deployment readiness.

Checkpoint directory: `artifacts/reports/cv_t15/train_gpu/run/weights/`.

- best.pt SHA-256: `a019175e841b8842cd84cf395b7eda9585df4f9e306c60e42c27d15a3ff97f03`
- last.pt SHA-256: `f195485da1fa5fc59e0097c3ca4b8477678abc185d512ade726e72af4b1be25c`
- Prepared dataset YAML SHA-256: `4a1c61449eba1ba32c6cf9d631c0573bace2f3c6ed3d110d11871292bfd3fe4f`

**Test evaluation completed**, 333 images / 225 labeled boxes / 108 assumed
negatives, with unchanged confidence .25 and IoU matching .50. Test was not used
for hyperparameter or threshold tuning. Metrics use the supplied annotation
policy; incomplete negatives or related captures would affect their meaning.

| Metric | Actual held-out result | Meaning |
|---|---:|---|
| Ultralytics precision | 94.54% | At validator's F1 operating point |
| Ultralytics recall | 84.61% | At validator's F1 operating point |
| mAP50 | 88.39% | AP confidence floor .001 |
| mAP50-95 | 71.14% | IoU .50:.95 |
| Fixed precision | 94.95% | Confidence .25, IoU .50 |
| Fixed recall | 83.56% | Confidence .25, IoU .50 |
| Fixed F1 | 88.89% | From 188 TP, 10 FP, 37 FN |
| Negative-image FP | 1 / 108 images | One assumed-negative image with one proposal |
| FP per assumed-negative image | .00926 | Fixed confidence .25 |
| Model inference, mean / p95 | 11.33 / 17.01ms | Single-image GPU samples, warm-up excluded |

The separate batch-4 validator reported approximately 5.6ms model inference per
image. The 11.33ms measurement is single-image prediction, excludes IO/matching/
plots, and is not end-to-end latency. The prediction/matching loop took 6.41s.
Fixed matching maximizes gated one-to-one match cardinality then summed IoU with
explicit unmatched choices. All test metrics are box metrics, not point tracking
or confirmed debris-identification metrics.

Image-only inference separately processed **333 ordered images**, emitted **198**
shared Detection objects and **141 empty frames**, and saved 333 annotated JPEGs.
Revalidation using the actual unchanged `app.schemas.result.Detection` passed:
198 sequence-wide unique IDs, original finite coordinates, positive exclusive
upper boxes within native 640x640 dimensions, frame order/indices, kind `streak`,
bounded uncalibrated confidence, and no annotation reads or invented metrics.
Production backend/tracking execution was not run or claimed in this experiment.

Representative images were inspected, with red annotation and green prediction
boxes. Misses include faint/short streaks (602,610,628,639); 621 has a localized
prediction whose box does not match the tall annotation at IoU .50. 670 and 69
have duplicate proposals around a streak. The sole assumed-negative FP is 884,
visually a bright star/cluster rather than an obvious long streak. This qualitative
inspection does not relabel the dataset. Successful box examples include
6,60,601,603. No post-test tuning was performed.

Local evidence/output:

- `artifacts/reports/cv_t15/experiment_plan.json`: frozen run/threshold plan.
- `artifacts/reports/cv_t15/train_gpu/training_evidence.json`: execution, versions, updates, hashes.
- `artifacts/reports/cv_t15/train_gpu/run/results.csv`: all five epochs.
- `artifacts/reports/cv_t15/test_gpu/evaluation.json`: metrics, all predictions and 43 failure-image records.
- `artifacts/reports/cv_t15/test_gpu/failure_examples.png`: reproducible evaluator panel.
- `artifacts/reports/cv_t15/test_gpu/representative_examples.png` and `.json`: post-evaluation qualitative selection, including negative FP and matches.
- `artifacts/reports/cv_t15/predictions_gpu/predictions.json` and `frame_0000.jpg` … `frame_0332.jpg`: image-only native-coordinate predictions.
- `artifacts/reports/cv_t15/contract_validation.json`: real shared-schema validation and sample Detection.
- `artifacts/reports/cv_t15/source_preservation.json`: original files rehashed unchanged after main training.
- `artifacts/reports/cv_t15/existing_file_observation.json`: baseline observation; concurrent CV-T14 changes were left alone.

Actual training/evaluation/inference commands (already executed successfully):

```powershell
Set-Location E:\Fusion
$yoloPython = 'E:\Fusion\.cache\cv_t15\venv\Scripts\python.exe'
$env:PYTHONPATH = 'E:\Fusion;E:\Fusion\backend'
& $yoloPython -m experiments.yolo.train --data .cache/cv_t15/dataset/dataset.yaml --weights .cache/cv_t15/weights/yolo26n.pt --output artifacts/reports/cv_t15/train_gpu --epochs 5 --imgsz 640 --batch 4 --device 0 --seed 26 --time-hours 0.25
& $yoloPython -m experiments.yolo.evaluate --data .cache/cv_t15/dataset/dataset.yaml --weights artifacts/reports/cv_t15/train_gpu/run/weights/best.pt --output artifacts/reports/cv_t15/test_gpu --split test --imgsz 640 --batch 4 --device 0 --conf 0.25
& $yoloPython -m experiments.yolo.infer --weights artifacts/reports/cv_t15/train_gpu/run/weights/best.pt --images .cache/cv_t15/dataset/test.txt --sequence-id cvt15-heldout --output artifacts/reports/cv_t15/predictions_gpu --imgsz 640 --batch 4 --device 0 --conf 0.25
& $yoloPython -m pytest -q -c backend/pyproject.toml tests/yolo
$savedYoloPath = $env:PYTHONPATH
$env:PYTHONPATH = ''
& $yoloPython -m pip check
$env:PYTHONPATH = $savedYoloPath
Invoke-Item artifacts/reports/cv_t15/test_gpu/representative_examples.png
Invoke-Item artifacts/reports/cv_t15/predictions_gpu/frame_0000.jpg
Get-Content artifacts/reports/cv_t15/contract_validation.json
```

The three existing output directories are intentionally protected from overwrite:
use fresh names such as `train_repro`, `test_repro`, `predict_repro` when repeating
commands, and point evaluation/inference at the corresponding selected checkpoint.
The README default is a configurable 10 epochs; the actual frozen run above used
five. Ignored artifacts/environment/weights are not included in Git and need local
reproduction or an approved licensed artifact-transfer path for another member.

## Contract proposal and integration recommendations

Experimental adapter: `experiments.yolo.adapter.to_detections(...)`, returning
`list[app.schemas.result.Detection]` plus explicit cap warnings. Backend and
schema 0.1.0 were inspected read-only; neither is modified or imported from this
experiment by production code. The adapter takes `Results.boxes.xyxy` already
mapped to original-image coordinates, confidence and class IDs; finite positive
exclusive-upper boxes must lie inside the actual width/height. No rounding,
automatic clipping, resizing transform or reference-frame registration is invented.
Raw x/y is the bounding-box midpoint, not an intensity centroid/endpoints.
IDs namespace sequence/model SHA token, frame index and proposal rank. Quality
is the [0,1] uncalibrated model confidence, also exported in explicit evidence.
Kind is `streak`; no confirmed debris label is introduced.

Exact import and a minimal original-pixel example (set PYTHONPATH as above):

```python
from experiments.yolo.adapter import to_detections
from app.schemas.result import Detection

detections, warnings = to_detections(
    [[10, 20, 100, 120]], [.9], [0], width=640, height=640,
    frame_index=0, sequence_id="demo", model_id="yolo26n-streak-experimental")
assert isinstance(detections[0], Detection)
assert detections[0].bbox_raw_px == (10., 20., 100., 120.)
```

Real frame-0 sample: model `yolo26n-streak-a019175e841b`, ID
`sy9561aeba172141da-f0-c0`, midpoint (278.15494,408.08399), box
(73.81631,238.96608,482.49356,577.20190), confidence .90629566. Exact unrounded
JSON is in `contract_validation.json`. These are image pixels with top-left origin.

Inference rejects untrained 80-class COCO checkpoints to prevent class0 (`person`)
being silently interpreted as `streak`. Image-only inference never reads labels;
metrics remain null. Evaluation reads labels separately. Native model confidence
and CV-T04 heuristic quality are not calibrated on the same scale.

Member 1 may later offer classical OpenCV or experimental YOLO as separate
explicit acquisition/task choices. A hybrid should initially show both outputs
separately, retaining model names/confidence semantics/provenance. Learned score
fusion, deduplication and common-frame registration need separate evaluation.
Do not automatically replace CV-T04. ESA compact point-localization numbers
and streak-box IoU metrics are **not directly comparable**.

## Files and reproducible instructions

Created under `experiments/yolo/`: `__init__.py`, `common.py`, `audit.py`,
`prepare.py`, `download.py`, `fetch_weights.py`, `train.py`, `evaluate.py`,
`infer.py`, `visualize.py`, `adapter.py`, `dataset.yaml`, `train.yaml`,
`requirements.txt`, `requirements-runtime-lock.txt`, `colab.ipynb`, `README.md`,
`PROVENANCE.md`.
Created under `tests/yolo/`: `conftest.py`, `test_boundaries.py`, `test_notebook.py`.
Created: this handoff. No existing implementation files modified.
Exception: library-generated root settings file above, left after approval rejection.

Full PowerShell setup/audit/preparation/training/inference commands are in
[experiment README](../../experiments/yolo/README.md). Colab notebook code cells
are AST-validated locally with no fabricated execution outputs; no Colab run or
upload occurred. It is an optional path because local GPU training was verified.

Actual commands run included hardware WMI/nvidia-smi, package/disk checks,
`python -m experiments.yolo.audit`, preparation with `--exclude-invalid`, label
visualization, bounded dependency/checkpoint/license fetches, isolated package
installation, `pip check`, CPU/GPU smoke training, smoke inference and targeted
pytest/compile checks. Main/evaluation/inference commands and outcomes are above.

Latest targeted tests: **21 passed, 0 failed, 0 skipped** in both shared test
runtime and isolated experiment runtime. They exercise malformed labels,
leakage-aware split filtering without movement, explicit invalid-sample exclusion,
native last-pixel geometry, finite score/class checks, sequence IDs, caps/empties,
one-to-one gated box matching and notebook syntax/no fake outputs.
Final isolated test run: 21 passed in 1.03s. Compileall and the documented adapter
example passed. Repository documentation check passed (73 local links across 64
Markdown files); experiment Markdown links were also checked separately. Git
diff whitespace check passed, with pre-existing LF/CRLF notices in two other
members' changed Markdown files. No full application suite or Colab run was claimed.

Known failures/warnings: six malformed source labels were genuine audit findings;
initial CUDA wheel request stalled and bounded first download timed out (resumed,
verified); initial PIL metadata lookup failed (corrected); upstream root config
fallback was corrected for future runs, with initial root-file cleanup rejected;
CPU smoke quality was poor. Main training/evaluation/inference had no failed
execution checks. Missing labels/session identities remain uncertain. Colab and
production tracking/backend integration were not executed; the Colab notebook
has syntax-only validation. Targeted pytest had no skipped tests.
The context-dependent backend package metadata warning is recorded above; it
does not establish HTTP application dependency readiness in the YOLO environment.

Next task: obtain capture/session identifiers and review ambiguous negatives and
streak boxes, then establish a session-separated streak evaluation before a longer
training/threshold experiment. Member 1 should review the experiment source,
licenses and task-profile suitability before separately authorizing optional backend
detector selection, dependency changes and a real tracking integration test. Keep
CV-T04 as the existing default; no shared schema change is requested. An optional
YOLO selector must use original Results boxes and explicit `streak` semantics.

Final Git state: branch `Subham`, HEAD unchanged at the base commit above. All
CV-T15 source files/handoff are untracked for human review; nothing was staged,
committed, pushed, merged or rebased. Other members' concurrent files remain in
the working tree. A snapshot of 95 pre-existing files observed only concurrent
changes to `src/astrotrace/detection/stress_evaluation.py` and
`scripts/spotgeo_robustness.py`; this task did not edit them.
