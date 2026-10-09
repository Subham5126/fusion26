# Member 2 post-Round 2 — T13 / T14 / T17 / T18 handoff

Owner: Member 2 / Data-CV. Implementation task selected: T18; T13/T14/T17 audited and verified without reimplementation.
Base: `61e381065642a592eef5ace97cb32cb3eefefb33` (fetched origin/development).
Working directory: `E:\Fusion-member2-post-round2`, detached HEAD, local review only.
Publication branch remains **Subham only**, at `922fb937a109ec3231d7ec462bb88f3fdbdd62b4`.
No commit, push, merge, rebase, reset, cleanup, new branch, training, weight download or external scientific dataset download.

## Status and scope

| Task | Actual completion status |
|---|---|
| T13 | Existing translation registration reused and tested; real diagnostic measurements reproduced; broader scientific calibration remains unvalidated |
| T14 | Existing spotGEO adapter/parser/evaluator reused; all 32,000 real frames decoded/hashed and all 32,000 annotation records validated; image-only inference and separate raw point scoring rerun |
| T17 | Existing CV-T15 five-epoch run/checkpoint/evaluation reviewed; fresh bounded CPU inference and schema validation passed; experimental only, no replacement or production integration |
| T18 | Missing local primary-FITS inspector/cutout helper added and tested; all 2,000 local headers inspected and three native cutouts decoded; rights, WCS and API adoption deferred |

BACKLOG **T14** is the spotGEO adapter; **CV-T14** is the later robustness work.
BACKLOG T17 covers **CV-T15** YOLO work, distinct from BACKLOG T15 tracking ablation.
The original requirement matrix is `MEMBER2-POST-ROUND2-AUDIT.md`; it records
implemented, insufficiently validated, missing and integration-blocked requirements.

Exact six source/document files are in `MEMBER2-POST-ROUND2-files.txt`. All six
are new in this isolated worktree; no existing source was edited. In particular,
T07 pipeline, T09 routes, shared schemas, Member3 tracker/fitter, Member4 UI,
root config/dependencies/locks and STATUS/BACKLOG remain byte-identical to HEAD.
No existing T13/T14 defect requiring a source change was demonstrated.

Final preservation: all813 pre-existing visible files across the original,
previous integration and latest-dev worktrees, their heads/indexes and best.pt
SHA-256 remained identical. During the final audit two unrelated frontend files
appeared in E:\Fusion: frontend/src/components/TrackingWorkbench.tsx and
frontend/src/visualization/overlay.ts. These concurrent additions were left
untouched and excluded from this task's six-file inventory. The initial exact
path-set check caught the additions; subsequent verification kept the original
baseline and explicitly checked every pre-existing path rather than hiding them.

The fresh `.venv` uses Python3.12.14, existing backend requirements.lock.txt and
the already declared optional astronomy dependency Astropy8.0.1, BSD-3-Clause.
Only the new environment was installed; no other environment was changed.
`pip check` passed. For local source imports set PYTHONPATH to src and backend;
committed backend packaging still excludes astrotrace (Member1 responsibility).

## Member 1 callable boundary

```python
from astrotrace.datasets import SpotGeoDataset, parse_annotations  # parser is evaluation-only
from orbittrace.detection import detect_sequence
from astrotrace.preprocessing.suitability import validate_sequence_suitability
from astrotrace.preprocessing.registration import (
    register_sequence, add_reference_coordinates, warp_to_reference,
)
from astrotrace.datasets.fits import inspect_fits, load_fits_cutout

sequence = SpotGeoDataset(r'E:\Fusion\data\raw\SpotGEOv2', split='train').load_sequence(84)
pixels = [frame.pixels for frame in sequence.frames]
assessment = validate_sequence_suitability(pixels)
if assessment['status'] != 'supported':
    raise ValueError(assessment['explanations'])
registration = register_sequence(pixels)
raw = detect_sequence(pixels, sequence_id='train-84', profile='spotgeo',
                      timestamps_s=[frame.timestamp_s for frame in sequence.frames])
if registration.status == 'failed':
    raise ValueError('Registration failed; do not submit partially registered observations')
observations = add_reference_coordinates(raw, registration)
# Member3 consumes the paired reference coordinates; pass all frame indexes.
# Tracker().process_sequence(observations, frame_indices=range(5))
```

