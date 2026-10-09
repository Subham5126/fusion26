# Dataset plan and acquisition checklist

## Download decision

Generate synthetic sequences first. Download spotGEO v2 in parallel only if local bandwidth and storage allow. Use a small reproducible subset after extracting the official archive; there is no verified separate tiny official subset in this research. You do not need all four datasets.

| Priority | Dataset or tool | Link | Verified size / format | Purpose |
|---|---|---|---|---|
| P0 | Our seeded synthetic generator | Implement locally | Proposed PNG + separate JSON truth | Full detection/tracking/prediction benchmark |
| P1 | spotGEO v2 | https://zenodo.org/records/4432143 | 4.2 GB archive; grayscale PNG sequences | Real astronomical localization validation |
| P1 support | spotGEO starter kit | https://zenodo.org/records/3874368 | About 495 kB combined files | Official validation/scoring reference |
| P2 | StreaksYoloDataset | https://zenodo.org/records/14047944 | 1.4 GB; 640×640 JPEG + YOLO text | Optional trained streak proposal detector |
| P2 | Frigate | https://doi.org/10.6084/m9.figshare.29545667 | FITS imagery; total archive size not verified here | Later LEO-domain validation |
| Inspect only | Catalog Kaggle reference | https://www.kaggle.com/datasets/sadianawar/debris-detection-dataset | Contents and labels not verified | Adopt only after sample inspection |

Source records: [S1, S5, S6, S9, S16]. No archive was downloaded during this planning task. Sizes are published archive sizes, not guarantees of disk usage after extraction.

## spotGEO: fit and limitations

The record describes 6,400 sequences of five images, 32,000 images total; v2 adds test annotations. Images are 640×480. GEO/near-GEO targets are compact blobs or short streaks; long LEO streaks are outside its challenge target definition. Camera orientation changes between frames. Ground truth consists of per-frame object coordinates, not an assumed cross-frame ID schema. Do not identify objects by annotation-array index. Some scenes have no objects. [S1–S4]

### Acquisition steps

1. Open the official record and use its `SpotGEOv2.zip` download. Inspect rights metadata and archive documentation before redistributing samples.
2. Check available disk capacity for the archive, extracted tree and working copies. Budget conservatively rather than assuming extraction remains 4.2 GB.
3. Verify the downloaded file against the published MD5 `9a44895f17830247208230bc09c43f2d` for accidental corruption; use our own SHA-256 in the manifest for reproducibility. [S1]
4. Extract safely into `data/external/spotgeo_v2/`; never commit the full archive.
5. Inspect actual folder names and annotation fields. Historical documentation uses slightly different annotation filenames; locate the actual file rather than hard-coding a guessed name.
6. Create `data/manifests/spotgeo_subset.json` with sequence IDs, source version and split membership. Proposed first subset: 60 development, 20 validation and 20 held-out sequences. Adjust to availability and time; these counts are our plan.
7. Preserve all five frames of a sequence in the same split. Use fixed seed 26 for selection. Record sequence selection before threshold tuning.
8. Include empty scenes if available. Keep a random manifest-based subset separate from hand-picked presentation examples.
9. Map detections back into raw-image coordinates before scoring. Report any unsupported sequence and registration failure.

### Annotation mapping

The official format names `sequence_id`, `frame`, `num_objects`, `object_coords`. [S3] Normalize identifiers to strings and frame indexes to zero-based values in our internal format; preserve the original value in adapter metadata. Inspect actual numbering first. Point labels support centroid/localization metrics; they do not provide bounding boxes or confirmed debris classes. Tracking metrics requiring identity ground truth are primarily evaluated on synthetic sequences.

The original spotGEO coordinate convention has boundary limits offset by half a pixel. Preserve the published coordinates and document any conversion into our zero-based pixel-center convention. The evaluator must not silently round them. [S3]

## Synthetic data specification

Proposed generation defaults: 640×480, 12 frames, 0–3 targets, unsigned grayscale images with floating-point generation before clipping. Target motion and appearance are generated separately from image rendering. The benchmark must contain more than easy bright targets.

Generate fixed scenes with star points, star streaks where appropriate, moving compact targets, moving streaks, Poisson-like photon noise, read noise, background gradients, hot pixels, isolated cosmic-ray-like flashes, mild blur and optional camera translation/rotation. Maintain two profiles: stationary-star synthetic scenes and ground-static/streaked-star scenes. Do not imply these simplified models reproduce every atmospheric or optical effect.

Cases: easy, faint, high noise, no target, one-frame artifact, persistent hot pixel, one missed frame, two crossing tracks, target near boundary, small camera rotation. Include negative scenes in evaluation.

Save images and metadata in the inference directory. Save true positions, IDs, visibility flags and camera transforms under `data/ground_truth/`, read only by evaluation. Use different scene seeds and star fields for development, validation and test. Proposed allocation: 20/10/20 sequences; more only if generation is cheap.

## StreaksYoloDataset

The publisher describes astronomical images annotated for streak detection, not a guaranteed track-ID benchmark. An archive and separate `license.txt` are provided. Published archive MD5: `ff4f651b55077a23ebda94c9d157e1b0`. [S6] Inspect class mappings, empty-image handling, train/validation separation and capture-session grouping after download. A streak label does not certify debris identity. Prevent tiles or augmented copies of the same source image from landing in different splits.

Use only after the main pipeline works and a short GPU run is feasible. Keep bounding-box evaluation separate from point-label evaluation. Do not assume success transfers to spotGEO's tiny compact sources.

## Frigate and catalog Kaggle reference

Frigate's author repository confirms a FITS-oriented processing workflow. The dataset landing page was blocked during research; exact sizes, label completeness, timing and reuse terms remain unverified. Use the DOI plus https://github.com/DanSRoll/frigate to inspect later. Do not plan a mandatory download or metric around unverified labels. [S9, S16]

The Kaggle page did not expose usable dataset details through our lookup. Inspect actual samples before accepting it; reject a body-image or unrelated debris dataset as primary telescope-sequence evidence.

## Provenance manifest

For every adopted asset record: dataset ID/version, original URL, creator, downloaded filename, hash, acquisition date, local folder, label type, split membership, license text/location, allowed redistribution status, and preprocessing config. Mark missing entries `unverified`; never infer permission from public download availability. Share download instructions with teammates instead of uploading large external datasets into Git.
