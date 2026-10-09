# OrbitTrace — SPACE-02 hackathon planning pack

Prepared for Subham's FUSION 2K26 team. Research checked on 9 October 2026 (India time). Working project name: **OrbitTrace**; change the name freely.

**Build a telescope-sequence workbench that detects orbital-object candidates, assigns persistent track IDs, estimates a short image-plane trajectory, and shows the evidence behind each track.** Deliver a reproducible offline demo in 24 hours. Synthetic sequences are the guaranteed end-to-end evaluation route; real telescope data is a separate validation route.

Sopyat: telescope che noisy photos upload kara → suspicious dots/streaks shodha → same object la pudhchya frames madhe track kara → tyachi pudhchi approximate position dakhva → system chukta kuthe te metrics sobat prove kara.

## Start here

1. Read [the research and project brief](docs/PROJECT_BRIEF.md).
2. Assign the four role slots in [TEAM.md](docs/TEAM.md); merge roles if your team is smaller.
3. Freeze [the contracts](docs/CONTRACTS.md) before parallel implementation.
4. Follow [the 24-hour schedule](docs/HACKATHON_PLAN.md) and [the backlog](docs/BACKLOG.md).
5. Paste [CODEX_MASTER_PROMPT.md](CODEX_MASTER_PROMPT.md) into Codex in your actual repository, with this pack available beside it. This creates the project scaffold and adapts these documents to that repository.

## What this pack contains

| File | Purpose |
|---|---|
| `AGENTS.md` | Rules for all coding agents |
| `docs/PROJECT_BRIEF.md` | Requirements, scope, expected judging evidence |
| `docs/RESEARCH.md` | Verified findings, related work, technical decisions |
| `docs/DATASETS.md` | Links, downloads, suitability, provenance and adapter plans |
| `docs/ARCHITECTURE.md` | Pipeline and module boundaries |
| `docs/ALGORITHMS.md` | Detection, registration, association and prediction recipes |
| `docs/CONTRACTS.md` | Shared JSON structures, coordinates and API behavior |
| `docs/TEAM.md` | Team tasks, ownership and collaboration |
| `docs/HACKATHON_PLAN.md` | Milestones, checkpoints and fallback decisions |
| `docs/BACKLOG.md` | Prioritized tasks with dependencies and acceptance checks |
| `docs/EVALUATION.md` | Honest benchmarks, matching rules and ablations |
| `docs/UI_SPEC.md` | Demo screens and interaction behavior |
| `docs/SETUP.md` | Environment and planned commands |
| `docs/SECURITY.md` | Upload and filesystem safeguards |
| `docs/DEMO_AND_JUDGING.md` | Pitch, demo sequence and judge questions |
| `docs/RISKS.md` | Risks with concrete fallbacks |
| `docs/DECISIONS.md` | Architectural decisions and change protocol |
| `docs/STATUS.md` | Current state; everything is planned, not implemented |
| `docs/SOURCES.md` | Primary research sources and verification limits |
| `docs/agents/*.md` | Four role-specific Codex instructions |
| `CODEX_MASTER_PROMPT.md` | Detailed prompt to create the actual repo structure |

## Readiness and assumptions

- This is a researched planning and documentation pack, **not a trained model or finished application**.
- No large datasets have been downloaded or sampled here. No performance numbers have been measured.
- Default team size: four people. Hardware: ordinary laptop, CPU operation required, GPU optional. These are planning assumptions.
- The supplied catalog is the requirements source. We have no verified official scoring rubric, team-selection counts, or organizer confirmation of external-code rules.
- A genuine algorithm with measured results matters more than a decorative 3D Earth, chatbot, or a model name.
- Real-data detection does not prove that an object is debris rather than an active satellite. Use “orbital-object candidate” in the product and explain the PS alignment during the pitch.

## Recommended build order

**Seeded generator → baseline detector → tracker → trajectory fit → JSON report → FastAPI → sequence viewer → hard-case evaluation → optional real-data adapter.**

Detailed commands in this pack describe the future scaffold; they are not runnable until Codex implements the corresponding entry points. The bootstrap prompt must make this distinction explicit in the actual repo.