Existing exact signatures:

- `SpotGeoDataset(source, *, split='train', prefix=None, expected_size=(640,480), max_pixels=4000000, max_image_bytes=16777216, archive_limits=...)`; `.load_sequence(sequence_id) -> Sequence`.
- `parse_annotations(payload, *, width_px=640, height_px=480, max_bytes=33554432, require_complete=True) -> AnnotationSet`; never import it into inference.
- `detect_sequence(frames, *, sequence_id, profile='spotgeo', timestamps_s=None, config=None, method='optimized') -> list[Detection]`.
- `register_sequence(frames, config=None) -> SequenceRegistration`; config is RegistrationConfig or declared numeric mapping.
- `add_reference_coordinates(detections, registration) -> list[Detection]`.
- `FrameRegistration.transform_points(points, *, inverse=False) -> ndarray`; `warp_to_reference(pixels, frame) -> (float32 preview, bool validity_mask)`.
- New: `inspect_fits(path, *, max_header_bytes=184320) -> dict`.
- New: `load_fits_cutout(path, *, region=None, max_pixels=4000000, max_header_bytes=184320) -> FitsCutout` with read-only pixels, exclusive native region and `origin_xy`.
- Existing optional experiment: `experiments.yolo.adapter.to_detections(xyxy, confidence, classes, *, width, height, frame_index, sequence_id, model_id='yolo26n-streak-experimental', max_candidates=200) -> (list[Detection], warnings)`; original CV-T15 source remains uncommitted in E:\Fusion, not added to this change set.

Grayscale CV accepts native uint8/uint16 and finite float32/64 normalized to[0,1],
equal native dimensions <=4M pixels. Registration needs dimensions >=32px and
1..30 frames; spotGEO/suitability here use exactly five. Real frame timestamps
remain null. FITS signed/scaled types need a separately reviewed normalization
policy before detector consumption; no automatic stretching occurs in the loader.

Coordinates: integer pixel centers, NumPy[y,x], x right/y down. Frame0 is the
reference anchor. Raw-to-reference translation subtracts measured background
shift; inverse restores it. Only paired Detection reference coordinates change;
raw centroid/boxes/IDs remain untouched. Boxes are exclusive upper limits.
FITS cutout coordinates require adding `origin_xy` to recover native array pixels;
no sky orientation, astrometric transformation or physical coordinates are inferred.

Invalid registration input raises ValueError. A valid but rejected frame has
status failed, null usable matrices and explicit reason codes. Failed sequences
are refused by the bridge even for empty detections. Do not let tracker fallback
mix raw/reference frames or silently substitute identity. Only reference anchor
geometry is identity. API error transport and failed-frame policy remain Member1's
responsibility; no shared schema change is requested.

## T13 actual measurements

Fresh runner used the unchanged tracker/fitter snapshot from base61e3810.
Five previously used ESA examples; 25 native PNGs. Non-reference transforms:
**17/20 accepted**, **3/20 rejected**; complete valid sequences3/5.
Reference identities are excluded from this estimated-transform success count.

| Real sequence | Accepted /4 | Reserved-validation inlier RMSE for indexes1..4, px |
|---|---:|---|
| train/84 | 4 | .238, .315, .310, .382 |
| train/438 | 2 | .525, .691, .576 rejected, .788 rejected |
| test/10 | 4 | .533, .720, .506, .595 |
| test/57 | 3 | .535, .394, .852 rejected, .445 |
| test/1107 | 4 | .291, .481, .343, .514 |

