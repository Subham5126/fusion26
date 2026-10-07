# CI and Dependency Update Preparation

No executable workflow is included because there is no application or selected stack yet.

After selecting the stack and package manager:

1. Add a GitHub Actions workflow using the actual project's verified commands.
2. Run applicable lint, tests, build, and security checks on PRs and the agreed branches.
3. Use minimal workflow permissions, reviewed action versions pinned to commit SHAs, and GitHub repository secrets for credentials. Keep untrusted PR code away from privileged secrets.
4. Document required checks in the contribution guide and enable them in branch rules after they run successfully.
5. Configure `.github/dependabot.yml` immediately for the selected package ecosystems and manifest locations, including GitHub Actions when workflows are added. Agree on update cadence and reviewers; do not guess ecosystems now.

Commit appropriate package manifests and lockfiles after dependencies are introduced.
No `dependabot.yml` is included at this stage.
