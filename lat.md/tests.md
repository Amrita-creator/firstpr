---
lat:
  require-code-mention: true
---

# Tests

Unit coverage for ranking rules that must not depend on GitHub or model providers.

Integration smoke scripts under `tests/` may call live APIs but are not required leaf specs.

## Ranker prefers beginner fit

Verifies a language-matched repo with contributing guide and beginner issues outranks a mismatched popular repo.
