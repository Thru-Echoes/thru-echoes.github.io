"""Synthetic-store tests for loading, scope buckets, closed vocabularies, and aggregation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tools.trace_evidence.aggregate import get_identity, get_report
from tools.trace_evidence.load import RegistryError, get_alias_map, get_snapshot
from tools.trace_evidence.models import SessionMeta

from .conftest import TEST_ALLOWLIST, event, session_dict

AS_OF = datetime(2026, 4, 10, 15, 0, tzinfo=UTC)
CANARY = "zz-canary-private-string"


def _decision(eid: str, disposition: str, resolved: str | None = "human", proposed: str = "ai") -> dict[str, object]:
    return event(
        eid,
        "decision",
        decision={
            "description": "d",
            "rationale": "r",
            "proposed_by": {"type": proposed, "id": "a", "role": None},
            "disposition": disposition,
            "resolved_by": None if resolved is None else {"type": resolved, "id": "h", "role": None},
            "revision_note": None,
            "revises_event_id": None,
            "suggestion_type": "proactive",
            "tags": [],
        },
    )


def _contrib(eid: str, direction: str | None, execution: str | None) -> dict[str, object]:
    c = {"description": "x", "artifact": "f", "direction": direction, "execution": execution, "related_decision_ids": [], "tags": []}
    return event(eid, "contribution", contribution=c)


def _ann(eid: str, category: str) -> dict[str, object]:
    a = {"category": category, "content": "x", "corrects_event_ids": [], "related_event_ids": [], "tags": []}
    return event(eid, "annotation", annotation=a)


def _run(store, allowlist=TEST_ALLOWLIST, as_of=AS_OF):
    snap = get_snapshot(store)
    return get_report(snap, get_alias_map(store / "projects.json"), as_of, [], allowlist=allowlist)


def _reconciles(snap_files: int, d) -> bool:
    unique = d.identity_conflicts + d.unresolved + d.other_projects + d.meetings + d.recent + d.included
    return snap_files == d.malformed + d.duplicate_copies + d.conflicting_files + unique


# ── identity ──────────────────────────────────────────────────────────
def test_alias_resolves_case_and_whitespace_insensitive(make_store):
    rep, _ = _run(make_store([session_dict("s1", "  COLLAB-A ")]))
    assert [p.key for p in rep.projects] == ["acme"]


def test_explicit_key_wins_when_label_unknown(make_store):
    alias = get_alias_map(make_store([]) / "projects.json")
    assert get_identity(SessionMeta(project="whatever", project_key="ACME"), alias) == ("acme", False)


def test_unknown_explicit_key_never_falls_back_to_label(make_store):
    alias = get_alias_map(make_store([]) / "projects.json")
    assert get_identity(SessionMeta(project="acme", project_key="nope"), alias) == (None, False)


def test_key_label_conflict_quarantined(make_store):
    _, diag = _run(make_store([session_dict("s1", "clientco", project_key="acme")]))
    assert diag.identity_conflicts == 1 and diag.included == 0


def test_registry_alias_collision_raises(tmp_path):
    reg = tmp_path / "projects.json"
    reg.write_text('{"projects": {"acme": {"aliases": ["shared"]}, "clientco": {"aliases": ["Shared "]}}}')
    with pytest.raises(RegistryError):
        get_alias_map(reg)


# ── scope buckets ─────────────────────────────────────────────────────
def test_non_allowlisted_excluded_and_not_named(make_store):
    rep, diag = _run(make_store([session_dict("s1", "acme"), session_dict("s2", "clientco")]))
    assert diag.other_projects == 1
    assert "clientco" not in rep.model_dump_json()


def test_unresolved_label_counted(make_store):
    rep, diag = _run(make_store([session_dict("s1", "nobody-knows")]))
    assert diag.unresolved == 1 and rep.projects == []


@pytest.mark.parametrize(
    "tags,actor",
    [
        (["meeting"], "ai-assistant"),
        (["Transcription "], "ai-assistant"),
        (["rehome", "state-change"], "ai-assistant"),
        (["duplicate"], "ai-assistant"),
        ([], "whisper-1"),
        ([], "PyAnnote"),
    ],
)
def test_meeting_by_tag_or_recording_actor(make_store, tags, actor):
    evs = [event("e1", "annotation", actor={"type": "system", "id": actor, "role": None})]
    rep, diag = _run(make_store([session_dict("s1", "acme", tags=tags, events=evs)]))
    assert diag.meetings == 1 and rep.projects == []


def test_mixed_session_with_one_recording_event_excluded(make_store):
    evs = [_decision("e1", "accepted"), event("e2", "annotation", actor={"type": "system", "id": "whisper-1", "role": None})]
    _, diag = _run(make_store([session_dict("s1", "acme", events=evs)]))
    assert diag.meetings == 1


def test_recent_activity_after_cutoff_excluded(make_store):
    late = _decision("e1", "accepted")
    late["timestamp"] = "2026-04-09T01:00:00Z"  # after the 00:00 UTC cutoff on the day before AS_OF
    rep, diag = _run(make_store([session_dict("s1", "acme", events=[late]), session_dict("s2", "acme")]))
    assert diag.recent == 1 and rep.coverage.sessions == 1
    assert rep.coverage.cutoff == datetime(2026, 4, 9, tzinfo=UTC)


def test_malformed_counted_and_waterfall_reconciles(make_store):
    store = make_store(
        [session_dict("s1", "acme"), session_dict("s2", "clientco")],
        raw_files={"trace_bad1.json": "{not json", "trace_bad2.json": "[1, 2]", "trace_bad3.json": '{"id": 5}'},
    )
    snap = get_snapshot(store)
    assert snap.malformed == 3 and snap.files_read == 5
    _, diag = _run(store)
    assert _reconciles(snap.files_read, diag)


def test_identical_duplicate_collapses(make_store):
    s = session_dict("dup", "acme", events=[_decision("e1", "accepted")])
    store = make_store([s, s])
    rep, diag = _run(store)
    assert diag.duplicate_copies == 1 and rep.projects[0].sessions == 1
    assert _reconciles(get_snapshot(store).files_read, diag)


def test_conflicting_duplicate_quarantined(make_store):
    a = session_dict("dup", "acme", events=[_decision("e1", "accepted")])
    b = session_dict("dup", "acme", tags=["meeting"])
    store = make_store([a, b, session_dict("ok", "acme")])
    rep, diag = _run(store)
    assert diag.conflicting_ids == 1 and diag.conflicting_files == 2
    assert rep.projects[0].sessions == 1
    assert _reconciles(get_snapshot(store).files_read, diag)


# ── counting and vocab ────────────────────────────────────────────────
def test_old_format_missing_fields_ok(make_store):
    old = _decision("e1", "proposed", resolved=None)
    old["decision"].pop("suggestion_type")  # type: ignore[union-attr]
    rep, _ = _run(make_store([session_dict("s1", "acme", events=[old], version="0.3.0")]))
    p = rep.projects[0]
    assert p.resolved_by == {"not_recorded": 1} and p.proposed_by == {"ai": 1}
    assert rep.coverage.sessions_resolved_by_alias == 1
    assert rep.coverage.format_versions == {"0.3.0": 1}


def test_null_subobjects_do_not_crash(make_store):
    evs = [event("e1", "decision"), event("e2", "contribution"), event("e3", "annotation")]
    p = _run(make_store([session_dict("s1", "acme", events=evs)]))[0].projects[0]
    assert p.decisions == 1 and p.contributions == 1
    assert p.decisions_by_disposition == {"unknown": 1}
    assert p.contributions_by_pair == {"unknown→unknown": 1}


def test_canary_in_every_categorical_field_never_reaches_output(make_store):
    evs = [
        event("e1", CANARY),
        _decision("e2", CANARY, resolved=CANARY, proposed=CANARY),
        _contrib("e3", CANARY, CANARY),
        _ann("e4", CANARY),
    ]
    s = session_dict("s1", "acme", events=evs, version=CANARY)
    rep, diag = _run(make_store([s]))
    blob = rep.model_dump_json() + diag.model_dump_json()
    assert CANARY not in blob
    assert rep.coverage.format_versions == {"unknown": 1}
    p = rep.projects[0]
    assert p.events_by_type == {"annotation": 1, "contribution": 1, "decision": 1, "other": 1}
    assert p.decisions_by_disposition == {"unknown": 1}
    assert p.proposed_by == {"not_recorded": 1} and p.resolved_by == {"not_recorded": 1}
    assert p.contributions_by_pair == {"unknown→unknown": 1}


def test_open_session_counted_per_project(make_store):
    rep, _ = _run(make_store([session_dict("s1", "acme", status="active", ended=None), session_dict("s2", "acme")]))
    assert rep.projects[0].open_sessions == 1 and rep.totals.open_sessions == 1


def test_weekly_zero_fills_and_sums(make_store):
    store = make_store(
        [
            session_dict("s1", "acme", created="2026-03-17T10:00:00Z"),  # 2026-W12
            session_dict("s2", "beta", created="2026-03-31T10:00:00Z"),  # 2026-W14
        ]
    )
    rep, _ = _run(store)
    weeks = {w.week: w.counts for w in rep.weekly}
    assert weeks["2026-W12"] == {"acme": 1, "beta": 0}
    assert weeks["2026-W13"] == {"acme": 0, "beta": 0}
    assert list(weeks)[-1] == "2026-W15"
    assert sum(sum(c.values()) for c in weeks.values()) == rep.totals.sessions


def test_weekly_iso_year_boundary(make_store):
    s = session_dict("s1", "acme", created="2025-12-29T10:00:00Z", ended="2025-12-29T11:00:00Z")
    s["events"] = []
    rep, _ = _run(make_store([s]), as_of=datetime(2026, 1, 6, tzinfo=UTC))
    assert [w.week for w in rep.weekly] == ["2026-W01", "2026-W02"]


def test_rejected_or_revised_and_breakdowns_sum(make_store):
    evs = [_decision("e1", "accepted"), _decision("e2", "rejected"), _decision("e3", "revised"), _decision("e4", "proposed", None)]
    p = _run(make_store([session_dict("s1", "acme", events=evs)]))[0].projects[0]
    assert p.rejected_or_revised == 2 and p.decisions == 4
    assert p.decisions_by_disposition == {"accepted": 1, "proposed": 1, "rejected": 1, "revised": 1}
    assert sum(p.proposed_by.values()) == sum(p.resolved_by.values()) == p.decisions


def test_corrections_discoveries_pairs_and_totals(make_store):
    evs = [_ann("a1", "correction"), _ann("a2", "discovery"), _contrib("c1", "human", "ai"), _contrib("c2", "collaborative", "ai")]
    rep, _ = _run(make_store([session_dict("s1", "acme", events=evs), session_dict("s2", "beta", events=[_contrib("c3", "human", "ai")])]))
    acme = rep.projects[0]
    assert (acme.corrections, acme.discoveries) == (1, 1)
    assert acme.contributions_by_pair == {"collaborative→ai": 1, "human→ai": 1}
    assert rep.totals.key == "all" and rep.totals.contributions == 3
    assert rep.totals.sessions == sum(p.sessions for p in rep.projects)


def test_projects_in_allowlist_order_and_empty_omitted(make_store):
    rep, _ = _run(make_store([session_dict("s1", "beta"), session_dict("s2", "acme")]))
    assert [p.key for p in rep.projects] == ["acme", "beta"]


def test_empty_project_omitted(make_store):
    rep, _ = _run(make_store([session_dict("s3", "beta")]))
    assert [p.key for p in rep.projects] == ["beta"]
