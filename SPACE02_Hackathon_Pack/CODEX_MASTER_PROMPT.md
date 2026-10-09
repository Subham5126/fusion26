# Codex master prompt — create the real repository scaffold and project documents

Copy the entire prompt below into Codex **inside your actual FUSION repository**, with this planning pack attached or locally available. It does not authorize remote push or deployment. The prompt creates the initial structure and adapts the researched documents; subsequent role tasks implement the pipeline.

If the planning pack is not present in that Codex session, attach the ZIP or extract the folder beside the repository first. Do not assume a previous ChatGPT session's scratch path will exist on another computer.

```text
You are the repository bootstrap and documentation lead for our 24-hour FUSION 2K26 hackathon project, PS-SPACE-02: Ground-Based Optical Detection and Tracking of Orbital Debris. Working name: OrbitTrace.

The supplied SPACE02_Hackathon_Pack is our researched project specification. Your task is to create a practical file structure, detailed Markdown documentation, role-specific agent instructions, safe configuration and a minimal honest application scaffold in the current local repository. Do the work, verify it, and report the concrete result. Do not stop after proposing a file tree.

Scope for THIS run: bootstrap and docs, not a pretend finished detector. Do not download GB-scale datasets, train models, copy an unrelated repo wholesale, publish, deploy, push or merge remote branches. After the bootstrap, leave clear next task IDs so the team can implement in parallel.

1. INSPECT BEFORE EDITING

- Read all applicable existing AGENTS.md instructions, README, package/config files, git status and repository structure. Use rg/rg --files for discovery.
- Confirm the current directory is our intended local repo. Do not clone or manipulate a remote URL based only on earlier conversation context.
- Find the attached planning pack and read its README, PROJECT_BRIEF, RESEARCH, DATASETS, ARCHITECTURE, ALGORITHMS, CONTRACTS, TEAM, HACKATHON_PLAN, BACKLOG, EVALUATION, UI_SPEC, SECURITY, DECISIONS, STATUS, SOURCES and role prompts.
- Preserve existing work and user changes. Do not delete files, reset Git or replace a functioning stack unnecessarily. Adapt the structure if the current repo already has usable equivalent modules; document the mapping.
- If the pack is unavailable, say what is missing and use the specification below to make progress; do not invent researched facts or dataset rights. If current code conflicts with this plan, explain the concrete trade-off and choose the smallest compatible route.

2. PROJECT GOAL AND BOUNDARIES

Input: ordered real or synthetic telescope-image sequence.
Output: image-only candidate detections, persistent track IDs across frames, rough short image-plane trajectory, visual evidence and JSON/CSV report.

Synthetic sequences are permitted by the supplied PS and are the guaranteed end-to-end route. Real dataset validation is separate. Inference never reads generator truth, annotations, test labels or exact synthetic camera transforms. Predictions are not observations. Objects remain candidates, not verified debris. No physical orbit, altitude, collision probability or km/s from uncalibrated pixels. Unknown timestamps mean pixels/frame, not fabricated seconds.

Proposed stack: Python 3.11/3.12, NumPy, OpenCV headless, SciPy, Pydantic, FastAPI and Uvicorn; React + TypeScript + Vite viewer. CPU operation required, GPU optional. Optional extras: Astropy and a validated trained streak detector. If an existing lightweight stack works, preserve it and update the docs. No auth/database/chatbot/3D globe/cloud architecture in the bootstrap.

3. CREATE OR ADAPT THIS STRUCTURE

Root files:
README.md
AGENTS.md
.gitignore
.env.example
CODEX_MASTER_PROMPT.md

Documentation:
docs/PROJECT_BRIEF.md
docs/RESEARCH.md
docs/DATASETS.md
docs/ARCHITECTURE.md
docs/ALGORITHMS.md
docs/CONTRACTS.md
docs/TEAM.md
docs/HACKATHON_PLAN.md
docs/BACKLOG.md
docs/EVALUATION.md
docs/UI_SPEC.md
docs/SETUP.md
docs/SECURITY.md
docs/DEMO_AND_JUDGING.md
docs/RISKS.md
docs/DECISIONS.md
docs/STATUS.md
docs/SOURCES.md
docs/CREDITS.md
docs/agents/INTEGRATION_AGENT.md
docs/agents/DATA_CV_AGENT.md
docs/agents/TRACKING_EVALUATION_AGENT.md
docs/agents/UI_DEMO_AGENT.md
docs/handoffs/README.md

Backend:
backend/pyproject.toml
backend/app/__init__.py
backend/app/main.py
backend/app/api/__init__.py
backend/app/services/__init__.py
backend/app/core/__init__.py
backend/app/core/config.py
backend/app/schemas/__init__.py
backend/app/schemas/sequence.py
backend/app/schemas/result.py
backend/orbittrace/__init__.py
backend/orbittrace/pipeline.py
backend/orbittrace/io/__init__.py
backend/orbittrace/synthetic/__init__.py
backend/orbittrace/preprocessing/__init__.py
backend/orbittrace/registration/__init__.py
backend/orbittrace/detection/__init__.py
backend/orbittrace/tracking/__init__.py
backend/orbittrace/trajectory/__init__.py
backend/orbittrace/evaluation/__init__.py

Frontend:
frontend/package.json
frontend/package-lock.json (only a genuinely resolved lockfile)
frontend/index.html
frontend/tsconfig.json and actual Vite config
frontend/src/main.tsx
frontend/src/App.tsx
frontend/src/api/client.ts
frontend/src/types/contracts.ts
frontend/src/components/
frontend/src/pages/

Other:
configs/pipeline.yaml
configs/demo.yaml
scripts/README.md
scripts/generate_demo.py
scripts/analyze_sequence.py
scripts/evaluate.py
tests/README.md
tests/contracts/
data/README.md
data/manifests/
data/raw/
data/external/
data/synthetic/
data/ground_truth/
artifacts/README.md
artifacts/jobs/
artifacts/reports/
models/README.md

Create package initializers where importability needs them. Use small README markers to retain empty non-package directories; do not scatter dozens of purposeless placeholder files. Keep data/ground_truth out of inference paths. Do not create empty or fabricated model weights, dataset archives or benchmark results.

4. CONTENT REQUIREMENTS — WRITE DETAILED DOCS

Adapt and preserve the planning pack's substantive content rather than replacing it with generic TODOs. Every doc should tell teammates what to do, where to edit, inputs/outputs, completion evidence, dependencies, scope and known limits. Use clear English; short Marathi/Hinglish summaries may appear in the brief for easy understanding, but code identifiers remain English.

README: explain the problem, planned workflow, current readiness, directory map and document navigation. Distinguish runnable bootstrap commands from pending algorithm commands. No finished-project claims.

AGENTS: mission, file ownership, truthfulness, truth separation, coordinate/units rules, safe uploads, testing, dependency ownership, handoff and scope constraints. Inference modules must not read labels.

PROJECT_BRIEF: map detection/tracking/trajectory requirements to expected demo evidence; P0/P1/P2; honest judge interpretation, not an official rubric; definition of done.

RESEARCH/SOURCES: preserve primary links and verified caveats. spotGEO is GEO/near-GEO data with camera rotation and point coordinates; it is not a generic streak-classification/LEO debris dataset. StreaksYoloDataset is per-frame streak annotation, not guaranteed track IDs. Related Blender/YOLO repo lists tracking as future work; do not copy its reported accuracy. Frigate size/labels/license remain unverified in the supplied research. No “new research novelty” claim for established tracking methods.

DATASETS: synthetic-first strategy; optional download steps and manifests; sequence-based splits; hashes; actual rights checks; no assumed track IDs from point arrays. No auto-download in this run.

ARCHITECTURE/ALGORITHMS: CPU image processing, profile-dependent registration, raw/reference coordinates, blob and streak proposals, bounded gated assignment with unmatched cases, track confirmation using real observations, short trajectory fit and error cases. Median background can erase slow targets. Persistent hot pixels are not solved by temporal confirmation alone.

CONTRACTS: implement schema version 0.1.0 and consistent frontend types. Required SequenceInput/Detection/Track/Trajectory/AnalysisResult structures; empty lists valid; null for unknown values; observed/interpolated/extrapolated points distinct; no arbitrary disk paths or URLs. Native image origin top-left; preserve external conventions through adapters. API routes, structured errors, bounded config and state transitions.

TEAM: four unnamed role slots; suggested Subham integration lead, but do not invent other names. Three/two-person adaptations. Owned paths and human/agent collaboration. Integration controls schemas/config/lockfiles; workers hand off changes rather than editing shared status concurrently.

HACKATHON_PLAN/BACKLOG: relative 0–24-hour plan, task IDs T01–T19, dependencies/acceptance; checkpoints at 2/6/10/12/18/22; CLI/simple viewer fallback if React is disconnected at hour 12; freeze features at hour 18. Official clock/submission rules remain to be confirmed.

EVALUATION: independent splits; point matching with explicit gate; TP/FP/FN and null denominator rules; matched-localization error with recall; synthetic identity metrics; future prediction evaluated without future fit points; runtime/hardware provenance; fixed-split ablations; honest failures. Do not report spotGEO identity metrics without identity labels. Do not turn interpolations into detection TP.

UI_SPEC: ordered frame viewer, playback, stable track IDs, evidence crops, raw/reference overlays, dashed predictions, source labels, error/empty states, actual job polling and measured comparison only when data exists.

SETUP: executable commands appropriate to the scaffold created. Document future CLI names as pending until implemented. Include Windows and Linux/macOS guidance and actual dependency resolution status.

SECURITY: streamed upload limits, decoded-image checks, traversal protection, bounded job concurrency, allowed artifacts, local binding, safe .env and Git ignores. No production auth scope creep.

DEMO_AND_JUDGING: three-minute truthful demo; judge Q&A on candidate identity, trajectory limits, existing repo differences, synthetic domain gap, hot pixels, timing and actual measured results.

STATUS: researched/planned/implemented/tested/blocked separately. Existing work gets credit only after inspection. Add exact bootstrap checks performed and next task; do not mark algorithms implemented because stubs exist.

CREDITS: source and asset provenance registry; actual license text/status; unknown fields unverified. Do not automatically select a repo-wide license that conflicts with reused materials.

Role agent docs: copy/adapt the four detailed prompts. Each worker gets assigned task IDs, owned files, required contracts, meaningful checks and a handoff. No automatic delegation unless available and explicitly authorized; these prompts are for team use.

5. MINIMAL HONEST SCAFFOLD

Implement importable package/config structures and the shared Pydantic models, plus a health route that truthfully reports which capabilities are still absent. The frontend can show project readiness and backend health with a clearly labeled schema fixture, but not fake tracks behind a run button.

Stub algorithm entry points may raise a clear NotImplementedError or fail with a structured not-implemented code. They must not return successful empty analysis to conceal missing functionality. CLI stubs must exit nonzero with a useful pending-task message; --help can work. Do not add an analysis API that reports success before real pipeline integration.

The public routes planned for later implementation are:
GET /api/health
GET /api/demos
POST /api/analyze/demo
POST /api/analyze/upload
GET /api/jobs/{job_id}
GET /api/jobs/{job_id}/result
GET /api/jobs/{job_id}/frames/{frame_index}
GET /api/jobs/{job_id}/exports/{format}
GET /api/benchmarks/{benchmark_id}

Upload defaults planned for implementation: 3–30 images, 10 MiB/file, 50 MiB total and 4 megapixels/frame; one active CPU job. Unknown timestamp means frame units. Confirmation defaults to at least three observed points; prediction horizon one/two frames. Do not present defaults as validated scientific thresholds.

6. DEPENDENCIES, HYGIENE AND VALIDATION

Create real dependency declarations compatible with the chosen runtime. Resolve versions and lock using the available environment; do not hand-invent a lockfile or claim installation when network/dependencies fail. Keep optional training/Astropy separate from core imports.

.gitignore should ignore local environments, caches, node_modules, .env/secrets, bulk data archives/images, model weights and runtime artifacts while retaining data/README, manifests, our small licensed fixtures and docs. .env.example is safe placeholders only.

Verify relevant bootstrap behavior: Python syntax/imports and schemas; health response and truthful capabilities; TypeScript build if installed; relative Markdown links; no leaked secrets/large binary artifacts introduced; scaffold CLI help/pending behavior. Use meaningful schema/health checks, not a broad fabricated test suite for unimplemented algorithms.

If installs are blocked, finish files that do not depend on them, state the exact limitation and commands to run later. Never mark failing/unrun checks passed. Inspect git diff and preserve existing work.

7. FINAL HANDOFF

Return a short summary with concrete files created/changed, actual checks and outcomes, current readiness, unresolved issues and the next three assigned tasks. Suggested next tasks: B starts T02/T03, C starts T04/T06 on the shared fixture, D starts T08, while A prepares T07 integration. These parallel tasks depend on T01 contract freeze.

Do not implement all team roles secretly in this bootstrap run. Leave a detailed reviewable scaffold and accurate docs so our team can follow them throughout the hackathon. Do not push or deploy.
```

## After bootstrap

Give each teammate the appropriate role prompt in `docs/agents/` and an explicit task ID. The lead integrates handoffs and updates STATUS. If you later ask Codex to implement the whole project, make that a separate instruction with the same contracts and scope gates.
