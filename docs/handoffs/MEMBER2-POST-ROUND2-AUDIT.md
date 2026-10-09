# Member 2 post-Round 2 requirement audit

Base: origin/development `61e381065642a592eef5ace97cb32cb3eefefb33`.
Original publication branch: Subham `922fb937a109ec3231d7ec462bb88f3fdbdd62b4`.
Isolated working directory: `E:\Fusion-member2-post-round2`, detached HEAD.
This audit precedes implementation. Final measured outcomes are in the companion handoff.

T14 in BACKLOG means the spotGEO adapter. CV-T14 is the subsequent robustness
milestone. T17 corresponds to the CV-T15 optional YOLO experiment, not BACKLOG
T15 tracking ablation. These implementations are distinct and will be preserved.

| Requirement | Audit classification | Existing evidence / remaining action |
|---|---|---|
| T13 native grayscale arrays | Already implemented | uint8/uint16/finite normalized floats, bounded dimensions; rerun tests |
| Explicit reference and raw-to-reference direction | Already implemented | frame0, 3x3 translation matrices; known-shift tests |
| Inverse transforms / integer pixel centers | Already implemented | transform_points inverse, warp mask, exclusive boxes |
| Numerical residuals and independent validation matches | Already implemented | fitting/reserved validation counts/ratios/RMSE; rerun five ESA diagnostics |
| Registration rejection / no fake identities | Already implemented | failed records have null matrices, whole-sequence conversion refuses failure |
| Invalid/nonfinite input | Already implemented | normalizer/config tests reject NaN, wrong dtype, dimensions and truth keys |
| Timestamp preservation | Already implemented | registration takes pixels only; adapter timestamps None; test supplied timestamps remain unchanged |
| Real registration calibration / broad validation | Implemented but insufficiently validated | five reused diagnostic sequences; residuals do not establish true camera/astrometric error |
| Rotation/affine recovery | Missing, intentionally deferred | translation-only gates reject unsupported motion; no evidence warrants relaxing them |
| T14 directory / bounded ZIP adapter | Already implemented | SpotGeoDataset, safe archive support, no extraction/download |
| Exactly five ordered real frames | Already implemented | explicit official 1..5 to internal 0..4; equal native dimensions |
| Annotation schema and conventions | Already implemented | strict separate parser, raw half-pixel bounds, no persistent identities |
| Unknown timing and truth separation | Already implemented | metadata-only sequences; labels only in separate evaluation helpers |
| Deterministic selection / reproducible detection metrics | Already implemented | frozen whole-sequence membership, config hashes, gated point matcher |
| Dataset provenance / actual source inspection | Implemented but insufficiently validated | publisher/version/rights documented; local archive checksum/acquisition chain not independently verified |
| Registration before reference tracking | Already implemented in bridge | failed sequence is refused, including empty detections; Member 1 must adopt the policy |
| T07/T09 production telescope integration on committed development | Blocked by another team member | missing-registration placeholder; working unpublished integration exists separately; this task must not edit it |
| Clean packaging of astrotrace on committed development | Blocked by another team member | backend discovery excludes src; use source PYTHONPATH locally, propose packaging to Member 1 |
| CV-T14 robustness | Already implemented | suitability/stress/inventory/evaluation; rerun existing tests without rewriting |
| T17 real model / architecture / provenance | Already implemented, verification pending | local best.pt + five-epoch results + YOLO26n experiment documentation |
| Trained CPU inference | Implemented but insufficiently validated | old reports mainly GPU; run a bounded CPU sample with existing checkpoint |
| Held-out measured accuracy | Already implemented, caveats | 333-image test evidence; assumed negatives and unavailable session IDs limit independence |
| Fair classical versus YOLO replacement evidence | Missing | ESA points and streak boxes are different tasks; retain classical detector |
| New training / model download | Deferred | not required or authorized automatically |
| T18 local FITS data | Available | 2,000 raw Frigate files; sampled primary image 9600x6422, BITPIX16, BZERO32768 |
| FITS timestamp / exposure metadata | Inspection pending | DATE-OBS and EXPTIME present; preserve strings/time-scale uncertainty |
| Bounded FITS-to-NumPy conversion | Missing | no existing FITS module; full images exceed 4M-pixel schema limit; add local inspection/cutout helper only |
| FITS tests / real sample evidence | Missing | add bounded scientific scaling, origin, invalid/header/resource tests and real cutout validation |
| Frigate rights / labels / WCS / physical calibration | Insufficiently validated | local source lacks provenance manifest; no redistribution or physical inference |
| Synthetic demo regression | Implemented, rerun required | use unchanged merged T07 trusted synthetic path |

Implementation scope: T18 local FITS inspection/cutout module and owned tests;
bounded audit/reproduction evidence and Member 1 handoff. Modify T13/T14 only if
rerun reveals a genuine defect. Do not change pipeline, routes, schemas, tracker,
frontend, root dependency files, STATUS/BACKLOG or any existing worktree.
