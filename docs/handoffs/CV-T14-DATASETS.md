# CV-T14 wider dataset inventory and proposed training plan

OrbitTrace / Member2, 9 October 2026. Evidence:
`artifacts/reports/cv_t14/inventory.json`. Read-only local audit, completed exit 0.
Every requested image header, streak label file and flat train/val CSV record
inspected; ESA annotations rely on earlier strict-parser validation, not a new
global annotation audit in this task. All non-ESA
encoded image files SHA256 hashed; no source copied/downloaded/repaired.
All 61,398 headers readable; dimensions/modes below are header evidence, not a
claim of full pixel decoding. Three ESA five-frame sequences were fully decoded
for the separate robustness run. train/0.jpg and streak train/images/1.jpeg were
also visually inspected; appearance is not label provenance.

| Source under E:\Fusion | Images | Dimensions/mode | Existing split |
|---|---:|---|---|
| data/raw/SpotGEOv2 | 32,000 | 640x480 L | train 6,400; test 25,600 |
| data/raw/StreaksYoloDataset | 2,388 | 640x640 RGB | train 1,722; validation 333; test 333 |
| data/raw/train | 20,000 | 512x512 RGB | flat train |
| data/raw/val | 2,000 | 512x512 RGB | flat validation |
| data/raw/test | 5,000 | 512x512 RGB | flat test |
| data/synthetic | 10 | 64x48 L | existing authored loader fixture |

ESA: five consecutive PNGs per sequence; existing strict train_anno.json and
test_anno.json point parser preserves native coordinates. GEO-like position
labels do not certify debris/satellite identity or provide persistent truth IDs
for our tracking score. No new real benchmark split chosen or tuned in CV-T14.
Use existing ESA documentation for attribution/license evidence; no redistribution
of official images in this source handoff. data/raw/README.md's old "no data"
statement is stale and was preserved rather than edited outside this task.

Streak data.yaml declares class0 **streak**, normalized cx,cy,w,h. The declared
`./data/yolo-streaks-dataset/...` paths do not resolve to this extracted dataset.
All observed labels use one row; no explicit empty label files or orphan labels.

| Split | Label files | Valid boxes | Missing label files | Invalid normalized rows |
|---|---:|---:|---:|---:|
| train | 1,193 | 1,189 | 529 | 4 |
| validation | 224 | 222 | 109 | 2 |
| test | 225 | 225 | 108 | 0 |

Invalid: train/labels/1028.txt, 1141.txt, 2092.txt, 2108.txt;
validation/labels/35.txt, 557.txt. All violate normalized bounds; no clipping or
automatic correction applied. 746 images lack labels. They may be intentional
negative examples or incomplete annotations: require source-owner confirmation.
Do not silently treat all of them as verified negatives. No extracted LICENSE,
source manifest or class-identity documentation was found under this source.
Streak is a visual morphology label, not confirmed orbital debris identity.
Training is blocked on rights/provenance, YAML ownership, bad-label review and
negative-label interpretation; it is not ready for a defensible judged model run.

Flat CSV source: train.csv/val.csv have ImageID,bboxes with safe Python list
literals. All 20,000/2,000 row IDs match image stems; no orphan or missing IDs or
literal errors found. 75,272/7,524 four-value boxes respectively. No empty rows
found. Values resemble xmin,xmax,ymin,ymax, but axis order, coordinate bounds,
class meanings, acquisition origin and license are **unverified**. Do not import
them through ESA parser or claim debris labels. No test truth supplied;
sample_submission.csv is not truth. Visual example train/0.jpg looks unlike the
ESA point targets; that observation cannot establish source/class identity.

Negative candidates: existing ESA empty point-label frames (via existing parser),
possibly the 746 unlabelled streak images after verification, and authored
synthetic empty/noise/daylight-like cases. None supplies sufficient independently
labelled real daylight/cloud/non-astronomical suitability negatives. ESA object
negatives are not daylight negatives. Flat CSV labels contain no empty rows.

## Leakage and training proposal (planned, not executed)

No cross-source or cross-split **encoded byte-identical** SHA256 duplicate groups
found among all 29,398 non-ESA images. This does not establish independence:
re-encoding, near duplicates, scenes, capture sessions and synthetic-family
dependence are untested. ESA was header-audited without new global hashes here;
its previous validation remains separate evidence. Do not count reused numeric
filenames alone as leakage or publish a blind-test claim from existing splits.

1. Obtain source/version/rights/class documentation for streak and CSV datasets;
   resolve the six invalid rows and confirm intentional negatives with source owner.
2. Integration owner proposes corrected YAML and any dependencies; do not silently
   repair shared configs from CV role. Retain originals and record repair manifest.
3. Fully decode images, validate label axes/boxes against overlays, audit decoded
   hashes/perceptual neighbors and group by source/capture session. Resolve leakage
   groups before choosing any new split. Keep ESA whole sequences together.
4. Preserve original splits and already consumed ESA regression sets as such.
   Freeze source/session-disjoint train/development/untouched final sets only after
   audit; ratios and final membership need source counts/session metadata first.
5. Curate independently labelled real daytime/cloud/city/blank/night hard negatives.
   Separate suitability labels from visual streak labels and debris identity.
6. After approved dependencies/rights/budget, train an actual licensed streak
   candidate model with declared seed/config/CPU budget and saved weights hash.
   A box model needs its own parser and center conversion reviewed against 0.1.0;
   retain classical T03/CV-T04 comparisons and native coordinates.
7. Freeze parameters before final evaluation; report detection and association
   tradeoffs separately. Test quantized/CPU runtime only on available hardware.

No training, YOLO installation, weights adoption, huge download or dataset copying
performed **by CV-T14**. Torch and Ultralytics are unavailable in this .venv; models/ contains
only README.md. Current working model is an untrained classical OpenCV candidate
detector. Provenance and calibrated debris classification remain unavailable.
The concurrent CV-T15 experiment reports an isolated training runtime, fuller
streak decoding/audit and external provenance investigation. Those claims are
separate from this header audit and were not independently rerun here; consult
that handoff before duplicating training or making cross-workstream conclusions.

Reproduce with `scripts/spotgeo_inventory.py --output <new ignored JSON path>`;
full PowerShell commands and module interfaces are in
`src/astrotrace/preprocessing/ROBUSTNESS.md` and CV-T14.md.
