---
provider: openai
model: gpt-5.5
checked_at: 2026-07-14
verification_required_for:
  - current feature availability
  - current API parameter recommendations
---

# OpenAI GPT-5.5 Guidance

Source checked:

- https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.5

Prefer a fresh baseline during migration rather than copying all legacy scaffolding. Audit whether structured output, static-first prompt layout, and runtime verbosity/reasoning controls can replace repeated natural-language instructions.

Apply this guidance only to gpt-5.5 and only when supported by the artifact, runtime configuration, or eval results. If current verification is unavailable, label version-specific claims as potentially stale.
