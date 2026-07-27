# DEC-005 Platform Maturity Design

Date: 2026-07-28

Decision: option 1 accepted

## Architecture and contract

Maturity is metadata of a platform profile rather than a platform-name branch in Core. Every profile declares `maturity` as `stable` or `experimental` and a `validation` object with contract-matrix status, native-smoke status and evidence pointers. The existing capability resolver remains unchanged: maturity communicates confidence and release support level, while capability modes still control whether a concrete operation is native, fallback or blocked.

Every profile must contain at least one evidence pointer. A `stable` profile is valid only when both `contract_matrix` and `native_smoke` are `passed`. An `experimental` profile may pass the shared matrix while its native smoke remains `not_run`; this lets the repository verify common contracts without presenting simulation in the current host as independent vendor-host validation. Promotion is data-driven: update the native result and evidence, change maturity, and rerun the same schema, contract and acceptance checks.

Codex starts as stable because the current Codex Desktop host is directly observable. Google Antigravity, GitHub Copilot VS Code and Claude VS Code start as experimental until each is exercised in its own host. Evidence for promotion must identify host/version, OS/runtime, date, command or scenario, and result.

## Data flow, failures and testing

`load_platform_profile` validates maturity before resolving capabilities. Missing fields, unknown statuses, empty evidence items or a stable profile without complete validation fail closed with `PlatformProfileError`. The JSON Schema mirrors these requirements, including the stable-profile invariant, so runtime and declarative validation agree.

The 16-cell acceptance runner continues to pass cells based on functional contract behavior, but now emits `platform_maturity`, `native_smoke` and contract-matrix evidence for every result. Therefore an experimental adapter does not fail the shared matrix; the report clearly distinguishes repository contract evidence from native-host evidence.

Contract tests verify the required platform order, maturity assignments and the failure case for premature stable promotion. Scenario tests verify that maturity does not alter capability routing. Final acceptance requires focused platform tests, full discovery, strict workspace and release-artifact matrices, manifest regeneration, Health Check without `ERROR`/`CRITICAL`, audit without findings, documentation link validation and zero release-artifact drift.
