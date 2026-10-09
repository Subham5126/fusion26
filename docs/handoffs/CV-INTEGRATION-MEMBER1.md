# Member 1 — CV integration checklist after T13/T14

9 October 2026. Subham base `c802622800ed14739bd841ee840ec16cf905e4cd`.
CV library readiness verified; packaging/pipeline/API adoption belongs to you.
Evidence and publication plan: [CV-INTEGRATION.md](CV-INTEGRATION.md).

## Imports and exact callable boundaries

```python
from app.schemas.result import Detection, AnalysisResult
from astrotrace.datasets import SpotGeoDataset
from astrotrace.preprocessing.images import decode_png
from astrotrace.preprocessing.suitability import validate_sequence_suitability
from astrotrace.detection.optimized import OptimizedDetector, OptimizedConfig
from orbittrace.detection import FrameContext, detect_frame, detect_sequence
from astrotrace.preprocessing.registration import register_sequence, add_reference_coordinates

# Available on Member 3's branch, not canonical imports on current Subham:
from orbittrace.tracking.tracker import Tracker
from orbittrace.trajectory.fit import attach_trajectories
```

```python
decode_png(payload: bytes, *, max_pixels=4_000_000, expected_size=(640, 480))
# -> read-only native uint8/uint16 grayscale ndarray; PNG only

SpotGeoDataset(source, *, split="train", prefix=None, expected_size=(640, 480),
               max_pixels=4_000_000, max_image_bytes=16*1024*1024,
               archive_limits=ArchiveLimits())
SpotGeoDataset.load_sequence(self, sequence_id: str | int)  # -> image-only Sequence

validate_sequence_suitability(frames)  # -> dict; EXACTLY five decoded arrays
OptimizedDetector.detect(self, pixels, context: FrameContext, config)  # -> list[Detection]
FrameContext(frame_index, width_px, height_px, profile, timestamp_s=None)
detect_frame(pixels, context, config=None, *, method="optimized", sequence_id="sequence")
detect_sequence(frames, *, sequence_id, profile="spotgeo", timestamps_s=None,
                config=None, method="optimized")  # -> flat list[Detection]

register_sequence(frames, config=None)  # -> SequenceRegistration
add_reference_coordinates(detections, registration)  # -> new list[Detection]

Tracker(gate_distance_px=20.0, confirmation_observations=3,
        max_consecutive_misses=2, motion_aware=True, track_prefix="track", config=None)
Tracker.process_sequence(self, detections, frame_indices=None, frame_timestamps=None)
Tracker.process_frame(self, frame_index, detections, timestamp_s=None)
attach_trajectories(tracks, coordinate_frame="reference_frame_0", time_basis="frame",
                    prediction_horizon=2, frame_dimensions=None, frame_timestamps=None)
```

Import `ArchiveLimits` from `astrotrace.datasets.archive` if constructing it.
Full type annotations were captured via inspect.signature in the ignored
`.cache/cv_readiness/proposal_installed.json`. Do not confuse the flat bridge
`orbittrace.detection.detect_sequence` with the older local-envelope runner
`astrotrace.detection.runner.detect_sequence(sequence, detector, config)`.

## Adoption checklist

- [ ] Package `app`, `orbittrace` AND `astrotrace`. The existing backend wheel
  installed with all pinned dependencies fails with missing `astrotrace` under
  Python `-I`. The existing [root packaging proposal](CV-GIT-packaging.patch),
  applied only in an ignored copy, built/installed successfully and ran native
  detection plus registration on train/84 without source PYTHONPATH. The real
  root patch remains unapplied. No new classical runtime dependency is required.
- [ ] Integrate Member 3's reviewed source. Current Subham has tracking/trajectory
  initializers only; the successful compatibility tests use byte-identical Git
  snapshots from `a015cc949955d0438c8a16789b23746c3206f3d1`.
- [ ] Enforce streamed encoded-byte limits before decode, manifest order, decoded
  pixel bounds and safe job storage. `decode_png` is grayscale PNG only. JPEG/RGB
  uploads require a separately approved loader policy; current schema limits do
  not implement that decoder. Do not accept arbitrary disk paths/URLs publicly.
