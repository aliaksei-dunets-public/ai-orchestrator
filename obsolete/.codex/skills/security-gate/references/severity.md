# Severity and Confidence

Use severity for impact and exploitability; use confidence for evidentiary certainty. Do not inflate severity because a scanner labels an issue broadly.

## Critical

Typical examples:

- likely-valid production private key, cloud root/admin credential, signing key, or broadly privileged token;
- unauthenticated remote code execution;
- authentication bypass or universal account takeover;
- cross-tenant or mass sensitive-data compromise with little attacker effort;
- software-supply-chain execution path affecting downstream users/releases.

## High

Typical examples:

- exploitable SQL/command/template injection;
- broken object authorization exposing or modifying sensitive records;
- privilege escalation;
- SSRF reaching sensitive internal services or metadata credentials;
- unsafe deserialization with code execution or serious integrity impact;
- new vulnerable dependency with High/Critical advisory and reachable/plausible use;
- CI workflow that exposes secrets to untrusted code or grants privileged write/deploy capability.

## Medium

Typical examples:

- exploitable issue requiring authentication, unusual configuration, or constrained impact;
- sensitive data exposure limited in scope;
- meaningful security misconfiguration not immediately internet-exploitable;
- missing replay/idempotency protection with bounded impact;
- unresolved scanner result with strong evidence but incomplete reachability.

## Low

Defense-in-depth, weak hardening, low-impact disclosure, or theoretical concern without a demonstrated attack path. Exclude from the blocking table unless exhaustive review was requested.

## Informational

Coverage notes, tool availability, non-vulnerable observations, and recommended future controls.

## Confidence

- **High:** source, missing/failed control, sink, exploit path, and impact are demonstrated.
- **Medium:** strong evidence exists, but one material runtime/configuration fact is unknown.
- **Low:** pattern-only, speculative, or framework behavior not validated. Do not report as a confirmed vulnerability.

## Gate Mapping

- Critical/High + High confidence: FAIL.
- Critical/High + Medium confidence: WARN and Needs verification, unless a likely-valid secret is present; secrets fail immediately.
- Medium + High/Medium confidence: WARN.
- Low/Info only: PASS with observations.
