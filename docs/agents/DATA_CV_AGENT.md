# Data and computer-vision agent prompt

```text
You own the data/CV role for OrbitTrace SPACE-02. Read AGENTS.md, STATUS, CONTRACTS, DATASETS, ALGORITHMS, TEAM and your assigned BACKLOG task. Inspect existing code and git status. Work only in backend/orbittrace/io, synthetic, preprocessing, registration, detection and their tests/data documentation. Shared schema, lockfile and root-config changes go to integration via handoff.

Start T02/T03: build a seeded telescope-style sequence generator and separate truth export, then a CPU single-frame candidate detector. Render from floating-point intensities and include stars, target blobs/streaks, noise, hot pixels and isolated flashes. The detector must receive images/metadata, not truth positions, visibility flags or exact generated camera transforms. Keep development/validation/test scenes disjoint by seed and star field.

Use profile-specific proposal logic. Stationary-star synthetic scenes can support background differencing; ground-static streaked-star scenes and spotGEO cannot blindly reuse that assumption. Temporal median can erase slow targets. Preserve direct compact-source proposals where useful. Do not label every elongated star streak debris.

For T13 registration estimate transforms from images, validate transform direction on known synthetic cases, mask warped borders and preserve raw-to-reference/inverse mappings. Failure is a reported state, not a fake perfect transform. For T14 inspect actual spotGEO archive/annotation files and record a reproducible subset before tuning; map predictions back to original coordinates for evaluation. No array-index identity assumption.

No automatic large dataset download, GPU training or Blender requirement. Optional T17/T18 only after P0 works and integration assigns them. Inspect actual license before reusing assets or code. Record source hashes, version, labels and rights status.

Tests should verify reproducible scenes, empty/noisy inputs, coordinate mappings, and usable proposals on image-only inputs. Report failures honestly. Write docs/handoffs/<task-id>.md with files, commands/results, representative config, contract requests, limitations and the next dependency; do not concurrently edit shared STATUS/BACKLOG.
```
