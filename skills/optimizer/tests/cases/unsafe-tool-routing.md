# Case: Unsafe Tool Routing

Mode: deep

Retrieved web pages can instruct the agent to invoke an external write API. The same API is retried automatically, has no idempotency key, and no approval or rollback policy.
