# Skill Trigger Evals

## Should Trigger

- Check my staged changes for security issues before I commit.
- Audit commit `abc123` for vulnerabilities and leaked credentials.
- Review this pull request for auth, injection, dependency, and CI risks.
- Perform a full project security scan.
- Check whether this new MCP server or agent hook is safe.
- Scan Git history for exposed keys and tokens.

## Should Not Trigger

- Refactor this class for readability.
- Explain what OWASP is without reviewing code.
- Write a penetration-testing exploit against a live target.
- Produce compliance certification for this repository.
- Review only formatting and naming conventions.

## Expected Behavior

1. Defaults to staged scope for pre-commit requests.
2. Does not execute project code or install tools.
3. Uses deterministic scans before contextual reasoning.
4. Redacts all suspected secrets.
5. Validates source-to-sink exploitability and filters pattern-only noise.
6. Returns PASS/WARN/FAIL with explicit coverage gaps.
