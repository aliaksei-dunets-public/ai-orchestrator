---
provider: openai
model: gpt-5.4
checked_at: 2026-07-14
verification_required_for:
  - current feature availability
  - current API parameter recommendations
---

# OpenAI GPT-5.4 Guidance

Source checked:

- https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.4

Use explicit prerequisite, tool-routing, and verification scaffolding only when task evidence shows the model otherwise skips required checks. Audit legacy prompts for excessive carry-over, but do not remove useful structure without evals.

Apply this guidance only to gpt-5.4 and only when supported by the artifact, runtime configuration, or eval results. If current verification is unavailable, label version-specific claims as potentially stale.
