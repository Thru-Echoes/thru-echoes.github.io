"""Pure aggregation of a TRACE store snapshot into a public report and private diagnostics.

The allowlist is the private release map (registry key -> ProjectDisplay);
public output identifies projects only by `ProjectDisplay.slug`.

Scope rule (each unique session lands in exactly one bucket, in this order):
  identity_conflict  metadata.project_key and metadata.project resolve to different keys
  unresolved         no registry key (an unknown explicit project_key never falls back)
  other              resolved to a key outside the allowlist
  meeting            a MEETING_TAGS tag, or a recording actor (whisper-1, pyannote)
  recent             any activity at or after the cutoff (00:00 UTC the day before as_of)
  included           everything else

Exports:
    MEETING_TAGS, RECORDING_ACTORS
    get_cutoff(as_of) -> datetime
    get_identity(meta, alias_map) -> tuple[str | None, bool]
    is_meeting(session) -> bool
    get_last_activity(session) -> datetime | None
    get_bucket(session, alias_map, allowlist, cutoff) -> tuple[Bucket, str | None]
    get_project_stats(key, display, sessions) -> ProjectStats
    get_weekly(by_key, keys, as_of) -> list[WeekRow]
    get_report(snapshot, alias_map, as_of, excerpts, allowlist)
        -> tuple[EvidenceReport, Diagnostics]

No side effects: every function here is pure.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal

from .models import (
    ACTOR_TYPES,
    DISPOSITIONS,
    EVENT_TYPES,
    PARTIES,
    ActorType,
    Coverage,
    Diagnostics,
    Disposition,
    EventType,
    EvidenceReport,
    Excerpt,
    PairKey,
    ProjectDisplay,
    ProjectStats,
    SessionMeta,
    SessionRecord,
    Snapshot,
    WeekRow,
)

MEETING_TAGS: frozenset[str] = frozenset({"meeting", "transcription", "rehome", "duplicate"})
"""Tags of meeting recordings and of the recorder's own bookkeeping sessions
(re-homing or duplicating a recording between projects)."""
RECORDING_ACTORS: frozenset[str] = frozenset({"whisper-1", "pyannote"})

Bucket = Literal["identity_conflict", "unresolved", "other", "meeting", "recent", "included"]


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def get_cutoff(as_of: datetime) -> datetime:
    """00:00 UTC on the day before the as_of date.

    A session with any activity at or after the cutoff may still be in
    progress, so it waits for the next snapshot. The one-day margin keeps a
    session that is live at generation time (last write minutes before
    midnight) from being counted while it is still growing.
    """
    return datetime.combine(as_of.astimezone(UTC).date() - timedelta(days=1), time(0), tzinfo=UTC)


def get_identity(meta: SessionMeta | None, alias_map: Mapping[str, str]) -> tuple[str | None, bool]:
    """Return (canonical key or None, identity_conflict).

    An explicit `project_key` is authoritative but must itself resolve in the
    registry; it never falls back to the label. A label that resolves to a
    different key than the explicit key is a conflict.
    """
    if meta is None:
        return None, False
    by_label = alias_map.get(_norm(meta.project)) if meta.project else None
    if meta.project_key:
        by_key = alias_map.get(_norm(meta.project_key))
        if by_key and by_label and by_key != by_label:
            return None, True
        return by_key, False
    return by_label, False


def is_meeting(session: SessionRecord) -> bool:
    """True for meeting recordings: a meeting tag or any recording-actor event."""
    tags = (session.metadata.tags if session.metadata else None) or []
    if any(_norm(str(t)) in MEETING_TAGS for t in tags):
        return True
    return any(_norm(e.actor.id if e.actor else None) in RECORDING_ACTORS for e in session.events)


def get_last_activity(session: SessionRecord) -> datetime | None:
    """Latest of created, ended, and every event timestamp."""
    stamps = [t for t in (session.created, session.ended) if t]
    stamps += [e.timestamp for e in session.events if e.timestamp]
    return max(stamps) if stamps else None


def get_bucket(
    session: SessionRecord, alias_map: Mapping[str, str], allowlist: Mapping[str, ProjectDisplay], cutoff: datetime
) -> tuple[Bucket, str | None]:
    """Place one unique session into exactly one scope bucket (see module docstring)."""
    key, conflict = get_identity(session.metadata, alias_map)
    if conflict:
        return "identity_conflict", None
    if key is None:
        return "unresolved", None
    if key not in allowlist:
        return "other", key
    if is_meeting(session):
        return "meeting", key
    last = get_last_activity(session)
    if last is None or last >= cutoff:
        return "recent", key
    return "included", key


def _event_type(v: str | None) -> EventType:
    return v if v in EVENT_TYPES else "other"  # type: ignore[return-value]


def _disposition(v: str | None) -> Disposition:
    return v if v in DISPOSITIONS else "unknown"  # type: ignore[return-value]


def _actor(v: str | None) -> ActorType:
    return v if v in ACTOR_TYPES and v != "not_recorded" else "not_recorded"  # type: ignore[return-value]


def _party(v: str | None) -> str:
    return v if v is not None and v in PARTIES else "unknown"


_VERSION_RE = re.compile(r"^\d{1,2}\.\d{1,2}\.\d{1,3}$")


def _version(v: str | None) -> str:
    """Closed format-version vocabulary: semantic version strings only."""
    return v if v is not None and _VERSION_RE.match(v) else "unknown"


def _iso_week(d: datetime | date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def get_project_stats(display: ProjectDisplay, sessions: list[SessionRecord]) -> ProjectStats:
    """Count sessions and events for one project (or the 'all' totals row)."""
    by_type: Counter[EventType] = Counter()
    disposition: Counter[Disposition] = Counter()
    proposed: Counter[ActorType] = Counter()
    resolved: Counter[ActorType] = Counter()
    pairs: Counter[PairKey] = Counter()
    corrections = discoveries = 0
    for s in sessions:
        for e in s.events:
            etype = _event_type(e.type)
            by_type[etype] += 1
            if etype == "decision":
                d = e.decision
                disposition[_disposition(d.disposition if d else None)] += 1
                proposed[_actor(d.proposed_by.type if d and d.proposed_by else None)] += 1
                resolved[_actor(d.resolved_by.type if d and d.resolved_by else None)] += 1
            elif etype == "contribution":
                c = e.contribution
                pair = f"{_party(c.direction if c else None)}→{_party(c.execution if c else None)}"
                pairs[pair] += 1  # type: ignore[index]
            elif etype == "annotation":
                cat = e.annotation.category if e.annotation else None
                corrections += cat == "correction"
                discoveries += cat == "discovery"
    created = [s.created for s in sessions if s.created]
    return ProjectStats(
        key=display.slug,
        name=display.name,
        url=display.url,
        sessions=len(sessions),
        open_sessions=sum(1 for s in sessions if s.status != "completed"),
        first=min(created).date() if created else None,
        last=max(created).date() if created else None,
        events_by_type=dict(sorted(by_type.items())),
        decisions=by_type["decision"],
        decisions_by_disposition=dict(sorted(disposition.items())),
        proposed_by=dict(sorted(proposed.items())),
        resolved_by=dict(sorted(resolved.items())),
        rejected_or_revised=disposition["rejected"] + disposition["revised"],
        contributions=by_type["contribution"],
        contributions_by_pair=dict(sorted(pairs.items())),
        corrections=corrections,
        discoveries=discoveries,
    )


def get_weekly(by_key: Mapping[str, list[SessionRecord]], keys: list[str], slugs: Mapping[str, str], as_of: datetime) -> list[WeekRow]:
    """Session starts per ISO week per project slug, zero-filled from the first week to as_of's week."""
    created = [s.created for k in keys for s in by_key.get(k, []) if s.created]
    if not created:
        return []
    counts: dict[str, Counter[str]] = {}
    for k in keys:
        for s in by_key.get(k, []):
            if s.created:
                counts.setdefault(_iso_week(s.created), Counter())[k] += 1
    start = min(created).date()
    cursor = start - timedelta(days=start.weekday())
    end_monday = as_of.date() - timedelta(days=as_of.date().weekday())
    rows: list[WeekRow] = []
    while cursor <= end_monday:
        c = counts.get(_iso_week(cursor), Counter())
        rows.append(WeekRow(week=_iso_week(cursor), counts={slugs[k]: c[k] for k in keys}))
        cursor += timedelta(days=7)
    return rows