Accepted range .238.. .720px. These are conditional feature-matching residuals,
not ground-truth camera/astrometric error. train438 indexes3/4 fail consensus/
validation support; test57 index3 exceeds the .8px validation gate. No gate changed.
Synthetic known-translation maximum errors: .01330074px compact, .02760681px
streak, .03093631px isolated. Known target motion remains independent of estimated
background compensation; truth enters evaluation only after image inference.

The standalone T13 registration fixtures are not the trusted tiny P0 demo:
the compact-field diagnostic produces many star/nuisance tracks (52 records,
51 confirmed) and the isolated diagnostic3 records/2 confirmed. These are not
certified target identities or detector-accuracy improvements. Proper P0 demo
regression separately produces five detections and one confirmed five-observation
track through unchanged pipeline/API code, preserving supplied timestamps.
ESA84 produces31 track records but0 confirmed tracks; test10 has9/0 and test1107
0/0. Failed sequences are not passed to reference tracking. No real trajectory
accuracy or physical orbit is established.

## T14 dataset and separate scoring

Full current decode/hash/parser validation: train1,280 sequences /6,400 images;
test5,120 sequences /25,600 images. All images640x480 uint8, explicit frame1..5
ordering, immutable arrays, timestamp None. All32,000 strict annotation records
validated separately; explicit empty sequences stay valid. Source is the existing
E:\Fusion\data\raw\SpotGEOv2 extraction, documented v2.0.0 / CC BY4.0. Original
archive MD5 and acquisition chain remain unverified; no archive was downloaded.

A guarded inference rerun opened **only25 PNGs**, no JSON/TXT/CSV annotations
or truth, under true real/spotgeo profile. Saved predictions before separate
annotation discovery. Evaluation uses frozen optimized defaults, raw native
coordinates and one-to-one5px matching; these reused examples are diagnostic
regressions, not blind/official ESA evaluation or threshold tuning.

| Sequence | TP / FP / FN | Precision | Recall | Matched localization RMSE px |
|---|---|---:|---:|---:|
| train84 | 15 /19 /10 | .4412 | .6000 | .3201 |
| train438 | 12 /15 /18 | .4444 | .4000 | .2885 |
| test10 | 4 /5 /1 | .4444 | .8000 | .0992 |
| test57 | 14 /22 /6 | .3889 | .7000 | .2983 |
| test1107 | 0 /0 /0 | null | null | null |

Raw point scoring remains possible on a registration-rejected sequence; this
does not permit reference tracking. ESA annotation array order never becomes
persistent identity. Frozen selection/evaluator and CV-T14 robustness tests are
reused; none was rewritten. Full hashes and annotation/source version evidence
are under spotgeo_validation_01 and detection_review_01.

## T17 actual review

Existing YOLO26n one-class streak checkpoint loaded successfully. best.pt hash
`a019175e841b8842cd84cf395b7eda9585df4f9e306c60e42c27d15a3ff97f03` matches
training, held-out evaluation and fresh CPU inference reports. Training has five
CSV epoch rows with finite losses, recorded378.62s /2,145 batches /366 changed
parameter tensors. Those are verified historical artifacts; no training rerun.
Source architecture/weight URLs/class mapping and licenses are documented in
experiments/yolo/PROVENANCE.md. Ultralytics defaults to AGPL-3.0; dataset CC BY-SA4.0.

Historical test333 images /225 boxes /108 assumed negatives: fixed conf.25 and
IoU.50 give188TP/10FP/37FN, P.9495/R.8356; mAP50.8839, mAP50-95.7114.
Reviewed report hashes are saved in yolo_review.json. Test was separated from
training in the recorded experiment, but capture/session identifiers are absent;
missing labels are assumed negatives. This limits held-out independence/completeness.

Fresh CPU-only640px inference on the first eight ordered test-list images:
five valid Detection objects, no label reads, metrics null, elapsed14.42s for
prediction/decode/rendering including lazy predictor setup, excluding imports
and model construction; backend-reported mean180.46ms/image (batch averaged, requested
batch4, concurrent I/O/tests). This is feasibility evidence, not single-image
latency certification or new accuracy evaluation. Original experiment/runtime/
weights were preserved; source was snapshotted into ignored cache, runtime writes
went to the new workspace. Existing21 YOLO boundary/notebook tests passed.

