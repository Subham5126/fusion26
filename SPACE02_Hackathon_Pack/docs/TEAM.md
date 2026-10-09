# Team and agent collaboration

Default: four role slots. Actual team members and skills have not been supplied. Subham can take the integration/lead slot if suitable; this is a suggested allocation, not a claim about roles already agreed.

## Role assignments

| Slot | Human assignment | Primary work | Owned paths | First deliverable |
|---|---|---|---|---|
| A — Integration/lead | Suggested: Subham | Contracts, API, pipeline glue, merge reviews, pitch | `backend/app/`, pipeline, root configs, scripts, shared schemas | Frozen contract + importable scaffold |
| B — Data/CV | Assign teammate | Generator, loading, detection, registration, provenance | `io/`, `synthetic/`, `preprocessing/`, `registration/`, `detection/` | Images + separate truth + single-frame detections |
| C — Tracking/evaluation | Assign teammate | Association, trajectory, matching, robustness tests | `tracking/`, `trajectory/`, `evaluation/` | Track fixture + honest benchmark runner |
| D — UI/demo | Assign teammate | Viewer, overlays, timeline, exports, visuals and demo capture | `frontend/` except shared types | Viewer over schema-valid fixture |

Each slot owns relevant tests. Evaluation design is reviewed by A/B to avoid tuning or label leakage. A controls shared type changes; D should propose transport changes early.

## Smaller or larger teams

- **Three people:** A combines integration and lightweight UI; B owns CV/data; C owns tracking/evaluation. Use Streamlit if combining UI consumes core time.
- **Two people:** one person owns generator/CV and one owns tracking/integration/viewer. Make React optional from the start.
- **Five or six people:** add an evaluation/provenance owner and demo/documentation owner. Give each a discrete task; do not split one module among several unsynchronized agents.
- GPU access changes only optional model work. The CPU detector remains the fallback.

## Collaboration rhythm

First 20 minutes: assign slots, inspect repository, confirm hackathon rules and freeze goal. Check in at hours 2, 6, 10, 12, 18, 22. Between checkpoints, a short status update every 90 minutes: completed evidence, current blocker, next deliverable. Do not spend the whole event in calls.

## Branch and merge policy

Use task branches such as `task/T02-generator` and small commits with one purpose. The integration owner reviews and merges. Maintain a working demo branch after hour 6. Do not force-push shared branches or commit generated datasets.

If each person runs a Codex agent, pass the same root AGENTS and contracts plus exactly one role prompt and task ID. Each agent needs a distinct worktree if editing a shared repository concurrently. When worktrees are unavailable, use strict file ownership and sequential integration. Shared lockfiles and schema edits belong to A.

## Handoff template

```markdown
# Handoff: Txx
Owner/role:
Base commit:
State: planned | in_progress | blocked | ready_for_review | done
Files changed:
Input contract consumed:
Output contract produced:
Commands actually run and results:
Reproducible sample/config:
Known failure or limitation:
Shared-file changes requested:
Next dependent task:
```

## Merge acceptance

A checks import/build compatibility, schema consistency, targeted tests, truth separation and a small end-to-end run. Refuse a change that only works inside one person's notebook or absolute local path. Merge functional increments; do not wait for perfect UI styling.
