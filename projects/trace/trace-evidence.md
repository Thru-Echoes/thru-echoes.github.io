---
title: "TRACE evidence"
short_title: TRACE evidence
description: >-
  Aggregate, attributable records of my AI-assisted engineering, captured
  with TRACE, the provenance MCP server I built.
---

# TRACE evidence

```{include} _evidence_claim.md
```

## What TRACE records

[TRACE](https://github.com/Thru-Echoes/TRACE) is an open-source MCP server I
built for decision provenance in AI-assisted work. While I work with coding
agents, it writes a structured record of each session: decisions with who
proposed them, who resolved them, and why; contributions with who had the idea
and who did the work; and annotations, including corrections. The format is
defined in the
[specification](https://github.com/Thru-Echoes/TRACE/blob/main/docs/specification.md).

I build TRACE and I run it on my own work. This page is a snapshot of those
records from five project workspaces, published by hand.

## Summary

```{include} _evidence_table.md
```

**Sessions** counts recorded work sessions; **session starts** gives the first
and last start date. **Rejected or revised** counts decision records where the
proposal was turned down or changed before acceptance.

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

## Who had the idea, who did the work

Each contribution record names who had the idea (**direction**) and who
carried it out (**execution**). In most of my records, I set the direction and
the agent wrote the code.

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

## What one record looks like

The two events below are a **synthetic example** with made-up content, shown
only to illustrate the fields that answer "who proposed, who decided, who
built." They are not from my records.

```json
{
  "type": "decision",
  "actor": {"type": "ai", "id": "assistant"},
  "decision": {
    "description": "Cache parsed config files in memory",
    "rationale": "Config is re-read on every request",
    "proposed_by": {"type": "ai"},
    "disposition": "revised",
    "resolved_by": {"type": "human"},
    "revision_note": "Cache, but invalidate on file change"
  }
}
{
  "type": "contribution",
  "contribution": {
    "description": "Config cache with file-change invalidation",
    "artifact": "app/config_cache.py",
    "direction": "collaborative",
    "execution": "ai",
    "related_decision_ids": ["evt_001"]
  }
}
```

## Methods and limits

- **Self-logged.** The agent and I write these records during the work. Each
  entry is attributable (it names who proposed, resolved, or did the work),
  but the records are not independently checked.
- **Scope.** Five project workspaces. Other projects in my TRACE store and all
  meeting recordings are excluded and not described here.
- **Human entries.** Nearly all human entries are mine; fewer than 1% come from
  collaborators on the co-owned and client projects.
- **Counting unit.** Counts are records, not distinct choices: a decision that
  is revised and then accepted can appear as more than one record. They measure
  recorded activity, not output, productivity, or quality.
```{include} _evidence_methods.md
```

The aggregates behind this page are published as
[evidence.json](/static/evidence/evidence.json). The code that computes them
reads my local TRACE store read-only and is part of this site's repository.
For the engineering itself, see TRACE's
[test suite](https://github.com/Thru-Echoes/TRACE/tree/main/tests) and
[releases](https://github.com/Thru-Echoes/TRACE/releases).