Keep optimized OpenCV as the default. Streak-box IoU and ESA point-localization
metrics are different domains and cannot justify replacement or score fusion.

## T18 actual inspection and implementation

2,000 raw FITS headers passed bounded inspection, all9600x6422 / BITPIX16 /
BSCALE1 / BZERO32768. DATE-OBS exists in all2,000; explicit TIMESYS in none;
sample exposure.5s, estimated system-clock frame start. Preserve the exact strings
and uncertainty; no absolute epoch/cadence/physical coordinates invented.

Three fixed512x512 cutouts (captures1,1001,2000), native region
(4544,2955,5056,3467), decode exactly to uint16 and match Astropy sections.
Source SHA-256 unchanged before/after; full frame is61,651,200 pixels, beyond
schema0.1.0's4M limit. Bounded sections avoid full-image allocation. All31 owned
FITS tests pass, covering scaling, unsigned extremes, origin, caps, metadata,
duplicate/truncated headers, cubes, BLANK/nonfinite pixels and missing dependency.

Existing processed folder has1,980 PNGs, all2325x1555 RGBA (header-only evidence).
The conversion/resize chain is undocumented; these are not native grayscale
scientific inputs or a verified substitute for raw FITS. No automatic reuse.
Rights, labels, WCS and physical calibration are unverified; NASA/Astropy method
references and detailed support limits are in src/astrotrace/datasets/FITS.md.

## Tests and errors actually run

- Final full unchanged-development plus new FITS suite: **421 passed,0 failed,0 skipped**,121.50s; includes contracts, registration, real adapters/detectors, robustness, tracking, trajectory, evaluation, pipeline and API demo.
- New FITS subset: **31 passed,0 failed,0 skipped**,.85s.
- Existing YOLO utilities from ignored exact source snapshot: **21 passed,0 failed,0 skipped**,.94s.
- T13 runner exit0; full spotGEO validation exit0; guarded inference/separate scoring, FITS inspection/three comparisons, CPU inference, schema validation and synthetic actual FastAPI/TestClient demo passed.
- pip check, original-worktree SHA preservation, empty index, whitespace/patch review passed. No new server was launched; previous integration services remain unaffected.

Initial new FITS run19failed/5passed exposed Astropy Header.count raising on absent
optional keywords; added membership guard. An intermediate broad run354passed/
1failed exposed test-fixture HDU construction normalizing BSCALE0. The malformed
card is now written after construction, so the rejection test exercises actual
bad input. Final31 FITS tests and full421 suite passed. Four full-suite warnings:
three existing Starlette/httpx/HTTP422 deprecations and one deliberate invalid
BLANK-card Astropy warning in the negative fixture. No algorithm test weakened.

## Exact PowerShell reproduction and viewing

Existing environment:

```powershell
Set-Location E:\Fusion-member2-post-round2
$env:PYTHONPATH = "$PWD\src;$PWD\backend"
$env:CV_T06_REAL_SOURCE = 'E:\Fusion\data\raw\SpotGEOv2'
$env:CV_T06_TRACKING_SNAPSHOT = "$PWD\artifacts\reports\member2_post_round2\registration_01\tracking_snapshot"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q -rs -c backend/pyproject.toml
$member2Run = 'artifacts/reports/member2_post_round2/repro_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
.\.venv\Scripts\python.exe scripts/spotgeo_register.py --source E:\Fusion\data\raw\SpotGEOv2 --output "$member2Run/registration" --tracking-ref 61e381065642a592eef5ace97cb32cb3eefefb33
.\.venv\Scripts\python.exe scripts/spotgeo_baseline.py validate --source E:\Fusion\data\raw\SpotGEOv2 --output "$member2Run/spotgeo_validation"
.\.venv\Scripts\python.exe -c "from astrotrace.datasets.fits import inspect_fits,load_fits_cutout; p=r'E:\Fusion\data\raw\frigate\raw\Capture_00001 02_55_24Z.fits'; print(inspect_fits(p)); c=load_fits_cutout(p,region=(4544,2955,5056,3467)); print(c.pixels.shape,c.pixels.dtype,c.origin_xy)"
Invoke-Item artifacts/reports/member2_post_round2/registration_01/train_84/aligned.png
Invoke-Item artifacts/reports/member2_post_round2/frigate_01/Capture_00001_display_only.png
Get-Content artifacts/reports/member2_post_round2/frigate_01/summary.json
Get-Content artifacts/reports/member2_post_round2/detection_review_01/evaluation.json
Get-Content artifacts/reports/member2_post_round2/yolo_review.json
```

