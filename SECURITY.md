# Security Policy

## Secrets and Access

- Never commit API keys, passwords, database credentials, private keys, or access tokens.
- Use environment variables locally. Keep `.env` and its variants ignored; commit only `.env.example` with empty values or safe placeholders.
- Use GitHub repository secrets for CI/CD credentials; do not embed secrets in workflow files or logs.
- Apply least privilege to accounts, API scopes, database users, and deployment access. Keep development and production credentials separate when relevant.
- If a credential is accidentally exposed, revoke or rotate it immediately. Notify the team privately, inspect usage, and remove the exposed material. Deleting a file or commit alone does not invalidate a credential; coordinate any history cleanup with the team.

## Application Security After Stack Selection

- Validate inputs at trust boundaries; use safe query interfaces and context-appropriate output encoding.
- Require authentication where needed and enforce authorization on the server for every protected action. Check ownership and roles, not just whether a user is signed in.
- Avoid collecting unnecessary personal data. Redact sensitive information from logs and demos.
- Review dependencies, commit applicable lockfiles, and run the selected ecosystem's security checks. Configure Dependabot immediately after choosing the stack/package manager; see [CI preparation](.github/workflows/README.md).

## Reporting Security Issues

Do not post credentials, exploit details, or personal data in public issues. Contact [SECURITY_CONTACT] through [PRIVATE_REPORTING_CHANNEL], or use GitHub private vulnerability reporting if enabled.
Before publishing this project, replace these reporting placeholders. Include the affected file/component, impact, and safe reproduction steps, with secret values redacted.

## Hackathon Security Checklist

- [ ] Environment files ignored; `.env.example` contains no credentials.
- [ ] Secret scanning and push protection checked on GitHub.
- [ ] Credentials scoped narrowly; exposed credentials rotated immediately.
- [ ] Inputs validated; authentication and authorization checked where applicable.
- [ ] Dependencies reviewed and security checks run after stack selection.
- [ ] Logs, screenshots, recordings, and demo data contain no sensitive information.
- [ ] Private security reporting channel shared with the team.
