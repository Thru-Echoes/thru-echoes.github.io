"""Pydantic models for the TRACE evidence pipeline.

Input models parse the subset of a TRACE session file (format v0.3 to v0.5)
that the pipeline reads; fields older formats may lack are optional and
unknown fields are ignored.

Output models are split by audience:
  * `EvidenceReport` is PUBLIC (`static/evidence/evidence.json`). Every
    categorical key is a closed Literal vocabulary, so no free-text string
    from the store can reach it; it describes in-scope sessions only.
  * `Diagnostics` is PRIVATE (written outside the repository). It holds the
    processing waterfall over the whole store, including excluded sessions.

Exports:
    Input:  Actor, DecisionRec, ContributionRec, AnnotationRec, EventRecord,
            SessionMeta, SessionRecord, Snapshot
    Vocab:  EventType, Disposition, ActorType, PairKey, EVENT_TYPES,
            DISPOSITIONS, ACTOR_TYPES, PARTIES, PAIR_KEYS
    Output: ProjectDisplay, ProjectStats, WeekRow, Coverage, Excerpt,
            EvidenceReport, Diagnostics
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ── closed public vocabularies ─────────────────────────────────────────
EventType = Literal["decision", "contribution", "annotation", "tool_call", "state_change", "other"]
Disposition = Literal["accepted", "rejected", "revised", "proposed", "unknown"]
ActorType = Literal["human", "ai", "system", "not_recorded"]
Party = Literal["human", "ai", "collaborative", "unknown"]
PairKey = Literal[
    "human→ai", "human→collaborative", "human→human", "human→unknown",
    "collaborative→ai", "collaborative→collaborative", "collaborative→human", "collaborative→unknown",
    "ai→ai", "ai→collaborative", "ai→human", "ai→unknown",
    "unknown→ai", "unknown→collaborative", "unknown→human", "unknown→unknown",
]  # fmt: skip

EVENT_TYPES: tuple[str, ...] = get_args(EventType)
DISPOSITIONS: tuple[str, ...] = get_args(Disposition)
ACTOR_TYPES: tuple[str, ...] = get_args(ActorType)
PARTIES: tuple[str, ...] = get_args(Party)
PAIR_KEYS: tuple[str, ...] = get_args(PairKey)


class _In(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


def _as_utc(v: datetime | None) -> datetime | None:
    """Treat naive timestamps as UTC; convert aware ones to UTC."""
    if v is None:
        return None
    return v.replace(tzinfo=UTC) if v.tzinfo is None else v.astimezone(UTC)


class Actor(_In):
    type: str | None = None
    id: str | None = None


class DecisionRec(_In):
    disposition: str | None = None
    proposed_by: Actor | None = None
    resolved_by: Actor | None = None


class ContributionRec(_In):
    direction: str | None = None
    execution: str | None = None


class AnnotationRec(_In):
    category: str | None = None


class EventRecord(_In):
    id: str | None = None
    type: str | None = None
    timestamp: datetime | None = None
    actor: Actor | None = None
    decision: DecisionRec | None = None
    contribution: ContributionRec | None = None
    annotation: AnnotationRec | None = None

    @field_validator("timestamp")
    @classmethod
    def _utc(cls, v: datetime | None) -> datetime | None:
        return _as_utc(v)


class SessionMeta(_In):
    project: str | None = None
    project_key: str | None = None
    tags: list[str] | None = None


class SessionRecord(_In):
    id: str
    created: datetime | None = None
    ended: datetime | None = None
    status: str | None = None
    trace_version: str | None = None
    metadata: SessionMeta | None = None
    events: list[EventRecord] = Field(default_factory=list)

    @field_validator("created", "ended")
    @classmethod
    def _utc(cls, v: datetime | None) -> datetime | None:
        return _as_utc(v)

    @field_validator("events", mode="before")
    @classmethod
    def _events_list(cls, v: object) -> object:
        return [] if v is None else v


class Snapshot(_In):
    """One read of the store: parsed, de-duplicated sessions plus read stats.

    `digests` maps session id -> sha256 of the exact bytes parsed, so a later
    recount can prove it saw the same inputs.
    """

    sessions: list[SessionRecord] = Field(description="De-duplicated parsed sessions.")
    paths: dict[str, str] = Field(description="Session id -> file path it was parsed from.")
    digests: dict[str, str] = Field(description="Session id -> sha256 of the parsed file bytes.")
    files_read: int = Field(description="Number of *.json files read.")
    malformed: int = Field(description="Files that were not a valid session object.")
    duplicate_copies: int = Field(description="Extra byte-identical copies of an already-seen id.")
    conflicting_ids: int = Field(description="Ids with differing copies; all copies quarantined.")
    conflicting_files: int = Field(description="Files belonging to quarantined conflicting ids.")


# ── public output ──────────────────────────────────────────────────────
class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectDisplay(_Out):
    slug: str = Field(pattern=r"^[a-z0-9-]{1,40}$", description="Public id used in evidence.json.")
    name: str = Field(description="Public display name (release-approved).")
    url: str | None = Field(default=None, description="Public link, or None.")


class ProjectStats(_Out):
    key: str = Field(description="Public project slug, or 'all' for the totals row.")
    name: str
    url: str | None = None
    sessions: int
    open_sessions: int = Field(description="Included sessions never marked completed.")
    first: date | None = Field(description="UTC date of the earliest session start.")
    last: date | None = Field(description="UTC date of the latest session start.")
    events_by_type: dict[EventType, int]
    decisions: int = Field(description="Decision records (events of type decision).")
    decisions_by_disposition: dict[Disposition, int]
    proposed_by: dict[ActorType, int]
    resolved_by: dict[ActorType, int] = Field(description="'not_recorded' when no resolver is stored.")
    rejected_or_revised: int
    agent_proposals: int = Field(description="Decision records proposed by an AI actor.")
    agent_proposals_rejected_or_revised: int = Field(
        description="AI-proposed decision records whose stored disposition is rejected or revised by a human resolver."
    )
    contributions: int
    contributions_by_pair: dict[PairKey, int] = Field(description="Keyed 'direction→execution'.")
    corrections: int
    discoveries: int


class WeekRow(_Out):
    week: str = Field(description="ISO week, %G-W%V, of session start.")
    counts: dict[str, int] = Field(description="Session starts per public project slug.")


class Coverage(_Out):
    """What the included population is, without describing excluded sessions."""

    cutoff: datetime = Field(description="Sessions with activity at or after this instant are not included.")
    sessions: int
    max_created: date | None = Field(description="UTC date of the latest included session start.")
    format_versions: dict[str, int] = Field(description="Included sessions per TRACE format version.")
    sessions_resolved_by_alias: int = Field(description="Included sessions lacking metadata.project_key.")


class Excerpt(_Out):
    event_id: str = Field(description="Seed event of the quoted chain.")
    related_event_ids: list[str] = Field(default_factory=list, description="Other quoted events in the same session.")
    session_id: str
    project: str = Field(description="Public slug of the project the event belongs to.")
    project_name: str
    month: str = Field(description="Session start, YYYY-MM.")
    title: str
    text: str = Field(description="Approved text, copied verbatim from the approvals file.")
    approved_on: date
    approved_by: str = Field(description="Who approved publication (the owner, or the owner's delegated panel).")


class EvidenceReport(_Out):
    schema_version: Literal[2] = 2
    as_of: datetime
    coverage: Coverage
    projects: list[ProjectStats]
    totals: ProjectStats
    weekly: list[WeekRow]
    excerpts: list[Excerpt]


# ── private output ─────────────────────────────────────────────────────
class Diagnostics(_Out):
    """Private processing waterfall; never committed. Stages are disjoint.

    files_read = malformed + duplicate_copies + conflicting_files + unique
    unique = identity_conflicts + unresolved + other_projects + meetings + recent + included
    """

    as_of: datetime
    cutoff: datetime
    files_read: int
    malformed: int
    duplicate_copies: int
    conflicting_ids: int
    conflicting_files: int
    unresolved: int
    identity_conflicts: int
    other_projects: int
    meetings: int
    recent: int
    included: int
    duplicate_event_ids: int = Field(description="Repeated event ids within included sessions.")
    store_max_created: datetime | None
    digests: dict[str, str] = Field(description="Included session id -> sha256 of parsed bytes.")
