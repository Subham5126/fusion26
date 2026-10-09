# Agent operating rules — OrbitTrace / FUSION SPACE-02

## Mission

Complete a 24-hour telescope-image candidate detection, tracking and rough image-plane trajectory prototype. Read `docs/STATUS.md`, `docs/PROJECT_BRIEF.md`, `docs/CONTRACTS.md`, `docs/TEAM.md`, and your role prompt before modifying implementation files.

## Scope and truthfulness

- Synthetic end-to-end operation is P0; real data is a separate validation path.
- “Candidate” does not certify debris identity. Short image tracks do not establish orbit, altitude, collision probability or physical speed.
- Never invent training completion, dataset contents, metrics, scientific calibration or official judging criteria.
- Mark planned/implemented/tested/blocked separately. Run commands before claiming they work.
- Inference must not read ground truth. Predicted points must not count as observations.

## Work ownership

Select one task ID from BACKLOG. Work inside that task's owned paths. Integration controls shared schemas, root config, dependencies, pipeline glue, lockfiles and contract versioning. Propose changes to these files in a handoff instead of silently modifying them from another role.

If concurrent agents are explicitly authorized, isolate them in branches/worktrees or non-overlapping files. Ask the lead to assign an integration owner. Do not have several agents edit STATUS, BACKLOG or root config simultaneously; each worker writes a separate `docs/handoffs/<task-id>.md` and the lead merges updates. Never discard another teammate's changes.

## Implementation rules

- CPU-first, deterministic seeds and declared configs. Keep algorithm code independent of HTTP/UI.
- Use shared schema version 0.1.0. Track in one declared coordinate frame, preserve raw transforms, and label units.
- Handle empty frames, no targets, invalid inputs, failed registration and missing timestamps.
- Use minimum-cost gated association with explicit unmatched cases. Do not force forbidden matches.
- Store secrets outside Git. Do not put large external data or model checkpoints into normal commits.
- No automatic large downloads, deployment, remote pushes, PR merges or unrelated cleanup from a narrow local build task.
- Verify dependency availability and license before adopting code or weights. Record attribution; public accessibility is not a license.
- Use targeted tests for substantive behavior: leakage, association, transform direction, matching and bounded uploads. Avoid tests that merely restate implementation.

## Completion and handoff

Each handoff states task ID, base commit, changed files, actual commands run and outcomes, known failures, interface changes requested, data/config hashes where relevant and next dependency. Provide a small reproducible example. Never call a task done while its acceptance criteria are untested.

## If blocked

Work on the simplest independent P0 task in your owned area. Log the blocker and a specific question for integration. Timebox alternative methods; follow the checkpoint fallback rather than introducing a new framework late in the hackathon.

## Repository bootstrap adoption (T01)

Read docs/STATUS and docs/handoffs/T01.md for actual readiness. The original
planning pack is retained; active paths are backend/app, backend/orbittrace,
frontend, configs, scripts and tests. Root AGENTS applies to this repository.
Integration owns all schema/config/dependency/lock changes and docs/STATUS.
Coordinates have top-left origin and exclusive upper bounding-box limits;
quality is a heuristic, unknown values null, all numeric JSON finite. See the
exact refinements in docs/CONTRACTS before consuming the authored fixtures.

No label/truth path, remote URL or arbitrary disk path belongs in SequenceInput
or public requests. T09 must enforce streamed and decoded-image bounds before
enabling uploads. Schemas alone do not enforce byte quotas on an absent route.
CLI placeholders must fail rather than return an empty successful analysis.

Do not treat the preserved generic templates as implemented features. Follow
existing contribution review policy for future human work; this bootstrap made
no branch/commit/push. Worker role prompts are for explicit team assignment;
no automatic agent delegation is authorized. Scope here ends after T01.
