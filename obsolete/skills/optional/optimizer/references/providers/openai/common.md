---
provider: openai
scope: common
checked_at: 2026-07-14
verification_required_for:
  - current API parameter recommendations
  - current feature availability
---

# OpenAI Common Guidance

Sources checked:

- https://learn.chatgpt.com/docs/prompting
- https://developers.openai.com/api/docs/guides/prompt-guidance-gpt-5p6
- https://developers.openai.com/api/docs/guides/latest-model

Use this file only for OpenAI model/runtime audits. Verify current documentation
when the recommendation depends on live API behavior.

## Audit implications

- Prefer outcome, constraints, and success criteria over unnecessary procedural micromanagement.
- Treat reasoning effort and output verbosity as separate controls when available.
- Prefer Structured Outputs for machine-consumed result shape.
- Evaluate prompt changes against representative tasks rather than equating shorter text with better performance.
- Place stable reusable prompt content before dynamic content when prompt caching applies.
- Use state continuation and compaction deliberately instead of replaying unbounded history.
- Keep tools focused, describe call criteria and important outputs, and reduce irrelevant tool-result text.
- Separate prompt behavior from application authorization, secrets, and side-effect controls.

Do not convert generic guidance into a mandatory rule without considering the
actual model, platform, task, and eval evidence.
