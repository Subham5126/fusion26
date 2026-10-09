# CV-T15 experimental streak training

This is a separate experiment, not a production replacement for T03/CV-T04.
Inputs are labeled streak boxes. Read [PROVENANCE.md](PROVENANCE.md) before sharing
data/panels/weights. Actual execution evidence and measured results belong in
[CV-T15 handoff](../../docs/handoffs/CV-T15.md).

Measured local run: five epochs completed on RTX 3050 in 378.62s. On 333 held-out
images, mAP50 was 88.39%, mAP50-95 71.14%; fixed confidence .25/IoU .50 gave
188 TP, 10 FP, 37 FN (precision 94.95%, recall 83.56%). One false positive occurred
on 108 assumed-negative images. Session metadata is absent, so residual leakage
is unknown. These streak-box metrics cannot be compared directly with ESA compact
point detections. See the handoff for evidence, failures and exact executed commands.

Use Python 3.12 and an isolated environment. Keep the existing OrbitTrace `.venv`
unchanged. An RTX 3050 6GB is available on the audited machine. The default main
run is 10 epochs, 640-pixel input, batch 4, GPU 0, two Torch CPU threads, no loader
workers, no RAM image cache and no AMP. A 15-minute soft budget is checked at epoch
boundaries without increasing the requested epoch count. Deterministic seeds are
declared; exact repeatability across hardware/library versions is not guaranteed.

Install the CUDA-enabled Torch pair **first**, then the experiment requirements:

```powershell
Set-Location E:\Fusion
.\.venv\Scripts\python.exe -m venv .cache/cv_t15/venv
$yoloPython = 'E:\Fusion\.cache\cv_t15\venv\Scripts\python.exe'
& $yoloPython -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu126
& $yoloPython -m pip install -r experiments/yolo/requirements.txt
& $yoloPython -m pip check
$env:PYTHONPATH = 'E:\Fusion;E:\Fusion\backend'
```

Keep PYTHONPATH unset for `pip check`. Adding the backend path exposes its existing
OrbitTrace package metadata and can report its HTTP dependencies as missing in
this intentionally separate YOLO environment. Restore that import path for
adapter inference/tests; no backend dependency readiness is claimed here.

If the full 2.7GB wheel request stalls, the explicit `download` helper supports
bounded range requests and verifies the publisher's SHA-256. This is a Torch
dependency download, never a scientific dataset downloader:

```powershell
.\.venv\Scripts\python.exe -m experiments.yolo.download --url 'https://download.pytorch.org/whl/cu126/torch-2.7.1%2Bcu126-cp312-cp312-win_amd64.whl' --output .cache/cv_t15/wheels/torch-2.7.1+cu126-cp312-cp312-win_amd64.whl --bytes 2716918001 --sha256 7d897b5ff67e778de4a2a05d4528377003105e29854fd73ecbe965287533f08b --timeout-s 600
& $yoloPython -m pip install .cache/cv_t15/wheels/torch-2.7.1+cu126-cp312-cp312-win_amd64.whl
& $yoloPython -m pip install torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu126
```

To resume an interrupted range download, add `--resume-partial` to the same command.
Final hash verification remains mandatory. Check free disk space before installing
CUDA packages; do not run multiple pip installs against the same environment.

Audit and prepare with fresh directories (these commands refuse to overwrite):

```powershell
& $yoloPython -m experiments.yolo.audit --source data/raw/StreaksYoloDataset --output .cache/cv_t15/audit_new
# Audit writes evidence and returns nonzero for malformed labels. Inspect it first.
Get-Content .cache/cv_t15/audit_new/dataset_audit.json
& $yoloPython -m experiments.yolo.prepare --audit .cache/cv_t15/audit_new/dataset_audit.json --output .cache/cv_t15/dataset_new --exclude-invalid
& $yoloPython -m experiments.yolo.fetch_weights --output .cache/cv_t15/weights_new/yolo26n.pt
```

