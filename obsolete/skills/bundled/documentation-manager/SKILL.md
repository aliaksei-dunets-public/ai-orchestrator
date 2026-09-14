---
name: documentation-manager
description: Determine documentation impact from changed contracts, update only canonical owner-controlled documents, validate local links, and block completion on missing required documentation.
---

# Documentation Manager

1. Read `docs/INDEX.md`, `docs/documentation-policy.md`, and
   `config/documentation-map.json`; compute impact from changed paths.
2. Require every mapped public contract document or record explicit non-applicability evidence.
3. Modify only canonical, hand-written documents owned by `documentation-manager`.
   Plans and specifications beneath `.orchestrator/` are contextual inputs, not
   documentation targets and must never be published mechanically.
4. Regenerate generator-owned documents through their owner rather than editing them manually.
5. Validate local links with `orchestrator.documentation.broken_local_links`; block completion on broken links.
6. Return exactly one `updated` or `not_applicable` disposition for every mapped
   canonical document. An update must appear in changed paths; non-applicability
   requires a concrete reason. Pass these dispositions to Task Finalization.