Executed setup was bundled Python3.12.14 `-m venv .venv`, followed by
`.venv\Scripts\python.exe -m pip install -r backend/requirements.lock.txt 'astropy>=7,<9'`.
Use a new output name for every rerun. The full data validation reads all32,000
local PNGs and can take several minutes. Diagnostic reports/caches are ignored.

Bounded trained-model repeat (no training or download):

```powershell
Set-Location E:\Fusion-member2-post-round2
$env:PYTHONPATH = "$PWD\.cache\yolo_snapshot;$PWD\backend"
$env:CV_T15_CACHE = "$PWD\.cache\yolo_runtime"
$member2CpuOutput = 'artifacts/reports/member2_post_round2/yolo_cpu_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
& 'E:\Fusion\.cache\cv_t15\venv\Scripts\python.exe' -m experiments.yolo.infer --weights E:\Fusion\artifacts\reports\cv_t15\train_gpu\run\weights\best.pt --images .cache/yolo_cpu_images.txt --sequence-id post-round2-cpu --output $member2CpuOutput --imgsz 640 --batch 4 --device cpu --conf 0.25
Invoke-Item "$member2CpuOutput/frame_0000.jpg"
Get-Content "$member2CpuOutput/predictions.json"
```

These experiment snapshots and trained assets are local-only; another machine
needs separately reviewed CV-T15 source, dependencies and licensed weights.

## Remaining limits and next dependency

Member1 should review the six-file T18/audit patch and optional dependency; retain
the unchanged T13 bridge and explicit failure policy. Committed development still
contains a missing-T13 telescope pipeline placeholder and excludes astrotrace
from backend packaging. The separate working integration in E:\Fusion-latest-dev
is preserved and unpublished; no conflicting integration was applied here.

Member3 owns ESA gating/motion-model validation: ESA84 still has no confirmed
tracks; registration changes apparent background-relative displacement. No gate,
tracking logic or false-positive policy was edited. Need independently labeled
real hard negatives, capture/session metadata and held-out profile validation.

Before FITS API adoption, verify Frigate provenance/rights/timing, select an
explicit tiling/normalization policy and carry native crop offsets. No blind real
registration accuracy, identity, orbit, altitude, collision risk or physical speed
is claimed. Next recommended task: Member1/Member3 coordinate the registered ESA
association failure and FITS crop transport using development data and actual
metadata, rather than retraining or relaxing validation gates.

## Recorded data and configuration hashes

Full ESA image-manifest SHA-256: `90f2521eb33ba269e88184f70ad614333204e421c9c8dcec9925ecdffb6bf9d8`.

train: `train_anno.json` SHA-256 `2727e7c21f1fef229b024dcb00952d0781057661c4ccb64937dce50f08e1fdfe`; 6400 records.

test: `test_anno.json` SHA-256 `8c3e141fba0b5d3ed220563b458a17b17d73ec8cc762aa46abe40d1016f557f4`; 25600 records.

Registration config SHA-256: `ff85d9631ec7cb3275e756d3d30bf7ec59baa29029c4d8bc89eebcafa73e0fcd`. Per-image and new source hashes are in the referenced JSON manifests.