Preparation conservatively filters audited malformed/similar samples; it never
changes original split assignments. It creates an ignored training view with
read-only-use image hard links (copies on another filesystem) and independent
label copies, keeping original files in their existing locations. Ultralytics'
label caches therefore stay in `.cache`, not the read-only source dataset.
Dataset YAML and frozen membership/hashes are generated in that view. The source
`dataset.yaml` is an explanatory template, not the original invalid publisher YAML.

Train and validate:

```powershell
& $yoloPython -m experiments.yolo.train --data .cache/cv_t15/dataset_new/smoke.yaml --weights .cache/cv_t15/weights_new/yolo26n.pt --output artifacts/reports/cv_t15/smoke_new --epochs 1 --imgsz 320 --batch 4 --device 0
# Inspect smoke_new/training_evidence.json before the main run.
& $yoloPython -m experiments.yolo.train --data .cache/cv_t15/dataset_new/dataset.yaml --weights .cache/cv_t15/weights_new/yolo26n.pt --output artifacts/reports/cv_t15/train_new --epochs 10 --imgsz 640 --batch 4 --device 0 --seed 26 --time-hours 0.25
& $yoloPython -m experiments.yolo.evaluate --data .cache/cv_t15/dataset_new/dataset.yaml --weights artifacts/reports/cv_t15/train_new/run/weights/best.pt --output artifacts/reports/cv_t15/test_new --split test --imgsz 640 --batch 4 --device 0 --conf 0.25
```

`training_evidence.json` records actual finite loss checks, parameter changes,
epochs completed and checkpoint hashes. A failed run writes `state=failed` and
raises; never call its checkpoint trained successfully without checking evidence.
`best.pt` is selected on validation; do not tune on test outputs. The evaluation
reports Ultralytics precision/recall at its F1 operating point and AP with a .001
confidence floor separately from fixed-.25 IoU-.5 TP/FP/FN, assumed-negative FP,
timing and missed/false-positive examples. Timing excludes warm-up; it is a single
local measurement, not a throughput guarantee. Mixed dataset tasks remain separate.

Image-only inference and visualization:

```powershell
& $yoloPython -m experiments.yolo.infer --weights artifacts/reports/cv_t15/train_new/run/weights/best.pt --images .cache/cv_t15/dataset_new/test.txt --sequence-id heldout-preview --output artifacts/reports/cv_t15/predict_new --imgsz 640 --device 0 --conf 0.25
Invoke-Item artifacts/reports/cv_t15/test_new/failure_examples.png
Invoke-Item artifacts/reports/cv_t15/predict_new/frame_0000.jpg
Get-Content artifacts/reports/cv_t15/predict_new/predictions.json
& $yoloPython -m pytest -q -c backend/pyproject.toml tests/yolo
```

The image list defines order explicitly. Inference reads images only; metrics
remain null. A trained one-class `streak` checkpoint is required, preventing COCO
class 0 (`person`) from being silently reinterpreted as a streak. Predictions use
the same uncalibrated confidence in `quality_score` and explicit evidence.

Experimental [adapter.py](adapter.py) consumes original-image
`Results.boxes.xyxy`, confidence and class IDs, rejects invalid/letterboxed-sized
boxes, preserves exclusive bounds and frame indices, namespaces IDs across the
sequence/model, and returns the unchanged shared `app.schemas.result.Detection`.
Its x/y are bounding-box midpoints, not intensity centroids or calibrated endpoints.
Reference coordinates stay null. The optional hybrid path should display both
methods separately; score fusion/calibration and deduplication require new evidence.
No production backend imports this experiment.

Optional [colab.ipynb](colab.ipynb) reuses the same audit/preparation/training/evaluation
scripts. Its Python cells are syntax-tested locally; Colab execution has not been
claimed. Upload reviewed source (including backend schemas) and the already
acquired dataset to your own Drive, select a GPU runtime, edit two paths, inspect
the audit, and run the smoke cell before training. Nothing has been uploaded or
scheduled by CV-T15. Copy selected results/checkpoints back from ephemeral storage.
