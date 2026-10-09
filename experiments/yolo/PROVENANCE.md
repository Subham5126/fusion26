# CV-T15 provenance and label policy

Dataset: **StreaksYoloDataset v1.0.0**, Olivier Parisot, Luxembourg Institute of
Science and Technology. [Publisher record](https://zenodo.org/records/14047944),
DOI 10.5281/zenodo.14047944. The publisher describes Stellina observations from
March 2022–February 2023 in the Luxembourg Greater Region. The labels identify
visible streaks, potentially satellites, debris or cosmic rays; they do not
certify orbital debris identity or provide persistent tracking IDs.

Local source: `E:\Fusion\data\raw\StreaksYoloDataset`, inspected read-only.
Class 0 is `streak`, using YOLO normalized center-x, center-y, width, height.
All 2,388 images decoded as 640×640 RGB JPEGs. Six labels have zero width/height;
the prepared view excludes them without repairing source annotations. No exact
file/pixel duplicates were found; five cross-split pHash<=6 pairs were flagged.
Their lower-priority members were conservatively excluded. The source split
membership was preserved, and no image moved between train/validation/test.

Missing label files are **assumed negative under the YOLO convention**, supported
by [Ultralytics' dataset format](https://docs.ultralytics.com/datasets/detect/).
There are 746 such images in the source. A small positive/negative sample was
visually inspected, not an exhaustive annotation-completeness audit. Do not turn
these assumptions into certified negatives. Numeric filenames provide no
capture-session or parent-tile metadata; residual sequence/near-duplicate leakage
cannot be excluded by this appearance screen.

The separately published [license.txt](https://zenodo.org/records/14047944/files/license.txt?download=1)
was inspected and downloaded to ignored `.cache/cv_t15/streaks_license.txt`:
CC **Attribution-ShareAlike 4.0 International**, 20,566 bytes, MD5
`9c7b782221be99df5f5f94edb0bc1358` (matches publisher), SHA-256
`0bdfb0201d1803634f268cdff0993b8349d2c70e956a06dbb667c8dd65254ec5`.
The full archive is already extracted locally; this task did not download it or
verify the original ZIP MD5. Per-image/label hashes and exact exclusion membership
are in `.cache/cv_t15/audit/dataset_audit.json` and `dataset/membership.json`.
Redistributed dataset-derived panels need creator attribution and applicable
CC BY-SA terms; current image panels are ignored local artifacts.

Model: [Ultralytics YOLO26n Detect](https://docs.ultralytics.com/models/yolo26/),
nano scale, end-to-end detection head, RGB input, P3/P4/P5 outputs. COCO-pretrained
checkpoint from the official [v8.4.0 assets release](https://github.com/ultralytics/assets/releases/tag/v8.4.0):
`yolo26n.pt`, 5,544,453 bytes, SHA-256
`9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef`.
Loaded architecture: 2,572,280 parameters; one-class training reconstruction:
2,504,190 parameters, 606/708 checkpoint items transferred. Only the class head
and model state are adapted by the training library, not OrbitTrace's detector.

[Ultralytics licensing](https://www.ultralytics.com/license) identifies its code,
pretrained models and trained models as AGPL-3.0 by default, with an Enterprise
alternative. This experiment does not decide production distribution licensing
or change the repository's license. Integration must retain applicable notices
and review model redistribution/deployment terms before adoption.

The experiment uses its own environment, configs and output paths. No ESA point
annotations are converted to streak boxes or included in training. Streak-box
IoU metrics and ESA point-localization metrics measure different tasks and must
not be presented as a direct CV-T04 versus YOLO accuracy comparison.
