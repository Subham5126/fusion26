# Prioritized task board

Initial state: every task is **planned**. Lead updates this board using handoffs. P0 tasks precede P1/P2 regardless of visual attractiveness.

| ID | Priority / owner | Task | Depends on | Acceptance evidence |
|---|---|---|---|---|
| T01 | P0 / A | Scaffold, schema and config | None | Imports and contract fixtures validate; docs state readiness |
| T02 | P0 / B | Seeded synthetic generator | T01 | Same seed/config produces same scene; truth separate |
| T03 | P0 / B | Loader and baseline detector | T01,T02 | Real candidates on image inputs; handles empty frames |
| T04 | P0 / C | Gated association and lifecycle | T01 | Stable IDs on fixture; invalid pairs unmatched; bounded misses |
| T05 | P0 / C | Trajectory fitting | T04 | Units correct; observed/predicted separation; finite output |
| T06 | P0 / C | Evaluator and splits | T01,T02 | One-to-one gated matching; empty cases; no split overlap |
| T07 | P0 / A | CLI end-to-end runner | T03,T04,T05 | Fresh generated images → result JSON; no label access |
| T08 | P0 / D | Frame viewer and track overlays | T01 | Correct native/resized coordinates; fixture labeled |
| T09 | P0 / A | Analysis API and exports | T07 | Job transitions work; bounded uploads; JSON/CSV consistent |
| T10 | P0 / B,C | Artifact and one-gap cases | T02–T07 | Negative scene evaluated; continuity measured, not assumed |
| T11 | P0 / D,A | Live UI integration | T08,T09 | No hard-coded track results; fresh job displayed |
| T12 | P0 / A,C | Held-out benchmark + offline demo | T06,T07,T11 | Report has config, seeds, counts, runtime and limitations |
| T13 | P1 / B | Registration and transforms | T03 | Known synthetic transform direction and round-trip correct |
| T14 | P1 / B | spotGEO adapter | T03,T13 | Actual annotation schema inspected; raw-coordinate evaluation |
| T15 | P1 / C | Temporal ablation and hard-case report | T06,T10,T13 | Same split/config fairness; no fabricated improvement |
| T16 | P1 / D | Evidence crops and comparison panel | T11,T12 | User can inspect support and warnings per track |
| T17 | P2 / B | Optional trained streak adapter | P0 done | License known; weights provenance; held-out comparison |
| T18 | P2 / B | FITS/Frigate subset inspection | P0 done | Headers/rights verified; no mandatory unverified metric |
| T19 | P0 / all; A integrates | Release and judge packet | T12 | Clean run, source credits, honest pitch, backup recording |

## Task-state rules

`planned` → `in_progress` → `ready_for_review` → `done`, or `blocked` with reason. A task is done only when its acceptance evidence exists. “Code written” alone is not completion. The review owner records the actual commands and outputs.

## P0 release checklist

- [ ] No truth path or test labels accessible to inference.
- [ ] Raw images, actual detections and stable track IDs visible.
- [ ] Measured points and predictions distinct.
- [ ] Correct speed units and explicit coordinate frame.
- [ ] Zero-target scene succeeds without fake detections.
- [ ] At least one hard case and one failure case documented.
- [ ] Benchmark labels, sample counts and matching threshold recorded.
- [ ] Clean environment runs documented commands.
- [ ] Dataset/code credits complete; no secret or large dataset in Git.
- [ ] Submission requirements confirmed.

## Repository bootstrap checkpoint — 9 October 2026

T01: ready_for_review, with files and actual evidence in STATUS and handoffs/T01.
All other T02–T19 tasks remain planned. Contract 0.1.0 is the proposed frozen
integration baseline; teammates review refinements before starting work.

Next assignments: B takes T02/T03; C starts T04 with the authored fixture and
T06 protocol work (real scoring waits for T02); D takes T08. A prepares T07
integration once T03/T04/T05 handoffs exist. These are unnamed role slots,
not claims that people/agents have already been assigned or started.
