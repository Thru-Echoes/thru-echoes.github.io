"""Render the generated MyST include fragments from an EvidenceReport.

The page sources never type a number; they include these fragments.
Copy rules enforced here: no em or en dashes, no double hyphens.

Exports:
    get_claim_md(report) -> str          (_evidence_claim.md)
    get_table_md(report) -> str          (_evidence_table.md)
    get_methods_md(report) -> str        (_evidence_methods.md)
    get_contrib_table_md(report) -> str  (_evidence_contributions.md)
    get_excerpts_md(report) -> str       (_evidence_excerpts.md, text version of the chains)
    get_graph_md(report) -> str          (_evidence_graph.md, interactive chain graph)
    get_featured_md(report) -> str       (_evidence_featured.md, landing-page chain)
    get_node_label(node) -> str

No side effects.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime

from .charts import CONTRIB_CATEGORIES, get_contrib_category
from .models import ChainNode, EvidenceReport, Excerpt, ProjectStats

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


_ACTOR = {"ai": "agent", "human": "human", "system": "system", "not_recorded": "unrecorded actor"}
_PARTY = {"ai": "AI", "human": "human", "collaborative": "shared", "unknown": "unrecorded"}
_REL = {"revises": "revises", "corrects": "corrects", "builds_on": "builds on"}


def get_node_label(n: ChainNode) -> str:
    """Short role label for one chain node, from store metadata only. Pure."""
    if n.kind == "decision":
        who = _ACTOR[n.proposed_by or "not_recorded"]
        if n.disposition in ("accepted", "rejected", "revised"):
            return f"Decision: {who} proposal, {n.disposition} by {_ACTOR[n.resolved_by or 'not_recorded']}"
        return f"Decision: {who} proposal, not yet resolved"
    if n.kind == "contribution":
        return f"Contribution: {_PARTY[n.direction or 'unknown']} idea, {_PARTY[n.execution or 'unknown']} built"
    return {"correction": "Correction", "annotation": "Annotation", "external": "External reference"}[n.kind]


def _when(x: Excerpt) -> str:
    return datetime.strptime(x.month, "%Y-%m").strftime("%B %Y") if x.month != "unknown" else "date not recorded"


def get_excerpts_md(report: EvidenceReport) -> str:
    """Text version of every chain: heading, source line, one quote per record, then its links."""
    if not report.excerpts:
        return "No decision chains are published in this snapshot.\n"
    out: list[str] = []
    for x in report.excerpts:
        out.append(f"### {_esc(x.title)}\n\n*{_esc(x.project_name)}, {_when(x)}*\n\n")
        for n in x.nodes:
            out.append(f"> **{_esc(n.id)}, {_esc(get_node_label(n))}**\n>\n")
            body = n.url and f"[{_esc(n.headline)}]({n.url})" or None
            parts = [body] if body else [ln for ln in (n.text or n.headline).splitlines() if ln.strip()]
            for i, line in enumerate(parts):
                label, sep, rest = line.partition(": ")
                labelled = bool(n.text) and sep and len(label) <= 60
                text = line if body else (f"**{_esc(label)}:** {_esc(rest)}" if labelled else _esc(line))
                out.append(f"> {text}\n")
                if i < len(parts) - 1:
                    out.append(">\n")
            out.append("\n")
            if n.resolution:
                who = _ACTOR[n.resolved_by or "not_recorded"].capitalize()
                body = "\n>\n".join(f"> {_esc(ln)}" for ln in n.resolution.splitlines() if ln.strip())
                out.append(f"> **{_esc(n.id)}, {who} {n.disposition}**\n>\n{body}\n\n")
        if x.edges:
            links = "; ".join(f"{_esc(e.source)} {_REL[e.relation]} {_esc(e.target)}" for e in x.edges)
            out.append(f"Links stored in these records: {links}.\n\n")
    return "".join(out)


def _graph_block(model: dict[str, object], css_class: str) -> str:
    body = json.dumps(model, ensure_ascii=True, separators=(",", ":"))
    return f":::{{anywidget}} /projects/trace/chains-graph.mjs\n:css: /projects/trace/chains-graph.css\n:class: {css_class}\n{body}\n:::\n"


def _chain_model(report: EvidenceReport, chains: list[Excerpt]) -> list[dict[str, object]]:
    order = {p.key: i for i, p in enumerate(report.projects)}
    return [
        {
            "slug": x.slug, "title": x.title, "project": x.project, "project_name": x.project_name,
            "color": order.get(x.project, 0), "when": _when(x), "key": x.key_event_id,
            "unshown": x.unshown_links,
            "nodes": [{**n.model_dump(exclude_none=True), "label": get_node_label(n)} for n in x.nodes],
            "edges": [e.model_dump() for e in x.edges],
        }
        for x in chains
    ]  # fmt: skip


def get_featured_md(report: EvidenceReport) -> str:
    """The featured chain for the landing page: caption, compact graph, and a link to all chains.

    Returns '' when no chain is featured, so the landing page then shows nothing.
    """
    featured = [x for x in report.excerpts if x.featured]
    if not featured:
        return ""
    model = {"compact": True, "projects": [], "chains": _chain_model(report, featured)}
    n = len(report.excerpts)
    caption = (
        "**One decision chain from my TRACE records.** Boxes are records and arrows\n"
        "are the links stored in them. Select a box to read the record.\n\n"
    )
    more = f"See all {n} decision chains →" if n > 1 else "See the decision chain →"
    return caption + _graph_block(model, "trace-featured") + f"\n[{more}](/trace-evidence#chain={featured[0].slug})\n"


def get_graph_md(report: EvidenceReport) -> str:
    """The interactive chain graph as a MyST anywidget block whose body is the chain data."""
    model = {
        "projects": [{"slug": p.key, "name": p.name, "color": i} for i, p in enumerate(report.projects)],
        "chains": _chain_model(report, report.excerpts),
    }
    return _graph_block(model, "col-page-right")
