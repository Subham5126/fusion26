# Contributing

## Branch Strategy

```text
main          stable, demo-ready code
  ↑
dev           integration branch
  ↑
feature/*     individual features
```

Create `dev` from the agreed stable base before feature work begins. This template does not create branches.

## Start a Feature

```sh
git checkout dev
git pull origin dev
git checkout -b feature/<feature-name>
```

Replace `<feature-name>` with a short descriptive name. Pull the latest `dev` before starting work.

## Commits

Keep commits small and use meaningful messages. These are format examples, not planned features:

```text
feat: add user dashboard
fix: resolve API error
docs: update README
refactor: simplify authentication
test: add API tests
chore: update dependencies
```

## Pull Requests

1. Implement and test the scoped change on `feature/*`.
2. Push your feature branch and open a PR targeting `dev` using the repository template.
3. Explain what changed, why, and how you checked it. Request a teammate's review.
4. Resolve merge conflicts carefully, inspect both sides, and retest the result.
5. Merge when review and applicable checks pass. Integrate and test on `dev`.
6. Open a PR from `dev` to `main` when the combined changes are stable and demo-ready.

## Team Rules

- Never push broken code to `main`; prefer PRs over direct pushes.
- Never commit secrets; follow [SECURITY.md](SECURITY.md).
- Test before requesting a merge and record the results. For documentation-only changes, check links and formatting.
- Update relevant documentation and the [task board](docs/TEAM_TASKS.md).
- Coordinate shared-file edits and communicate blockers early.
