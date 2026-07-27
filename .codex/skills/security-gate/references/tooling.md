# Tooling Strategy

Use repository-configured tools first. Do not install anything automatically. Commands are examples; verify the installed version's help before using unsupported flags.

## Secrets

### Gitleaks

Staged changes:

```bash
gitleaks git --pre-commit --redact --staged --verbose
```

Current filesystem:

```bash
gitleaks dir . --redact --no-banner
```

Git history:

```bash
gitleaks git . --redact --no-banner
```

Commit/range history can be narrowed with `--log-opts`. Always use redaction. Prefer the repository's `.gitleaks.toml` and reviewed baseline when present. Never create broad path-based exclusions merely to make a scan pass.

A baseline suppresses previously reviewed findings; it does not make an exposed credential safe. Revalidate old secrets separately.

## SAST

Prefer configured CodeQL, Semgrep, Sonar, Snyk, Bandit, Brakeman, SpotBugs/FindSecBugs, gosec, cargo-clippy security rules, or equivalent tools.

Semgrep example when network access and registry rules are allowed:

```bash
semgrep scan --config auto --error --metrics=off <paths>
```

Prefer local pinned rules for reproducible CI. Limit diff-mode runs to changed source plus necessary context; use a full scan for release gates.

## Dependencies / SCA

OSV-Scanner full source scan:

```bash
osv-scanner scan source -r .
```

Trivy filesystem scan:

```bash
trivy fs --scanners vuln,misconfig,secret --severity HIGH,CRITICAL .
```

Ecosystem-native examples:

```bash
npm audit --audit-level=high
pip-audit
cargo audit
govulncheck ./...
dotnet list package --vulnerable --include-transitive
bundle audit check --update
```

Do not run package installation to create a lockfile during an audit unless explicitly authorized. Never execute lifecycle scripts merely to scan dependencies.

## IaC, Containers, and CI

Select only when relevant:

```bash
trivy config .
checkov -d .
tfsec .
hadolint Dockerfile
actionlint
```

For container images, scan the exact immutable image digest intended for deployment when available.

## GitHub-Native Controls

When the repository is hosted on GitHub, verify whether these controls are enabled and required:

- secret scanning and push protection;
- CodeQL/code scanning on pull requests;
- Dependabot alerts and security updates;
- dependency review for new dependencies;
- branch/ruleset enforcement for security checks.

A local hook is developer feedback, not the final enforcement boundary. Repeat critical checks in CI because local hooks can be skipped or modified.

## Missing Tools

If a scanner is unavailable:

1. do not claim it ran;
2. continue with manual analysis;
3. record the missing category as a coverage gap;
4. recommend the smallest appropriate tool/configuration for the detected stack.
