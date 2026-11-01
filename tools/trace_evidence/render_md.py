"""Render the generated MyST include fragments from an EvidenceReport.

The page source never types a number; it includes these three fragments.
Copy rules enforced here: no em or en dashes, no double hyphens.

Exports:
    get_claim_md(report) -> str          (_evidence_claim.md)
    get_table_md(report) -> str          (_evidence_table.md)
    get_methods_md(report) -> str        (_evidence_methods.md)
    get_contrib_table_md(report) -> str  (_evidence_contributions.md)

No side effects.
"""

from __future__ import annotations

import re
from datetime import date

from .charts import CONTRIB_CATEGORIES, get_contrib_category
from .models import EvidenceReport, ProjectStats

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+!|<>])")


def _esc(text: str) -> str:
    """Escape Markdown/MyST-significant characters in display text."""
    return _MD_SPECIAL.sub(r"\\\1", text)


def _n(x: int) -> str:
    return f"{x:,}"


def _d(x: date | None) -> str:
    return x.strftime("%b %-d, %Y") if x else "n/a"


def _span(a: date | None, b: date | None) -> str:
    """Compact date range; the year is written once when both dates share it."""
    if a is None or b is None:
        return "n/a"
    if a.year == b.year:
        return f"{a.strftime('%b %-d')} to {b.strftime('%b %-d')}, {b.year}"
    return f"{_d(a)} to {_d(b)}"


def _name(p: ProjectStats) -> str:
    return f"[{_esc(p.name)}]({p.url})" if p.url else _esc(p.name)


def get_claim_md(report: EvidenceReport) -> str:
    """One-paragraph claim with the snapshot date. Numbers come from the report."""
    t = report.totals
    first = t.first.strftime("%B %Y") if t.first else "n/a"
    return (
        f"Since {first}, TRACE has recorded my AI-assisted engineering as structured, "
        f"attributable records. In a snapshot taken {_d(report.as_of.date())}, the records from "
        f"{len(report.projects)} project workspaces hold **{_n(t.sessions)} sessions**, "
        f"**{_n(t.decisions)} decision records** (who proposed, who resolved), "
        f"**{_n(t.contributions)} contribution records** (who had the idea, who did the work), "
        f"and **{_n(t.corrections)} annotations tagged correction**. Of the "
        f"{_n(t.agent_proposals)} decision records the agent proposed, "
        f"**{_n(t.agent_proposals_rejected_or_revised)}** were rejected or revised by a human.\n"
    )


def get_table_md(report: EvidenceReport) -> str:
    """Summary table, one row per project plus a totals row."""
    head = (
        "| Project | Sessions | Session starts | Decision records | Rejected or revised "
        "| Contribution records | Tagged correction |\n"
        "|:--|--:|:--|--:|--:|--:|--:|\n"
    )

    def row(p: ProjectStats, bold: bool = False) -> str:
        b = "**" if bold else ""
        cells = [
            f"{b}{_name(p)}{b}",
            f"{b}{_n(p.sessions)}{b}",
            _span(p.first, p.last),
            f"{b}{_n(p.decisions)}{b}",
            f"{b}{_n(p.rejected_or_revised)}{b}",
            f"{b}{_n(p.contributions)}{b}",
            f"{b}{_n(p.corrections)}{b}",
        ]
        return "| " + " | ".join(cells) + " |\n"

    return head + "".join(row(p) for p in report.projects) + row(report.totals, bold=True)


def get_methods_md(report: EvidenceReport) -> str:
    """Methods facts that depend on the data: snapshot, coverage, open sessions."""
    c = report.coverage
    t = report.totals
    versions = ", ".join(f"{v} ({_n(n)})" for v, n in c.format_versions.items())
    return (
        f"- **Snapshot.** Generated {report.as_of.strftime('%Y-%m-%d %H:%M')} UTC. A session whose latest "
        f"recorded timestamp is on or after {c.cutoff.strftime('%Y-%m-%d')} (UTC) may still be in progress "
        f"and is left for the next snapshot. A later snapshot can restate earlier weeks.\n"
        f"- **Coverage.** {_n(c.sessions)} sessions across TRACE format versions {versions}. "
        f"{_n(c.sessions_resolved_by_alias)} sessions lack a canonical project key and were matched to "
        f"their project through the TRACE alias registry.\n"
        f"- **Status.** {_n(t.open_sessions)} counted sessions are not marked completed; their events are "
        f"counted as recorded.\n"
        f"- **Resolution.** {_n(t.decisions_by_disposition.get('proposed', 0))} of {_n(t.decisions)} decision "
        f"records still have the stored disposition proposed, and {_n(t.resolved_by.get('not_recorded', 0))} "
        f"have no recorded resolver. They are counted, not dropped.\n"
    )


def get_contrib_table_md(report: EvidenceReport) -> str:
    """Contribution records per project by direction and execution (the chart's numbers)."""
    cats = [c for c in CONTRIB_CATEGORIES if any(
        get_contrib_category(k) == c and v for k, v in report.totals.contributions_by_pair.items()
    )]
    head = "| Project | " + " | ".join(cats) + " | Total |\n" + "|:--|" + "--:|" * (len(cats) + 1) + "\n"

    def row(p: ProjectStats, bold: bool = False) -> str:
        b = "**" if bold else ""
        counts = {c: 0 for c in cats}
        for k, v in p.contributions_by_pair.items():
            counts[get_contrib_category(k)] = counts.get(get_contrib_category(k), 0) + v
        cells = [f"{b}{_esc(p.name)}{b}", *(_n(counts[c]) for c in cats), f"{b}{_n(p.contributions)}{b}"]
        return "| " + " | ".join(cells) + " |\n"

    return head + "".join(row(p) for p in report.projects) + row(report.totals, bold=True)
