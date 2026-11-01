---
title: "TRACE usage"
short_title: TRACE usage
description: >-
  How much I use TRACE, the provenance MCP server I built: aggregate counts
  of my AI-assisted engineering records across five projects.
---

# TRACE usage

```{include} _evidence_claim.md
```

[TRACE](https://github.com/Thru-Echoes/TRACE) is the open-source MCP server I
built to record, during AI-assisted work, who proposed each decision, who
resolved it, and who had the idea and did the work for each artifact.
[proofpress](https://github.com/chenmingtang830/proofpress) ingests these
records; I co-founded Continuara Labs, the company building it.

:::{card} The evidence: decision chains →
:link: /trace-evidence
Twelve real chains from these records, drawn as linked graphs: an agent's
proposal and how I ruled on it, or a mistake and the correction that points
back at it.
:::

## By project

```{include} _evidence_table.md
```

## Session starts by week

:::{div}
:class: evidence-chart

```{image} /static/evidence/sessions-weekly-light.svg
:alt: Stacked bar chart of recorded TRACE session starts per week, March to November 2026, by project.
:class: evidence-chart-light
```

```{image} /static/evidence/sessions-weekly-dark.svg
:alt: Stacked bar chart of recorded TRACE session starts per week, March to November 2026, by project.
:class: evidence-chart-dark
```

:::

One session can run for days, so a quiet week is not a week without work.

## Who had the idea, who did the work

In most contribution records, the idea is human and the execution is AI.

:::{div}
:class: evidence-chart

```{image} /static/evidence/contributions-light.svg
:alt: Horizontal stacked bars showing, for each project, the share of contribution records by direction and execution.
:class: evidence-chart-light
```

```{image} /static/evidence/contributions-dark.svg
:alt: Horizontal stacked bars showing, for each project, the share of contribution records by direction and execution.
:class: evidence-chart-dark
```

:::

:::{dropdown} Table view
```{include} _evidence_contributions.md
```
:::

:::{dropdown} Methods and limits
- **Self-logged.** The agent and I write these records during the work. Each
  entry is attributable (it names who proposed, resolved, or did the work),
  but the records are not independently checked.
- **Scope.** Five project workspaces: TRACE, proofpress, proofpress
  experiments, COEQWAL (contract client work), and the RSI-Exam provenance
  study. Other projects and all meeting recordings are excluded.
- **Human entries.** Mine, except in the co-owned and client workspaces, where
  a few come from collaborators.
- **Counting unit.** Counts are records, not distinct choices: a decision that
  is revised and then accepted can appear as more than one record.
  **Rejected or revised** counts decision records with that stored
  disposition. Counts measure recorded activity, not output or quality.
```{include} _evidence_methods.md
```

The aggregates are published as
[evidence.json](/static/evidence/evidence.json). The code that computes them
reads my local TRACE store read-only and is part of this site's repository.
:::
