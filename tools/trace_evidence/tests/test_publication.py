"""Store-independent checks on the committed evidence outputs (these run in CI).

They prove the committed files are internally consistent and are exactly what
the committed evidence.json renders to, without access to any TRACE store.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.trace_evidence.__main__ import PUBLIC_FILES, main
from tools.trace_evidence.models import EvidenceReport

SITE = Path(__file__).resolve().parents[3]
EVIDENCE = SITE / "static/evidence/evidence.json"
PAGE = SITE / "projects/trace/trace-evidence.md"


def _report() -> EvidenceReport:
    return EvidenceReport.model_validate_json(EVIDENCE.read_text())


def test_all_public_files_committed():
    for p in PUBLIC_FILES:
        assert (SITE / p).is_file(), p


def test_committed_json_matches_closed_schema_and_has_no_excerpts():
    rep = _report()
    assert rep.schema_version == 2
    assert rep.excerpts == []


def test_committed_outputs_are_exactly_the_render_of_committed_json():
    assert main(["--from-json", str(EVIDENCE), "--check", "--root", str(SITE)]) == 0


def test_totals_and_breakdowns_reconcile():
    rep = _report()
    t = rep.totals
    assert t.sessions == sum(p.sessions for p in rep.projects) == rep.coverage.sessions
    for field in ("decisions", "contributions", "corrections", "discoveries", "open_sessions", "rejected_or_revised"):
        assert getattr(t, field) == sum(getattr(p, field) for p in rep.projects), field
    for p in [*rep.projects, t]:
        assert sum(p.decisions_by_disposition.values()) == p.decisions
        assert sum(p.proposed_by.values()) == sum(p.resolved_by.values()) == p.decisions
        assert sum(p.contributions_by_pair.values()) == p.contributions
        assert p.rejected_or_revised == p.decisions_by_disposition.get("rejected", 0) + p.decisions_by_disposition.get("revised", 0)
        assert 0 <= p.open_sessions <= p.sessions
    assert sum(sum(w.counts.values()) for w in rep.weekly) == t.sessions
    assert all(set(w.counts) == {p.key for p in rep.projects} for w in rep.weekly)
    assert sum(rep.coverage.format_versions.values()) == t.sessions
    for p in [*rep.projects, t]:
        assert p.agent_proposals == p.proposed_by.get("ai", 0)
        assert p.agent_proposals_rejected_or_revised <= min(p.rejected_or_revised, p.agent_proposals)


def test_slugs_are_public_ids_only():
    rep = _report()
    assert all(re.fullmatch(r"[a-z0-9-]{1,40}", p.key) for p in rep.projects)


def test_page_copy_rules():
    authored = [PAGE, *(SITE / p for p in PUBLIC_FILES if p.suffix == ".md")]
    for f in authored:
        text = f.read_text()
        assert "—" not in text and "–" not in text and " -- " not in text, f.name
        assert not re.search(r"\b(verified|proven|tamper-evident|trustless)\b", text, re.I), f.name
        assert not re.search(r"\b(applications?|accelerators?|investors?|fundrais\w*)\b", text, re.I), f.name


def test_page_includes_each_fragment_once():
    text = PAGE.read_text()
    for frag in ("_evidence_claim.md", "_evidence_table.md", "_evidence_methods.md", "_evidence_contributions.md"):
        assert text.count(f"{{include}} {frag}") == 1, frag


def test_managed_directories_hold_only_generated_files():
    expected = {p.name for p in PUBLIC_FILES if p.parent == Path("static/evidence")}
    assert {f.name for f in (SITE / "static/evidence").iterdir()} == expected
    page_dir = {f.name for f in (SITE / "projects/trace").iterdir()}
    assert page_dir == {p.name for p in PUBLIC_FILES if p.parent == Path("projects/trace")} | {"trace-evidence.md"}


def test_synthetic_example_is_valid_linked_json():
    import json

    text = PAGE.read_text()
    block = text[text.index("```json") + len("```json") : text.index("```", text.index("```json") + 7)]
    events = json.loads(block)
    ids = {e["id"] for e in events}
    refs = {r for e in events for r in (e.get("contribution") or {}).get("related_decision_ids", [])}
    assert refs and refs <= ids
