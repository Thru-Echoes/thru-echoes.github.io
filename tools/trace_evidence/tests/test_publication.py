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
DECISIONS = SITE / "projects/trace/trace-decisions.md"
WIDGET = ("chains-graph.mjs", "chains-graph.css")
QUOTE_FRAGMENTS = {"_evidence_excerpts.md", "_evidence_graph.md"}


def _report() -> EvidenceReport:
    return EvidenceReport.model_validate_json(EVIDENCE.read_text())


def test_all_public_files_committed():
    for p in PUBLIC_FILES:
        assert (SITE / p).is_file(), p


def test_committed_json_matches_closed_schema_and_excerpts_are_approved():
    rep = _report()
    assert rep.schema_version == 3
    for x in rep.excerpts:
        assert x.approved_by.strip() and x.approved_on
        assert x.project in {p.key for p in rep.projects}


def test_committed_chains_are_well_formed_graphs():
    rep = _report()
    assert len({x.slug for x in rep.excerpts}) == len(rep.excerpts)
    for x in rep.excerpts:
        ids = [n.id for n in x.nodes]
        assert len(set(ids)) == len(ids) and x.key_event_id in ids
        for e in x.edges:
            assert e.source in ids and e.target in ids and e.source != e.target
        for n in x.nodes:
            assert n.headline.strip()
            assert (n.url is not None) == (n.kind == "external")
            assert n.url is None or n.url.startswith("https://")


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
    authored = [PAGE, DECISIONS, *(SITE / p for p in PUBLIC_FILES if p.suffix == ".md")]
    for f in authored:
        text = f.read_text()
        assert "—" not in text and "–" not in text and " -- " not in text, f.name
        if f.name not in QUOTE_FRAGMENTS:
            # Claims about the records. Verbatim quotes use these words in their
            # ordinary sense ("verified after fixes", "a Next.js application").
            assert not re.search(r"\b(verified|proven|tamper-evident|trustless)\b", text, re.I), f.name
            assert not re.search(r"\b(applications?|accelerators?|investors?|fundrais\w*)\b", text, re.I), f.name


def test_pages_include_each_fragment_exactly_once():
    want = {
        PAGE: ("_evidence_claim.md", "_evidence_table.md", "_evidence_methods.md", "_evidence_contributions.md"),
        DECISIONS: ("_evidence_graph.md", "_evidence_excerpts.md"),
    }
    pages = {pg: pg.read_text() for pg in want}
    for pg, frags in want.items():
        for frag in frags:
            assert sum(t.count(f"{{include}} {frag}") for t in pages.values()) == 1, frag
            assert pages[pg].count(f"{{include}} {frag}") == 1, (pg.name, frag)


def test_overview_links_to_decision_chains_and_back():
    assert "/trace-decisions" in PAGE.read_text()
    assert "/trace-evidence" in DECISIONS.read_text()


def test_widget_module_holds_no_data():
    js = (SITE / "projects/trace" / WIDGET[0]).read_text()
    assert 'model.get("chains")' in js and "export default" in js
    assert "evt_" not in js and "trace_20" not in js


def test_managed_directories_hold_only_generated_files():
    expected = {p.name for p in PUBLIC_FILES if p.parent == Path("static/evidence")}
    assert {f.name for f in (SITE / "static/evidence").iterdir()} == expected
    page_dir = {f.name for f in (SITE / "projects/trace").iterdir()}
    assert page_dir == {p.name for p in PUBLIC_FILES if p.parent == Path("projects/trace")} | {PAGE.name, DECISIONS.name, *WIDGET}
