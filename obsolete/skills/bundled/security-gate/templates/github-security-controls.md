# GitHub Security Controls

Use this as an implementation checklist rather than copying unreviewed workflow YAML.

1. Enable secret scanning and push protection.
2. Run CodeQL or another SAST tool on pull requests and the default branch.
3. Enable Dependabot alerts and security updates.
4. Add dependency review to pull requests and fail on newly introduced High/Critical vulnerabilities.
5. Make security checks required through branch protection or rulesets.
6. Pin third-party actions to reviewed immutable commit SHAs; record the corresponding release tag in a comment.
7. Set top-level workflow permissions to read-only and grant narrower job-level permissions only when required.
8. Never execute untrusted pull-request code in a privileged `pull_request_target` workflow.
9. Keep secrets out of forked pull-request jobs and untrusted self-hosted runners.
10. Upload SARIF or machine-readable reports without including raw secrets.
