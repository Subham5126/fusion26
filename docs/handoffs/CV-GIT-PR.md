# What changed?

Publish the previously untracked spotGEO loader, preserved T03 detector, CV-T04
detector, evaluation/visualization tools, and CV-T06 shared-Detection adapter.
Fix the evidence CLI's Git lookup so installed modules use the caller's checkout.
Include an explicit publication allowlist and an independently tested packaging
proposal; the integration owner must approve/apply the root manifest separately.

## Why?

Teammates cannot reproduce detection from the existing backend distribution:
its wheel excludes astrotrace. The proposed root distribution includes app,
orbittrace and astrotrace with existing dependencies and unchanged imports.
Inference preserves native coordinates and never accepts annotation inputs.

## How was it tested?

- Full current repository suite: 236 passed, 0 failed, 0 skipped; one existing
  Starlette/httpx deprecation warning, 180.76 seconds.
- Regression test demonstrated the installed-CLI Git lookup failure before the fix.
- Fresh Windows CPython 3.12 environment, pinned dependencies, wheel installation
  and isolated-mode imports: current backend wheel fails to import astrotrace;
  proposed root wheel succeeds. pip check passes. Source distribution builds.
- Installed proposed package processes ESA train/84 with 7,7,6,8,6 detections and
  test/1107 with five empty outputs. Actual Member 3 source at c7227e9 consumes
  both without schema changes. Raw fallback is diagnostic; alignment is unverified.
- T03 frozen source hashes remain unchanged. No accuracy benchmark was rerun.

## Screenshots

Local evidence is deliberately excluded from Git. Generate candidates.png and
detections.json using the commands in docs/handoffs/CV-GIT.md. No ESA pixels,
archives, environments, secrets or generated reports belong in this PR.

## Checklist

- [x] Detector and adapter work locally with the tested packaging proposal.
- [x] Explicit source allowlist excludes unrelated work and generated data.
- [x] Applicable tests executed; limitations documented.
- [x] Documentation and reproduction commands supplied.
- [ ] Integration owner approves root packaging and confirms PR target dev.
- [ ] Final staged diff and commit reviewed by the human operator.
- [ ] Ready to merge after team integration review.

Backend pipeline/API still selects neither detector; public integration is not
implemented. Existing remote branch is development, not dev. Member 3's old
handoff examples contain stale imports; use the verified actual interface.
