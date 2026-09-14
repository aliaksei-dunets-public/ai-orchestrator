# Security Review Checklist

- Route authentication, authorization, credentials, cryptography, payments, tokens, and security policy changes through the gate.
- Check injection, unsafe evaluation, disabled TLS verification, credential exposure, access-control regressions, and unsafe logging.
- Redact credential values from every finding and report.
- Critical and high findings block handoff; local policy bypass is forbidden.
