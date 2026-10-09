# Practical security and repository hygiene

Scope: a local hackathon prototype with image uploads. Safeguards should support reliability without consuming the event with unrelated infrastructure.

## Input handling

- Allow PNG/JPEG in P0; FITS only through an explicit bounded optional adapter.
- Validate decoded image type and dimensions, not just filename extension or Content-Type.
- Enforce per-file, request-total, frame-count and decoded-pixel limits while reading. Reject decompression bombs and corrupt input cleanly.
- Generate server filenames and job IDs. Never join user-supplied filename/path into an unrestricted filesystem path.
- Accept ordered individual frames rather than arbitrary ZIP uploads in P0. If archives are later supported, defend against traversal and expansion bombs first.
- Whitelist bounded config overrides. No arbitrary Python expressions, shell execution, pickle/model deserialization, filesystem paths or remote fetch URLs from the client.

## Storage and serving

Store artifacts in job-scoped directories. Resolve the canonical path and verify it stays inside the permitted root before serving. Prevent one ID from traversing to another job or the repo. Logs may include job IDs and safe stages; keep full raw tracebacks out of client responses.

Bind backend to localhost by default. Use explicit dev origins. If later exposed online, add proper request/session isolation, quotas and retention before allowing public uploads. The planning task does not authorize public deployment.

## Git and credentials

Ignore `.env`, local secrets, `.venv`, `node_modules`, caches, external dataset archives, generated bulk images, weights, uploads and job artifacts. `.env.example` contains safe placeholders only. Commit small synthetic fixtures created by us only when useful and clearly labeled. Do not embed organizer credentials or unrelated account data in this project.

Record reused code/assets and their licenses in credits. Preserve required notices. Do not automatically assign a repository-wide license that conflicts with incorporated code; let the team choose after dependency review.

## Targeted verification

Test corrupt input, oversized dimensions, excessive frames, unknown job ID, path traversal attempt and invalid config. Ensure failed jobs become terminal and clean up incomplete uploads according to the chosen retention policy. Avoid adding an account system or complex production security framework to P0.
