# Security Review Checklist

Load only the sections relevant to the detected stack and change scope.

## Secrets and Sensitive Data

Look for API keys, cloud credentials, exchange/bot tokens, OAuth client secrets, JWT signing material, passwords, database URLs, private keys, certificates with private material, webhook secrets, cookies, session tokens, encryption keys, recovery codes, and secrets embedded in URLs.

Also inspect:

- comments, examples, notebooks, test snapshots, fixtures, logs, crash dumps, shell history, CI output, Docker layers, generated files;
- encoded or split values, concatenated literals, base64/hex strings, high-entropy assignments to sensitive names;
- `.env`, credential files, kubeconfigs, service-account JSON, PEM/KEY/P12/PFX files;
- sensitive values placed in frontend bundles, mobile apps, public artifacts, or client-visible configuration.

Do not classify every email, UUID, hash, hostname, or public key as a secret. PII is reportable when it appears to be real production/personal data, creates a privacy risk, or is logged/exposed outside its intended boundary.

## Access Control and Multi-Tenancy

Check authorization on every sensitive operation and object lookup. Look for:

- direct object retrieval by user-supplied ID without owner/tenant checks;
- admin or role checks performed only in the UI;
- missing deny-by-default behavior;
- privilege inferred from mutable client claims;
- tenant IDs accepted from requests rather than trusted identity context;
- inconsistent authorization between read, update, delete, export, bulk, and background paths;
- cache keys or database queries missing tenant scope;
- mass assignment of privileged fields.

## Authentication and Session Security

Review login, registration, password reset, email change, MFA, API keys, OAuth/OIDC, JWT, cookies, and sessions:

- weak or reusable reset tokens;
- missing expiration, audience, issuer, nonce, state, or PKCE checks;
- accepting unsigned or incorrectly verified tokens;
- session fixation or failure to rotate after privilege changes;
- insecure cookie attributes;
- user enumeration with meaningful impact;
- credentials or tokens in URLs/logs;
- authentication failures that fail open.

## Injection and Output Handling

Trace untrusted input into:

- SQL/NoSQL/LDAP/XPath queries;
- shell commands, subprocesses, PowerShell, templates, interpreters, `eval`/`exec`;
- HTML/DOM, markdown renderers, email templates, HTTP headers, logs;
- file paths, archive extraction, dynamic imports, plugin names;
- serialization formats, regex engines, or expression languages.

Confirm whether parameterization, contextual output encoding, allowlisting, canonicalization, and argument-array APIs are used correctly.

## Network, SSRF, Redirects, and Webhooks

Check whether users can influence scheme, host, port, path, DNS resolution, proxy, redirect chain, or headers. Verify:

- allowlists are applied after parsing and normalization;
- private, loopback, link-local, metadata, and internal ranges are blocked;
- redirects and DNS rebinding cannot bypass checks;
- webhook signatures and replay protection are verified;
- callbacks do not expose credentials or privileged network reach.

## Files and Uploads

Check filename/path normalization, destination containment, archive traversal, symlinks, content-type validation, executable content, storage permissions, malware scanning assumptions, size limits, and access control on download/delete.

## Deserialization and Dynamic Code

Flag unsafe deserialization of attacker-controlled data, pickle/yaml/object streams, dynamic module loading, untrusted plugin packages, template compilation, and reflection-based class selection. Verify authenticity before deserialization when applicable.

## Cryptography

Check algorithm and mode suitability, key sizes, random generation, nonce/IV uniqueness, salt usage, password hashing, constant-time comparison, certificate verification, key rotation, and signature verification order. Do not flag MD5/SHA-1 used only for non-security checksums unless collision resistance matters.

## Error Handling, Logging, and Privacy

Look for stack traces, secrets, tokens, personal data, query contents, payment data, or internal identifiers in logs and errors. Check log injection, security-event coverage, exception suppression, broad catches, fallback-to-allow behavior, and retries that repeat financial or privileged actions.

## Dependencies and Supply Chain

Review newly added or changed packages first:

- known vulnerabilities and fixed versions;
- reachability or plausible use of vulnerable functionality;
- suspicious names, maintainers, registries, Git URLs, forks, or newly created packages;
- unpinned or floating versions;
- dependency confusion and private namespace handling;
- install/postinstall scripts;
- lockfile consistency and integrity hashes;
- vendored binaries, downloaded executables, generated clients, and checksums/signatures;
- abandoned or deprecated security-sensitive libraries.

## CI/CD and Repository Automation

Inspect workflows, hooks, release scripts, and bots for:

- broad `GITHUB_TOKEN` or cloud permissions;
- secrets exposed to untrusted forks or pull-request code;
- `pull_request_target` combined with checkout/execution of PR code;
- shell injection through branch names, titles, labels, commit messages, issue text, matrix values, or outputs;
- unpinned third-party actions or downloaded tools;
- artifact poisoning, cache poisoning, writable shared runners;
- unsafe self-hosted runners;
- deployment from untrusted refs;
- security steps marked continue-on-error or conditionally skipped.

## Infrastructure and Containers

Review public exposure, IAM wildcard permissions, network rules, encryption, logging, secret injection, privileged containers, host mounts, root users, capabilities, seccomp/AppArmor, mutable image tags, base image vulnerabilities, Terraform state, Kubernetes RBAC, service accounts, and default namespaces.

## Business Logic and Concurrency

Look for bypasses that static pattern tools often miss:

- replay, duplicate execution, race conditions, TOCTOU;
- negative or overflow values, rounding and currency errors;
- quota, limit, discount, entitlement, workflow-state, or approval bypass;
- missing idempotency for payments and external side effects;
- inconsistent validation between synchronous and background paths;
- partial failure that commits an unsafe state.

## Agent, Skill, and MCP Security

Treat model-readable content and tool output as attacker-controlled when it crosses a trust boundary. Review:

- instructions loaded from repositories, issues, web pages, documents, logs, or retrieved data;
- skills or MCP servers that request unnecessary filesystem, shell, network, credential, or write access;
- automatic execution of downloaded scripts or commands;
- secrets placed in prompts, context, traces, telemetry, or tool arguments;
- untrusted output reused as commands, paths, SQL, code, or authorization decisions;
- missing confirmation for destructive or privileged actions;
- skill metadata that over-triggers or attempts to override higher-priority instructions.
