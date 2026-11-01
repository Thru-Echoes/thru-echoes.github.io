"""Excerpt gate: only explicitly approved text for in-scope events is published.

Approvals file (YAML, kept outside the repository):

    excerpts:
      - event_id: evt_012
        session_id: trace_20260401_abc123
        title: Short heading
        text: |
          Verbatim approved text.
        approved: true
        approved_on: 2026-11-02

Errors carry a code and the entry index only, never ids or text, so a failing
run cannot echo private content.

Exports:
    ExcerptError
    get_excerpts(path, snapshot, alias_map, allowlist, cutoff) -> list[Excerpt]

Side effects: reads the approvals file when given.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path

import yaml

from .aggregate import get_bucket
from .models import Excerpt, ProjectDisplay, Snapshot


class ExcerptError(ValueError):
    """An excerpt entry is unapproved, malformed, or outside the published scope."""

    def __init__(self, code: str, index: int) -> None:
        super().__init__(f"excerpt entry {index}: {code}")
        self.code = code
        self.index = index


def get_excerpts(
    path: Path | None,
    snapshot: Snapshot,
    alias_map: Mapping[str, str],
    allowlist: Mapping[str, ProjectDisplay],
    cutoff: datetime,
) -> list[Excerpt]:
    """Validate the approvals file and return publishable excerpts.

    Returns [] when `path` is None or does not exist. Raises ExcerptError for
    any entry that is not `approved: true` with an `approved_on` date, lacks
    text, or names an event not inside an included (allowlisted, non-meeting,
    stable) session.
    """
    if path is None or not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    entries = data.get("excerpts") or []
    sessions = {s.id: s for s in snapshot.sessions}
    out: list[Excerpt] = []
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            raise ExcerptError("not-a-mapping", i)
        if e.get("approved") is not True:
            raise ExcerptError("not-approved", i)
        if not isinstance(e.get("approved_on"), date):
            raise ExcerptError("missing-approved-on", i)
        if not str(e.get("text") or "").strip() or not str(e.get("title") or "").strip():
            raise ExcerptError("missing-text-or-title", i)
        s = sessions.get(str(e.get("session_id")))
        if s is None:
            raise ExcerptError("session-not-found", i)
        bucket, key = get_bucket(s, alias_map, allowlist, cutoff)
        if bucket != "included" or key is None:
            raise ExcerptError("session-out-of-scope", i)
        if str(e.get("event_id")) not in {ev.id for ev in s.events}:
            raise ExcerptError("event-not-in-session", i)
        out.append(
            Excerpt(
                event_id=str(e["event_id"]),
                session_id=s.id,
                project=allowlist[key].slug,
                title=str(e["title"]).strip(),
                text=str(e["text"]).strip(),
                approved_on=e["approved_on"],
            )
        )
    return out
