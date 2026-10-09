# Shared contracts — version 0.1.0

Integration owner controls this file. Freeze at hour 2. Any incompatible change requires an entry in DECISIONS and a coordinated update of backend schemas, frontend types, fixtures and consumer tasks. Do not implement independently invented field names.

## Conventions

- JSON uses snake_case. IDs are opaque strings. `frame_index` is zero-based; ordered indexes are contiguous internally.
- Our own images use pixel centers at integer `(x,y)` with origin top-left; x points right and y down. Real adapters preserve/document external coordinate conventions.
- Float coordinates stay unrounded internally. Bounding boxes are `[x_min,y_min,x_max,y_max]` in pixels, with upper bounds exclusive.
- `raw` coordinates belong to the original image; `reference` coordinates belong to a declared aligned frame. Keep both whenever alignment is used.
- Timing is either monotonically increasing seconds or frame indexes. Unknown timestamps are `null`, not zero or fabricated ISO strings.
- Empty arrays are valid. Unknown metrics are `null` with an explanation, not 0. No NaN or Infinity.
- No raw disk paths in client responses. Artifact URLs must resolve through safe per-job handlers.

## SequenceInput

Required: `schema_version`, `sequence_id`, `source_type` (`synthetic` / `real` / `user_upload`), `profile`, `frames`. Each frame has `frame_index`, server-controlled image reference, `width_px`, `height_px`, optional `timestamp_s`. Dataset identifier/version and input hash are metadata. Inference inputs exclude labels and generator truth.

For P0 require all frames to share dimensions; explicit resizing belongs to an adapter with recorded scale transforms. Automatic guessing of order is not allowed when the supplied manifest is inconsistent.

## Detection

Required: `detection_id`, `frame_index`, `x_raw_px`, `y_raw_px`, `bbox_raw_px`, `kind` (`compact` / `streak` / `unknown`), `quality_score`, `detector_name`. Optional reference coordinates, endpoints and evidence statistics. Quality score range `[0,1]` means normalized heuristic unless calibration has actually been evaluated.

## Track and trajectory

Track: `track_id`, `status` (`tentative` / `confirmed` / `ended`), `candidate_label`, `points`, `observed_count`, `quality_score`, `warnings`, `trajectory`.

Point: `frame_index`, optional `timestamp_s`, `x_reference_px`, `y_reference_px`, optional raw coordinates, `point_type` (`observed` / `interpolated` / `extrapolated`), optional `detection_id`. Predicted points never have a fabricated detection ID.

Trajectory: `model`, `coordinate_frame`, `time_basis` (`frame` / `second`), `vx`, `vy`, `speed`, `speed_unit`, `fit_rmse_px`, `observations_used`, `predictions`. `vx/vy` use the same unit as speed. Fit reference epoch is stored explicitly if coefficients are exported.

## Example result — illustrative fixture, not measured output

```json
{
  "schema_version": "0.1.0",
  "job_id": "example-job",
  "sequence_id": "demo-fixture",
  "source_type": "synthetic",
  "profile": "synthetic_static_stars",
  "status": "succeeded",
  "time_basis": "frame",
  "coordinate_frame": "reference_frame_0",
  "registration": {"status": "identity", "warnings": []},
  "detections": [],
  "tracks": [],
  "metrics": null,
  "runtime_ms": null,
  "warnings": ["Illustrative empty fixture; not a benchmark run"],
  "provenance": {
    "input_sha256": null,
    "config_sha256": null,
    "code_commit": null,
    "dataset_version": null
  }
}
```

`metrics` is only populated by an evaluation step with ground truth. A user's ordinary upload must not suddenly display accuracy percentages. Store benchmark reports separately from inference results, with their matching protocol and sample membership.

## Local API

| Method / route | Input | Output |
|---|---|---|
| `GET /api/health` | None | Service status, schema version and truthful capability flags |
| `GET /api/demos` | None | Available local demo IDs, source type and descriptions |
| `POST /api/analyze/demo` | JSON `demo_id`, approved config override | `202` with job ID |
| `POST /api/analyze/upload` | Multipart ordered images and JSON manifest | `202` with job ID after validation |
| `GET /api/jobs/{job_id}` | Opaque ID | Job state, progress stage, warnings or structured error |
| `GET /api/jobs/{job_id}/result` | Opaque ID | Result when succeeded; `409` when unfinished |
| `GET /api/jobs/{job_id}/frames/{frame_index}` | ID and index | Original image for allowed job |
| `GET /api/jobs/{job_id}/exports/{format}` | JSON or CSV | Downloadable scientific report |
| `GET /api/benchmarks/{benchmark_id}` | Known local report ID | Separate measured comparison if present |

No route accepts an arbitrary filesystem path, remote fetch URL or shell command. Jobs have a bounded input and compute budget. Errors include `code`, readable `message` and optional safe details; no tracebacks in the UI.

## Upload defaults

3–30 frames; max 10 MiB per file, 50 MiB total request, max 4 megapixels decoded per frame. Config overrides are a whitelist with bounded values. Limits are our proposed defaults and must be enforced by the implementation, including streamed reads; they are not currently implemented.

## Exports

JSON includes detections, tracks, trajectory and provenance. CSV rows include job ID, source type, track ID, frame index, point type, raw/reference positions, timestamp if known and units. Exporting a prediction must not convert it into an observed measurement. Filename generation is server-controlled.
