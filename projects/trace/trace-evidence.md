---
title: "TRACE evidence: decision chains"
short_title: TRACE evidence
description: >-
  Real decision chains from my TRACE records, drawn as linked graphs: who
  proposed, how a human ruled, what was corrected, and what was built.
site:
  hide_outline: true
---

Each chain comes from my TRACE records. Boxes are records; arrows are the
links stored in them. When a human rejects or revises an agent's proposal, the
ruling gets its own box pointing at the proposal. A revision points to the
decision it revises, a correction to what it corrects, and a contribution to
the decisions it carried out. Select a record to read it. For how much I use
TRACE overall, see [TRACE usage](/trace-usage).

```{include} _evidence_graph.md
```

Quotes are verbatim, except that other people's names are replaced with their
role, dashes are normalized, and long passages are trimmed at "[...]". Records
without a selected quote show a short excerpt. The links are read from the
records by the same code that builds [evidence.json](/static/evidence/evidence.json).

:::{dropdown} All chains as text
```{include} _evidence_excerpts.md
```
:::
