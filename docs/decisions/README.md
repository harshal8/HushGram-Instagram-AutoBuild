# Decision records

Short, append-only notes answering a question the code cannot answer: *why is it
this way, and what did we try instead?*

Write one when a future reader (human or agent) could plausibly "fix" the thing
back. The code comment that guards the rule should link here, and the file should
name the verification that keeps the rule true.

## Format

```markdown
# NNNN — <title in present tense>

**Status:** accepted (YYYY-MM-DD) | superseded by NNNN | deprecated
**Affects:** <paths, branches, wire formats, external state>

## Context        what the situation was, and what broke or nearly broke
## Decision       the rule, stated so it can be checked
## Rejected alternatives   each one, with the reason — this is the section that
                          stops the same idea being re-implemented in six months
## Consequences    what is now someone else's problem, and how to recover it
## Verification    the test or command that keeps the decision true
```

Number files monotonically, never renumber or delete one; supersede instead. Keep
each under ~100 lines — if it needs more, it is two decisions or an architecture
document.

## Index

| # | Decision | Affects |
|---|---|---|
| [0001](0001-release-metadata-ownership.md) | Release metadata is owned by whoever names it | release uploads, archive releases |

Worth writing next, because the reasoning currently lives only in comments and
commit messages: why manifests moved from release assets to the `website` branch
(2026-09-25), why blocked patch sources are skipped rather than retried, why
download prewarming was rejected, and why tuning knobs live in `build.yml` env
instead of repository variables.
