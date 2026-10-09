# 24-hour execution plan

Hours are relative to the official event start. Exact start/end time and submission rules must be confirmed with organizers. Do not hard-code the current research time as hour zero.

| Hours | A — integration | B — data/CV | C — tracking/evaluation | D — UI/demo | Exit evidence |
|---|---|---|---|---|---|
| 0–2 | Inspect repo; contracts, schema and scaffold | Generator design; inspect optional real samples | Matching and tracker interfaces | Wireframe + contract fixture | Contracts frozen; tasks assigned |
| 2–6 | CLI glue + health API | Seeded generator and baseline | Association on fixture; metric matcher | Ordered frame viewer + overlays | One honest CPU end-to-end run |
| 6–10 | Analysis job lifecycle and exports | Noise/artifact cases; alignment prototype | Missed-frame continuity + trajectory | Track panel, observed/predicted styling | Hard case processed; metrics executable |
| 10–12 | Integrate and smoke test | Optional spotGEO adapter if ready | Held-out synthetic evaluation | Connect UI to actual job results | Full live demo, or activate viewer fallback |
| 12–16 | Reliability and error paths | Real-data inspection or core improvements | Ablations and failure analysis | Benchmark comparison + warnings | Measured results and provenance saved |
| 16–18 | Merge stable features; freeze | Fix remaining P0 issues | Re-run only changed checks | UI cleanup, pitch assets | Scope frozen; no new dependency chain |
| 18–22 | Clean-checkout run; submission docs | Validate manifests and credits | Final benchmark after algorithm freeze | Record backup demo and rehearse | Reproducible release candidate |
| 22–24 | Submission packaging and final fix buffer | Support only | Support only | Present and submit per rules | Correct files submitted before deadline |

## Checkpoint decisions

**Hour 2:** schemas and path ownership agreed. If team cannot implement React + API comfortably, switch to Streamlit now. Do not split into incompatible app designs.

**Hour 6:** a fresh generated sequence must pass through detector, tracker and result export. If not, drop optional training and real-data work. Simplify association to declared constant-velocity gating; retain honest limitations.

**Hour 10:** at least one difficult case must be evaluated. If camera alignment fails, support the stable-camera mode and report unsupported alignment conditions. Do not hide rotation failures.

**Hour 12:** frontend consumes real pipeline results. If not, switch to CLI analysis + simple viewer. Freeze the API rather than continually changing field names.

**Hour 18:** feature freeze. Fix correctness, portability, labels and crashes. Drop unfinished YOLO/FITS/3D enhancements.

**Hour 22:** final evidence and submission artifacts ready. Only critical fixes; no broad refactors.

## Before the official clock

Confirm what preparation is permitted. Downloading public resources, setting up tools and writing plans may be allowed, but do not assume prebuilt implementation or pretrained work can be submitted unchanged. Verify event rules and record the team's starting assets honestly. No official rule was verified in this research.

## Rest and resilience

Rotate short breaks after milestone delivery. Keep at least one person available for integration. Store a runnable snapshot, config, report and short demo recording after hour 12. Do not make the final pitch depend on live internet or a last-minute dataset download.
