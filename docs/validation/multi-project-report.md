# Multi-Project Validation Report

The strict acceptance matrix covers 16 combinations: four platform profiles, Python and ABAP/RAP, and managed plus standalone installation. Each cell validates profile loading, evidence-based technology detection, idempotent onboarding, lifecycle contract availability, and isolated import of the 1.0.0 artifact.

Run:

```powershell
python tests/acceptance/run_matrix.py --strict
python tests/acceptance/run_matrix.py --release 1.0.0 --strict
```

## Contract matrix evidence

The matrix result and platform maturity are separate signals. All cells must pass the common repository contract; maturity additionally records whether the adapter has been observed in its native host.

| Platform | Contract matrix | Native smoke | Maturity |
| --- | --- | --- | --- |
| Codex | passed | passed | stable |
| Google Antigravity | passed | not run | experimental |
| GitHub Copilot VS Code | passed | not run | experimental |
| Claude VS Code | passed | not run | experimental |

## Native host evidence

The Codex smoke run was observed on 2026-07-28 in Codex Desktop 26.721.4979.0, Windows NT 10.0.26200.8875 (25H2, AMD64), with Python 3.12.13. The focused platform contract/scenario suite, strict 16-cell workspace matrix and strict 1.0.0 release-artifact matrix completed successfully.

Vendor-host-specific UI/tool discovery for Google Antigravity, GitHub Copilot VS Code and Claude VS Code has not been observed independently. Their profiles remain experimental until a native run records host/version, OS/runtime, date, executed scenario and result; external ABAP commands likewise require approval and compatible vendor tooling.