def get_report(
    snapshot: Snapshot,
    alias_map: Mapping[str, str],
    as_of: datetime,
    excerpts: list[Excerpt],
    allowlist: Mapping[str, ProjectDisplay],
) -> tuple[EvidenceReport, Diagnostics]:
    """Build the public report and the private diagnostics from one snapshot. Pure."""
    as_of = as_of.astimezone(UTC)
    cutoff = get_cutoff(as_of)
    by_key: dict[str, list[SessionRecord]] = {k: [] for k in allowlist}
    buckets: Counter[Bucket] = Counter()
    for s in snapshot.sessions:
        bucket, key = get_bucket(s, alias_map, allowlist, cutoff)
        buckets[bucket] += 1
        if bucket == "included" and key is not None:
            by_key[key].append(s)
    keys = [k for k in allowlist if by_key[k]]
    included = [s for k in keys for s in by_key[k]]
    inc_created = [s.created for s in included if s.created]
    all_created = [s.created for s in snapshot.sessions if s.created]
    report = EvidenceReport(
        as_of=as_of,
        coverage=Coverage(
            cutoff=cutoff,
            sessions=len(included),
            max_created=max(inc_created) if inc_created else None,
            format_versions=dict(sorted(Counter(_version(s.trace_version) for s in included).items())),
            sessions_resolved_by_alias=sum(1 for s in included if not (s.metadata and s.metadata.project_key)),
        ),
        projects=[get_project_stats(allowlist[k], by_key[k]) for k in keys],
        totals=get_project_stats(ProjectDisplay(slug="all", name="All projects"), included),
        weekly=get_weekly(by_key, keys, {k: allowlist[k].slug for k in keys}, as_of),
        excerpts=excerpts,
    )
    diagnostics = Diagnostics(
        as_of=as_of,
        cutoff=cutoff,
        files_read=snapshot.files_read,
        malformed=snapshot.malformed,
        duplicate_copies=snapshot.duplicate_copies,
        conflicting_ids=snapshot.conflicting_ids,
        conflicting_files=snapshot.conflicting_files,
        unresolved=buckets["unresolved"],
        identity_conflicts=buckets["identity_conflict"],
        other_projects=buckets["other"],
        meetings=buckets["meeting"],
        recent=buckets["recent"],
        included=buckets["included"],
        store_max_created=max(all_created) if all_created else None,
        digests={s.id: snapshot.digests[s.id] for s in sorted(included, key=lambda x: x.id)},
    )
    return report, diagnostics
