> Provenance: substantive findings below are retained from the supplied planning pack. This bootstrap did not re-run its web research or inspect dataset archives. The original catalog mentioned by the pack is not included in this repository; its requirement summary is inherited, and official rules/rights remain unverified.

# Primary sources and verification record

Checked 9 October 2026 in India local time. Links were inspected through web retrieval except where explicitly blocked. Published descriptions are not independent experiments. No large archive, model or dataset sample was downloaded during this task.

| ID | Source | URL | Verification use |
|---|---|---|---|
| S0 | User-provided FUSION catalog | Attached `Pasted markdown.md` | SPACE-02 requirement and synthetic-data permission |
| S1 | spotGEO v2 official record | https://zenodo.org/records/4432143 | Version, archive size/checksum, sequence overview |
| S2 | ESA spotGEO dataset page | https://kelvins.esa.int/spot-the-geo-satellites/dataset/ | Dimensions, rotation, object-definition caveats |
| S3 | ESA submission format | https://kelvins.esa.int/spot-the-geo-satellites/submission-details/ | Point annotation fields and coordinate convention |
| S4 | ESA problem/acquisition description | https://kelvins.esa.int/spot-the-geo-satellites/problem/ | Exposure regime, appearance and metadata limits |
| S5 | Official spotGEO starter kit | https://zenodo.org/records/3874368 | Validation/scoring tools and metric documentation |
| S6 | StreaksYoloDataset official record | https://zenodo.org/records/14047944 | Streak labels, format, archive and license-file presence |
| S7 | Jai's debris pipeline README | https://github.com/jaikr-dev/space-debris-detection-pipeline | Documented approach, limitations, future tracking, license display |
| S8 | UW eScience satmetrics | https://github.com/uwescience/satmetrics | Ground-telescope FITS streak-analysis reference |
| S9 | Frigate author repository | https://github.com/DanSRoll/frigate | FITS pipeline and annotation-development caveat |
| S10 | OpenCV feature detection | https://docs.opencv.org/4.x/dd/d1a/group__imgproc__feature.html | Line/streak detector API reference |
| S11 | OpenCV video tracking | https://docs.opencv.org/4.x/dc/d6b/group__video__track.html | ECC alignment and Kalman APIs |
| S12 | SciPy assignment | https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html | Minimum-cost assignment interface |
| S13 | Astropy WCS | https://docs.astropy.org/en/stable/wcs/ | Optional calibrated image-to-sky coordinate support |
| S14 | FastAPI upload docs | https://fastapi.tiangolo.com/tutorial/request-files/ | Multipart file-handling interface |
| S15 | Ultralytics model docs | https://docs.ultralytics.com/models/yolo11/ | Optional model train/inference reference; not telescope-trained proof |
| S16 | Frigate dataset DOI | https://doi.org/10.6084/m9.figshare.29545667 | Dataset reference; landing-page access blocked |
| S17 | Catalog Kaggle dataset | https://www.kaggle.com/datasets/sadianawar/debris-detection-dataset | Reference verified as a page; details not retrievable |

## Explicit verification limits

- Frigate dataset landing page returned an access error; exact archive size, annotation availability and reuse terms were not established.
- Kaggle did not expose enough content to assess actual samples/labels. Do not assume suitability from its name.
- StreaksYoloDataset lists `license.txt`, but its text was not retrievable in this session. spotGEO license text was not visible in extracted page content. Both require actual rights inspection before redistribution.
- Related repo findings are based on its README and public code-page inspection, not running the project.
- Library API documentation pages may show newer versions; the actual team environment must resolve compatible versions and record them.
- No official rubric, competitor selection count, organizer implementation rules or deadline format was verified.

All architecture, task allocations, timings, thresholds, data subsets and proposed innovations in this pack are our engineering recommendations, not claims made by these sources.