- [ ] Use **bounded load/decode -> suitability -> native detection + image-derived
  registration -> reference conversion -> tracking -> trajectory -> export**.
  Detection and registration are independent after the guard; both receive raw
  images. Aligned previews never become detector inputs.
- [ ] Suitability `supported` allows candidate inference, including valid empty
  star fields. `unsupported` and `uncertain` both have inference_allowed=false:
  expose reasons/review or reacquisition, and never emit empty successful analysis.
  Public status/error mapping needs your review; no new shared schema was added.
  The current rule set accepts only five frames, although SequenceInput accepts
  3..30. Restrict this profile explicitly until wider-length behavior is reviewed.
- [ ] If any registration frame fails, block **whole-sequence registered tracking**.
  Failed matrices remain null. The helper raises even if the failed frame has no
  detections. Raw diagnostic results may be retained separately and clearly
  labelled; never mix null-reference raw fallback with registered coordinates.
- [ ] Keep raw centroid/bbox/endpoints/ID/score unchanged. Matrices map raw into
  frame0: `[x_ref,y_ref,1] = raw_to_reference @ [x_raw,y_raw,1]`. Coordinates use
  top-left origin, integer pixel centers and exclusive upper boxes. Reference
  coordinates may lie outside the raw field; do not clip them. Preserve inverse
  transforms, diagnostics and warped-border masks through approved artifacts.
- [ ] Pass every frame index, including empty/trailing frames, to tracking. Use
  unknown timestamps null and px/frame; known monotonic seconds require the same
  frame_timestamps mapping throughout tracking/fit and px/s. Predictions remain
  extrapolated points without detection IDs and never count as observations.
- [ ] Preserve frozen CV-T04 by calling bridge method="optimized", config=None:
  threshold_sigma=4.5, max_context_elongation=2.0, denoise=.6, background=8,
  noise=12, area=3..150, elongation=2.5, cap=200, background_step=1,
  min_aperture_snr=0, max_peak_fraction=.55, max_component_aspect=20, min_score=0.
  Bare OptimizedConfig defaults are 5.5/2.5 for threshold/context. PipelineConfig
  defaults threshold_sigma=5.0 and calls its cap candidate_cap. Do not forward its
  whole dump to the detector: keys differ and unrelated fields are rejected.
  Review a bounded override mapping and record any intentional config difference.
  Capture CandidateLimitWarning and registration warnings in output provenance.
- [ ] Re-test installed canonical tracking imports, a fresh synthetic/real run and
  AnalysisResult validation after integration. Confirm 20px gate policy with
  Member 3; the earlier15px CV-T13 wording has been corrected to the source's20px.
- [ ] Implement T07 pipeline and T09 routes/jobs/upload bounds/artifact handlers/
  exports. Update capabilities and STATUS only after real HTTP analysis tests.
  Actual localhost checks here: health200; analysis demo/upload and demos404.
  analyze() still raises NotImplementedError. No successful analysis API exists.

## Actual examples and limits

ESA train/84: candidates [7,7,6,8,6], registration estimated, 31 registered tracks,
zero confirmed; raw diagnostic has23 tracks/3 confirmed. No real identity truth
exists here to call either association result accurate. Actual frame1 candidate:
raw=(71.35161699,418.06481770), reference=(41.18298448,410.51717976), raw box
[70,417,74,420], ID `saf4470bba67a858a-f1-c0`, name `opencv_context_filtered_v2`.

Controlled counts_change: [5,3,4,5,5], five confirmed tracks, 22TP/0FP/0FN,
17 correct links, zero switches/fragments, both scripted gaps recovered.
track-0001 observed frames[0,3,4], observed_count3; track-0005 frames[0,2,3,4],
observed_count4. Their predictions have no fabricated detection IDs.

Train/438 registration fails frames3/4 and blocks registered tracking. Persistent
artifact creates one false confirmed track; nearby4px targets are all missed;
blur guard bypass creates56 false confirmed tracks. These failure cases are
retained. Candidate/confirmed lifecycle never certifies debris, orbit or speed.
CV-T15 source, checkpoints and runtime remain a separate excluded publication.
