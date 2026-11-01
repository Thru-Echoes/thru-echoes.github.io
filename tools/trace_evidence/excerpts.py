"""Excerpt gate: only approved text for in-scope events is published, as linked chains.

Approvals file (YAML, kept outside the repository):

    excerpts:
      - session_id: trace_20260401_abc123
        title: Short heading
        key_event_id: evt_013          # the node a reader sees first
        nodes:
          - event_id: evt_012
            headline: Approved short text for the graph node.
          - event_id: evt_013
            headline: Approved short text.
            text: |                    # optional longer quote, one labelled part per line
              Correction: verbatim approved text.
        external:                      # optional; only refs a shown record actually stores
          - ref: external:github.com/org/repo/pull/1
            label: Approved label
        approved: true
        approved_on: 2026-11-02
        approved_by: owner

The approvals file supplies only text. Node metadata (kind, who proposed,
disposition, who resolved, direction, execution) and every edge come from
the records themselves: a decision's `revises_event_id`, a correction's
`corrects_event_ids`, a contribution's `related_decision_ids`. A link whose
target is not shown is counted in `unshown_links`, never drawn.

Errors carry a code and the entry index only, never ids or text, so a failing
run cannot echo private content.

Exports:
    ExcerptError
    get_links(event) -> list[tuple[Relation, str]]
    get_slug(title) -> str
    get_excerpts(path, snapshot, alias_map, allowlist, cutoff) -> list[Excerpt]

Side effects: reads the approvals file when given.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path

import yaml

from .aggregate import get_bucket
from .models import (
    ACTOR_TYPES,
    DISPOSITIONS,
    PARTIES,
    ChainEdge,
    ChainNode,
    EventRecord,
    Excerpt,
    ProjectDisplay,
    Relation,
    Snapshot,
)

_EXTERNAL = re.compile(r"^external:(?:https://)?([a-z0-9.-]+\.[a-z]{2,}/[A-Za-z0-9._~/#-]+)$")


class ExcerptError(ValueError):
    """An excerpt entry is unapproved, malformed, or outside the published scope."""

    def __init__(self, code: str, index: int) -> None:
        super().__init__(f"excerpt entry {index}: {code}")
        self.code = code
        self.index = index


def _ids(v: object) -> list[str]:
    """Normalize a stored link field (str, list, or junk) to a list of strings."""
    if isinstance(v, str):
        return [v] if v.strip() else []
    if isinstance(v, list):
        return [x for x in v if isinstance(x, str) and x.strip()]
    return []


def get_links(ev: EventRecord) -> list[tuple[Relation, str]]:
    """Outgoing links stored in one record, in stored order. Pure."""
    if ev.type == "decision" and ev.decision:
        return [("revises", t) for t in _ids(ev.decision.revises_event_id)]
    if ev.type == "annotation" and ev.annotation:
        return [("corrects", t) for t in _ids(ev.annotation.corrects_event_ids)]
    if ev.type == "contribution" and ev.contribution:
        return [("builds_on", t) for t in _ids(ev.contribution.related_decision_ids)]
    return []


def get_slug(title: str) -> str:
    """Lowercase hyphenated anchor from a title, at most 60 characters. Pure."""
    s = re.sub(r"[^a-z0-9]+", "-", re.sub(r"['\u2019]", "", title.lower())).strip("-")
    return s[:60].rstrip("-") or "chain"


def _node(ev: EventRecord, headline: str, text: str | None) -> ChainNode | None:
    """Store metadata plus approved text; None for record types that cannot be a node."""
    if ev.type == "decision":
        d = ev.decision
        disp = d.disposition if d and d.disposition in DISPOSITIONS else "unknown"
        pb = d.proposed_by.type if d and d.proposed_by else None
        rb = d.resolved_by.type if d and d.resolved_by else None
        return ChainNode(
            id=str(ev.id), kind="decision", headline=headline, text=text, disposition=disp,  # type: ignore[arg-type]
            proposed_by=pb if pb in ACTOR_TYPES else "not_recorded",  # type: ignore[arg-type]
            resolved_by=rb if rb in ACTOR_TYPES else "not_recorded",  # type: ignore[arg-type]
        )  # fmt: skip
    if ev.type == "annotation":
        kind = "correction" if ev.annotation and ev.annotation.category == "correction" else "annotation"
        return ChainNode(id=str(ev.id), kind=kind, headline=headline, text=text)
    if ev.type == "contribution":
        c = ev.contribution
        dr = c.direction if c and c.direction in PARTIES else "unknown"
        ex = c.execution if c and c.execution in PARTIES else "unknown"
        return ChainNode(id=str(ev.id), kind="contribution", headline=headline, text=text, direction=dr, execution=ex)  # type: ignore[arg-type]
    return None


def _clean(v: object) -> str:
    return str(v or "").strip()


def get_excerpts(
    path: Path | None,
    snapshot: Snapshot,
    alias_map: Mapping[str, str],
    allowlist: Mapping[str, ProjectDisplay],
    cutoff: datetime,
) -> list[Excerpt]:
    """Validate the approvals file and return publishable chains.

    Returns [] when `path` is None or does not exist. Raises ExcerptError for
    any entry that is not `approved: true` with an `approved_on` date and an
    `approved_by`, lacks a title or nodes, names an event outside an included
    (allowlisted, non-meeting, stable) session, repeats a node, or lists an
    external reference that no shown record stores.
    """
    if path is None or not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    entries = data.get("excerpts") or []
    sessions = {s.id: s for s in snapshot.sessions}
    out: list[Excerpt] = []
    slugs: set[str] = set()
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            raise ExcerptError("not-a-mapping", i)
        if e.get("approved") is not True:
            raise ExcerptError("not-approved", i)
        if not isinstance(e.get("approved_on"), date):
            raise ExcerptError("missing-approved-on", i)
        if not _clean(e.get("approved_by")):
            raise ExcerptError("missing-approved-by", i)
        title = _clean(e.get("title"))
        raw_nodes = e.get("nodes")
        if not title:
            raise ExcerptError("missing-title", i)
        if not isinstance(raw_nodes, list) or not raw_nodes:
            raise ExcerptError("missing-nodes", i)
        s = sessions.get(str(e.get("session_id")))
        if s is None:
            raise ExcerptError("session-not-found", i)
        bucket, key = get_bucket(s, alias_map, allowlist, cutoff)
        if bucket != "included" or key is None:
            raise ExcerptError("session-out-of-scope", i)
        events = {str(ev.id): ev for ev in s.events if ev.id}

        nodes: list[ChainNode] = []
        for rn in raw_nodes:
            if not isinstance(rn, dict):
                raise ExcerptError("node-not-a-mapping", i)
            eid, headline = str(rn.get("event_id")), _clean(rn.get("headline"))
            if eid not in events:
                raise ExcerptError("event-not-in-session", i)
            if not headline:
                raise ExcerptError("missing-headline", i)
            if any(n.id == eid for n in nodes):
                raise ExcerptError("duplicate-node", i)
            node = _node(events[eid], headline, _clean(rn.get("text")) or None)
            if node is None:
                raise ExcerptError("unsupported-node-type", i)
            nodes.append(node)
        shown = {n.id for n in nodes}
        if str(e.get("key_event_id")) not in shown:
            raise ExcerptError("key-event-not-a-node", i)

        links = {n.id: get_links(events[n.id]) for n in nodes}
        stored_refs = {t for ls in links.values() for _, t in ls}
        ext_ids: dict[str, str] = {}
        for j, rx in enumerate(e.get("external") or []):
            ref = _clean(rx.get("ref")) if isinstance(rx, dict) else ""
            label = _clean(rx.get("label")) if isinstance(rx, dict) else ""
            m = _EXTERNAL.match(ref)
            if not m or not label:
                raise ExcerptError("bad-external", i)
            if ref not in stored_refs:
                raise ExcerptError("external-not-in-records", i)
            ext_ids[ref] = f"ext-{j + 1}"
            nodes.append(ChainNode(id=ext_ids[ref], kind="external", headline=label, url=f"https://{m.group(1)}"))

        edges: list[ChainEdge] = []
        unshown = 0
        for src, ls in links.items():
            for rel, tgt in ls:
                target = tgt if tgt in shown else ext_ids.get(tgt)
                if target is None:
                    unshown += 1
                else:
                    edges.append(ChainEdge(source=src, target=target, relation=rel))

        slug = get_slug(title)
        if slug in slugs:
            raise ExcerptError("duplicate-title", i)
        slugs.add(slug)
        out.append(
            Excerpt(
                slug=slug,
                key_event_id=str(e["key_event_id"]),
                session_id=s.id,
                project=allowlist[key].slug,
                project_name=allowlist[key].name,
                month=s.created.strftime("%Y-%m") if s.created else "unknown",
                title=title,
                nodes=nodes,
                edges=edges,
                unshown_links=unshown,
                approved_on=e["approved_on"],
                approved_by=_clean(e["approved_by"]),
            )
        )
    return out
