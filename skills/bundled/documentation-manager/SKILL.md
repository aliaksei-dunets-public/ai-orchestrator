---
name: documentation-manager
description: Determine documentation impact from changed contracts, update only canonical owner-controlled documents, validate local links, and block completion on missing required documentation.
---

# Documentation Manager

1. Load `config/documentation-map.json` and compute impact from changed paths.
2. Require every mapped public contract document or record explicit non-applicability evidence.
3. Modify only canonical, hand-written documents owned by `documentation-manager`.
4. Regenerate generator-owned documents through their owner rather than editing them manually.
5. Validate local links with `orchestrator.documentation.broken_local_links`; block completion on broken links.
