"""CLI, excerpt-gate, renderer, and chart tests against synthetic stores."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from tools.trace_evidence.__main__ import PUBLIC_FILES, get_rendered, main
from tools.trace_evidence.aggregate import get_report
from tools.trace_evidence.charts import CONTRIB_CATEGORIES, get_contrib_category, get_contrib_svg, get_weekly_svg
from tools.trace_evidence.load import get_alias_map, get_snapshot
from tools.trace_evidence.models import EvidenceReport

from .conftest import TEST_ALLOWLIST, event, session_dict

AS_OF = "2026-04-10T15:00:00Z"


def _contrib(eid: str, d: str, e: str) -> dict[str, object]:
    c = {"description": "x", "artifact": "f", "direction": d, "execution": e, "related_decision_ids": [], "tags": []}
    return event(eid, "contribution", contribution=c)


@pytest.fixture
def store(make_store) -> Path:
    evs = [_contrib("c1", "human", "ai"), _contrib("c2", "collaborative", "ai"), _contrib("c3", "ai", "ai"), _contrib("c4", "human", "human")]
    return make_store(
        [
            session_dict("s1", "acme", events=evs),
            session_dict("s2", "beta", created="2026-03-31T10:00:00Z", ended="2026-03-31T11:00:00Z"),
            session_dict("s3", "clientco"),
        ]
    )


@pytest.fixture
def release_map(tmp_path: Path) -> Path:
    p = tmp_path / "private" / "release-map.json"
    p.parent.mkdir()
    p.write_text(json.dumps({"projects": {k: v.model_dump() for k, v in TEST_ALLOWLIST.items()}}))
    return p


def _git_root(root: Path) -> Path:
    import subprocess

    root.mkdir(exist_ok=True)
    if not (root / ".git").exists():
        subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def _cli(store: Path, release_map: Path, root: Path, *extra: str) -> int:
    _git_root(root)
    return main(
        ["--store", str(store), "--release-map", str(release_map), "--private-dir", str(release_map.parent),
         "--as-of", AS_OF, "--root", str(root), *extra]
    )  # fmt: skip


def _report(store: Path) -> EvidenceReport:
    snap = get_snapshot(store)
    return get_report(snap, get_alias_map(store / "projects.json"), datetime(2026, 4, 10, 15, tzinfo=UTC), [], TEST_ALLOWLIST)[0]


def _approvals(tmp_path: Path, **over: object) -> Path:
    """Write a one-chain approvals file for session s1 of `store`; `over` replaces top-level keys."""
    import yaml

    entry: dict[str, object] = {
        "session_id": "s1", "title": "T", "key_event_id": "c1",
        "nodes": [{"event_id": "c1", "headline": "Approved words."}],
        "approved": True, "approved_on": date(2026, 4, 9), "approved_by": "owner",
    }  # fmt: skip
    entry.update(over)
    p = tmp_path / "private" / "approved.yaml"
    p.write_text(yaml.safe_dump({"excerpts": [entry]}, sort_keys=False))
    return p


# ── CLI ───────────────────────────────────────────────────────────────
def test_cli_writes_exactly_public_files_and_private_outputs(store, release_map, tmp_path):
    root = tmp_path / "site"
    assert _cli(store, release_map, root) == 0
    written = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and ".git" not in p.parts)
    assert written == sorted(str(p) for p in PUBLIC_FILES)
    rep = EvidenceReport.model_validate_json((root / "static/evidence/evidence.json").read_text())
    assert rep.coverage.sessions == 2 and rep.excerpts == []
    assert (release_map.parent / "evidence-diagnostics.json").exists()
    assert set(json.loads((release_map.parent / "evidence-manifest.json").read_text())["sessions"]) == {"s1", "s2"}


def test_cli_output_is_deterministic(store, release_map, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _cli(store, release_map, a)
    _cli(store, release_map, b)
    for p in PUBLIC_FILES:
        assert (a / p).read_text() == (b / p).read_text()


def test_from_json_check_detects_drift(store, release_map, tmp_path):
    root = tmp_path / "site"
    _cli(store, release_map, root)
    ev = str(root / "static/evidence/evidence.json")
    assert main(["--from-json", ev, "--check", "--root", str(root)]) == 0
    (root / "projects/trace/_evidence_table.md").write_text("tampered\n")
    assert main(["--from-json", ev, "--check", "--root", str(root)]) == 1


def test_private_dir_inside_worktree_refused(store, release_map, tmp_path):
    root = tmp_path / "site"
    assert _cli(store, release_map, root, "--private-dir", str(root / "static" / "private")) == 3
    assert not (root / "static").exists()


def test_root_outside_git_refused(store, release_map, tmp_path):
    root = tmp_path / "nogit"
    root.mkdir()
    rc = main(["--store", str(store), "--release-map", str(release_map), "--private-dir", str(release_map.parent),
               "--as-of", AS_OF, "--root", str(root)])  # fmt: skip
    assert rc == 3 and not any(root.iterdir())


def test_check_flag_rejected_in_store_mode(store, release_map, tmp_path):
    with pytest.raises(SystemExit):
        _cli(store, release_map, tmp_path / "site", "--check")
    assert not (tmp_path / "site" / "static").exists()


def test_naive_as_of_rejected(store, release_map, tmp_path):
    root = _git_root(tmp_path / "site")
    with pytest.raises(SystemExit):
        main(["--store", str(store), "--release-map", str(release_map), "--private-dir", str(release_map.parent),
              "--as-of", "2026-04-10T15:00:00", "--root", str(root)])  # fmt: skip


def test_missing_sessions_dir_rejected_without_writing(release_map, tmp_path):
    store = tmp_path / "emptystore"
    store.mkdir()
    (store / "projects.json").write_text('{"projects": {"acme": {"aliases": []}}}')
    assert _cli(store, release_map, tmp_path / "site") == 2
    assert not (tmp_path / "site" / "static").exists()


def test_zero_included_sessions_refused(make_store, release_map, tmp_path):
    store = make_store([session_dict("only", "clientco")])
    assert _cli(store, release_map, tmp_path / "site") == 2
    assert not (tmp_path / "site" / "static").exists()


def test_malformed_approvals_yaml_rejected_without_echo(store, release_map, tmp_path, capsys):
    bad = tmp_path / "private" / "approved.yaml"
    bad.write_text("excerpts: [ {text: zz-canary-text, : : :\n")
    assert _cli(store, release_map, tmp_path / "site", "--excerpts", str(bad)) == 2
    assert "zz-canary-text" not in capsys.readouterr().err


def test_cli_stdout_never_names_excluded_projects(store, release_map, tmp_path, capsys):
    _cli(store, release_map, tmp_path / "site")
    out = capsys.readouterr()
    assert "clientco" not in out.out + out.err


# ── excerpt gate ──────────────────────────────────────────────────────
def test_approved_excerpt_published(store, release_map, tmp_path):
    root = tmp_path / "site"
    assert _cli(store, release_map, root, "--excerpts", str(_approvals(tmp_path))) == 0
    rep = EvidenceReport.model_validate_json((root / "static/evidence/evidence.json").read_text())
    (x,) = rep.excerpts
    assert x.project == "acme" and x.slug == "t" and [n.headline for n in x.nodes] == ["Approved words."]
    assert x.nodes[0].kind == "contribution" and (x.nodes[0].direction, x.nodes[0].execution) == ("human", "ai")
    md = (root / "projects/trace/_evidence_excerpts.md").read_text()
    assert "### T" in md and "> Approved words." in md and "*Acme, March 2026*" in md
    graph = (root / "projects/trace/_evidence_graph.md").read_text()
    assert graph.startswith(":::{anywidget} /projects/trace/chains-graph.mjs\n") and "Approved words." in graph
    assert (root / "projects/trace/_evidence_featured.md").read_text() == ""  # nothing featured


def _dec(eid: str, by: str, disp: str, res: str | None, revises: object = None) -> dict[str, object]:
    d = {"description": "x", "rationale": "y", "proposed_by": {"type": by, "id": by}, "disposition": disp,
         "resolved_by": {"type": res, "id": res} if res else None, "revises_event_id": revises}  # fmt: skip
    return event(eid, "decision", decision=d)


@pytest.fixture
def chain_store(make_store) -> Path:
    """One acme session whose records link to each other and outward."""
    evs = [
        _dec("d1", "ai", "rejected", "human"),
        _dec("d2", "ai", "accepted", "human", revises="d1"),
        event("a1", "annotation", annotation={"category": "correction", "content": "z",
              "corrects_event_ids": ["d2", "external:github.com/acme/repo/pull/7", "gone"]}),  # fmt: skip
        event("c1", "contribution", contribution={"description": "x", "artifact": "f", "direction": "human",
              "execution": "ai", "related_decision_ids": ["d1", "d2", "d9"]}),  # fmt: skip
        event("t1", "tool_call", tool_call={"name": "x"}),
    ]
    return make_store([session_dict("s1", "acme", events=evs), session_dict("s3", "clientco")])


def _chain(chain_store: Path, release_map: Path, tmp_path: Path, **over: object):
    root = tmp_path / "site"
    rc = _cli(chain_store, release_map, root, "--excerpts", str(_approvals(tmp_path, **over)))
    if rc != 0:
        return rc, None
    return rc, EvidenceReport.model_validate_json((root / "static/evidence/evidence.json").read_text()).excerpts[0]


_ALL = [{"event_id": e, "headline": f"h {e}"} for e in ("d1", "d2", "a1", "c1")]
_EXT = [{"ref": "external:github.com/acme/repo/pull/7", "label": "acme pull request 7"}]


def test_edges_come_from_the_records_not_the_approvals(chain_store, release_map, tmp_path):
    rc, x = _chain(chain_store, release_map, tmp_path, key_event_id="a1", nodes=_ALL, external=_EXT)
    assert rc == 0 and x is not None
    assert {(e.source, e.relation, e.target) for e in x.edges} == {
        ("d2", "revises", "d1"), ("a1", "corrects", "d2"), ("a1", "corrects", "ext-1"),
        ("c1", "builds_on", "d1"), ("c1", "builds_on", "d2"),
    }  # fmt: skip
    assert x.unshown_links == 2  # a1 -> "gone", c1 -> "d9"
    d1 = next(n for n in x.nodes if n.id == "d1")
    assert (d1.kind, d1.proposed_by, d1.disposition, d1.resolved_by) == ("decision", "ai", "rejected", "human")
    ext = next(n for n in x.nodes if n.kind == "external")
    assert ext.url == "https://github.com/acme/repo/pull/7" and ext.headline == "acme pull request 7"
    assert next(n for n in x.nodes if n.id == "a1").kind == "correction"


def test_links_to_unshown_records_are_counted_not_drawn(chain_store, release_map, tmp_path):
    nodes = [{"event_id": "d2", "headline": "h"}, {"event_id": "c1", "headline": "h"}]
    rc, x = _chain(chain_store, release_map, tmp_path, key_event_id="d2", nodes=nodes)
    assert rc == 0 and x is not None
    assert [(e.source, e.relation, e.target) for e in x.edges] == [("c1", "builds_on", "d2")]
    assert x.unshown_links == 3  # d2 -> d1, c1 -> d1, c1 -> d9


def test_malformed_link_fields_neither_break_parsing_nor_draw_edges(make_store, release_map, tmp_path):
    evs = [_dec("d1", "ai", "accepted", "human", revises=17),
           event("a1", "annotation", annotation={"category": "correction", "corrects_event_ids": {"bad": 1}})]  # fmt: skip
    st = make_store([session_dict("s1", "acme", events=evs)])
    nodes = [{"event_id": "d1", "headline": "h"}, {"event_id": "a1", "headline": "h"}]
    rc, x = _chain(st, release_map, tmp_path, key_event_id="d1", nodes=nodes)
    assert rc == 0 and x is not None and x.edges == [] and x.unshown_links == 0
    rep = EvidenceReport.model_validate_json((tmp_path / "site/static/evidence/evidence.json").read_text())
    assert rep.coverage.sessions == 1 and rep.totals.decisions == 1


@pytest.mark.parametrize(
    "over,code",
    [
        ({"approved": False}, "not-approved"),
        ({"approved": "yes"}, "not-approved"),
        ({"approved_on": ""}, "missing-approved-on"),
        ({"approved_by": ""}, "missing-approved-by"),
        ({"title": ""}, "missing-title"),
        ({"nodes": []}, "missing-nodes"),
        ({"session_id": "s3"}, "session-out-of-scope"),
        ({"session_id": "nope"}, "session-not-found"),
        ({"nodes": [{"event_id": "zzz", "headline": "h"}]}, "event-not-in-session"),
        ({"nodes": [{"event_id": "d1", "headline": " "}]}, "missing-headline"),
        ({"nodes": [{"event_id": "d1", "headline": "h"}, {"event_id": "d1", "headline": "h"}]}, "duplicate-node"),
        ({"nodes": [{"event_id": "t1", "headline": "h"}], "key_event_id": "t1"}, "unsupported-node-type"),
        ({"key_event_id": "c1", "nodes": [{"event_id": "d1", "headline": "h"}]}, "key-event-not-a-node"),
        ({"external": [{"ref": "external:github.com/acme/other/pull/1", "label": "x"}]}, "external-not-in-records"),
        ({"external": [{"ref": "javascript:alert(1)", "label": "x"}]}, "bad-external"),
        ({"external": [{"ref": "external:http://github.com/acme/repo/pull/7", "label": "x"}]}, "bad-external"),
        ({"key_event_id": "a1", "nodes": [{"event_id": "a1", "headline": "h"}], "external": _EXT * 2}, "duplicate-external"),
        ({"external": [{"ref": "external:github.com/acme/repo/pull/7", "label": ""}]}, "bad-external"),
    ],
)
def test_bad_excerpt_rejected_without_echoing_content(chain_store, release_map, tmp_path, capsys, over, code):
    base: dict[str, object] = {"key_event_id": "d1", "nodes": [{"event_id": "d1", "headline": "Approved words."}], "external": _EXT}
    base.update(over)
    rc, _ = _chain(chain_store, release_map, tmp_path, **base)
    err = capsys.readouterr().err
    assert rc == 2 and code in err
    assert "Approved words" not in err and "s1" not in err.replace("entry", "") and "github" not in err
    assert not (tmp_path / "site" / "static").exists()


def test_self_links_and_cycles_are_rejected(make_store, release_map, tmp_path, capsys):
    loop = [_dec("d1", "ai", "accepted", "human", revises="d1")]
    cyc = [_dec("d1", "ai", "accepted", "human", revises="d2"), _dec("d2", "ai", "accepted", "human", revises="d1")]
    for evs, nodes in ((loop, ["d1"]), (cyc, ["d1", "d2"])):
        st = make_store([session_dict("s1", "acme", events=evs)])
        rc, _ = _chain(st, release_map, tmp_path, key_event_id="d1", nodes=[{"event_id": n, "headline": "h"} for n in nodes])
        assert rc == 2 and "cyclic-links" in capsys.readouterr().err


def test_duplicate_titles_are_rejected(chain_store, release_map, tmp_path, capsys):
    import yaml

    one = {"session_id": "s1", "title": "Same title", "key_event_id": "d1", "nodes": [{"event_id": "d1", "headline": "h"}],
           "approved": True, "approved_on": date(2026, 4, 9), "approved_by": "owner"}  # fmt: skip
    p = tmp_path / "private" / "approved.yaml"
    p.write_text(yaml.safe_dump({"excerpts": [one, {**one, "title": "Same, title!"}]}))
    assert _cli(chain_store, release_map, tmp_path / "site", "--excerpts", str(p)) == 2
    assert "duplicate-title" in capsys.readouterr().err


def test_only_corrections_draw_corrects_links(make_store, release_map, tmp_path):
    evs = [_dec("d1", "ai", "accepted", "human"),
           event("g1", "annotation", annotation={"category": "gotcha", "corrects_event_ids": ["d1"]})]  # fmt: skip
    st = make_store([session_dict("s1", "acme", events=evs)])
    nodes = [{"event_id": "d1", "headline": "h"}, {"event_id": "g1", "headline": "h"}]
    rc, x = _chain(st, release_map, tmp_path, key_event_id="d1", nodes=nodes)
    assert rc == 0 and x is not None and x.edges == [] and x.nodes[1].kind == "annotation"


def test_human_ruling_is_published_only_on_human_rejections_and_revisions(chain_store, release_map, tmp_path):
    nodes = [{"event_id": "d1", "headline": "h", "resolution": "No, because Y."}]
    rc, x = _chain(chain_store, release_map, tmp_path, key_event_id="d1", nodes=nodes)
    assert rc == 0 and x is not None and x.nodes[0].resolution == "No, because Y."
    md = (tmp_path / "site/projects/trace/_evidence_excerpts.md").read_text()
    assert "> **d1, Human rejected**\n>\n> No, because Y." in md


def test_ruling_requires_a_human_resolver_and_allows_revisions(make_store, release_map, tmp_path, capsys):
    evs = [_dec("r1", "human", "rejected", "ai"), _dec("v1", "ai", "revised", "human")]
    st = make_store([session_dict("s1", "acme", events=evs)])
    rc, _ = _chain(st, release_map, tmp_path, key_event_id="r1", nodes=[{"event_id": "r1", "headline": "h", "resolution": "zz"}])
    assert rc == 2 and "resolution-not-allowed" in capsys.readouterr().err  # rejected, but by an AI
    rc, x = _chain(st, release_map, tmp_path, key_event_id="v1", nodes=[{"event_id": "v1", "headline": "h", "resolution": "Keep it, but Z.\n\nSecond paragraph."}])
    assert rc == 0 and x is not None and x.nodes[0].resolution
    md = (tmp_path / "site/projects/trace/_evidence_excerpts.md").read_text()
    assert "> **v1, Human revised**\n>\n> Keep it, but Z.\n>\n> Second paragraph.\n" in md  # stays inside the quote


@pytest.mark.parametrize("eid", ["d2", "a1", "c1"])  # accepted decision, correction, contribution
def test_ruling_text_on_other_records_is_rejected(chain_store, release_map, tmp_path, capsys, eid):
    rc, _ = _chain(chain_store, release_map, tmp_path, key_event_id=eid, nodes=[{"event_id": eid, "headline": "h", "resolution": "zz"}])
    assert rc == 2 and "resolution-not-allowed" in capsys.readouterr().err


def test_featured_chain_renders_compact_block_with_link(chain_store, release_map, tmp_path):
    import json as _json

    rc, _ = _chain(chain_store, release_map, tmp_path, key_event_id="d1", nodes=[{"event_id": "d1", "headline": "h"}], featured=True)
    assert rc == 0
    text = (tmp_path / "site/projects/trace/_evidence_featured.md").read_text()
    lines = text.splitlines()
    at = lines.index(":::{anywidget} /projects/trace/chains-graph.mjs")
    assert lines[at + 2] == ":class: trace-featured" and _json.loads(lines[at + 3])["compact"] is True
    assert text.startswith("**One decision chain from my TRACE records.**")
    assert "[See the decision chain →](/trace-evidence#chain=t)" in text


def test_featured_must_be_boolean_and_unique(chain_store, release_map, tmp_path, capsys):
    import yaml

    one = {"session_id": "s1", "key_event_id": "d1", "nodes": [{"event_id": "d1", "headline": "h"}], "featured": True,
           "approved": True, "approved_on": date(2026, 4, 9), "approved_by": "owner"}  # fmt: skip
    p = tmp_path / "private" / "approved.yaml"
    p.write_text(yaml.safe_dump({"excerpts": [{**one, "title": "A"}, {**one, "title": "B"}]}))
    assert _cli(chain_store, release_map, tmp_path / "site", "--excerpts", str(p)) == 2
    assert "multiple-featured" in capsys.readouterr().err
    p.write_text(yaml.safe_dump({"excerpts": [{**one, "title": "A", "featured": "yes"}]}))
    assert _cli(chain_store, release_map, tmp_path / "site", "--excerpts", str(p)) == 2
    assert "bad-featured" in capsys.readouterr().err


def test_external_ref_must_be_stored_by_a_shown_record(chain_store, release_map, tmp_path):
    rc, _ = _chain(chain_store, release_map, tmp_path, key_event_id="d1", nodes=[{"event_id": "d1", "headline": "h"}], external=_EXT)
    assert rc == 2  # a1 stores the ref, but a1 is not shown


def test_missing_excerpts_file_is_empty(store, release_map, tmp_path):
    assert _cli(store, release_map, tmp_path / "site", "--excerpts", str(tmp_path / "nope.yaml")) == 0


def test_slugs_are_stable_anchors():
    from tools.trace_evidence.excerpts import get_slug

    assert get_slug("Shouldn't it just be the one-liner?") == "shouldnt-it-just-be-the-one-liner"
    assert get_slug("Megatonnes are not metric tons") == "megatonnes-are-not-metric-tons"
    assert get_slug("???") == "chain"


def test_text_version_labels_quotes_but_not_headlines(chain_store, release_map, tmp_path):
    nodes = [{"event_id": "d1", "headline": "Plan: do X"}, {"event_id": "d2", "headline": "h", "text": "Agent proposed: do Y\nHuman accepted: fine"}]
    rc, x = _chain(chain_store, release_map, tmp_path, key_event_id="d2", nodes=nodes)
    assert rc == 0
    md = (tmp_path / "site/projects/trace/_evidence_excerpts.md").read_text()
    assert "> **d1, Decision: agent proposal, rejected by human**" in md
    assert "> Plan: do X" in md  # a headline is never split into a fake label
    assert "> **Agent proposed:** do Y\n>\n> **Human accepted:** fine" in md
    assert "Links stored in these records: d2 revises d1." in md


def test_graph_block_body_is_the_chain_data(chain_store, release_map, tmp_path):
    import json as _json

    rc, _ = _chain(chain_store, release_map, tmp_path, key_event_id="a1", nodes=_ALL, external=_EXT)
    assert rc == 0
    lines = (tmp_path / "site/projects/trace/_evidence_graph.md").read_text().splitlines()
    assert lines[:3] == [":::{anywidget} /projects/trace/chains-graph.mjs", ":css: /projects/trace/chains-graph.css", ":class: col-page-right"] and lines[-1] == ":::"
    model = _json.loads(lines[3])
    (c,) = model["chains"]
    assert c["key"] == "a1" and len(c["edges"]) == 5 and c["unshown"] == 2
    assert {n["label"] for n in c["nodes"]} >= {"Correction", "External reference", "Contribution: human idea, AI built"}


# ── renderers ─────────────────────────────────────────────────────────
def test_rendered_markdown_has_no_banned_dashes(store):
    for path, text in get_rendered(_report(store)).items():
        assert "—" not in text and "–" not in text and " -- " not in text, path


def test_table_rows_and_totals(store):
    table = get_rendered(_report(store))["projects/trace/_evidence_table.md"]
    rows = [r for r in table.splitlines() if r.startswith("| ")]
    assert len(rows) == 1 + 2 + 1  # header + 2 projects + totals
    assert "[Acme](https://example.com/acme)" in table and "**All projects**" in table


# ── charts ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_svgs_parse_and_are_accessible(store, theme):
    rep = _report(store)
    for svg in (get_weekly_svg(rep, theme), get_contrib_svg(rep, theme)):
        root = ET.fromstring(svg)
        assert root.get("role") == "img" and root.get("viewBox")
        ns = "{http://www.w3.org/2000/svg}"
        assert root.find(f"{ns}title") is not None and root.find(f"{ns}desc") is not None


def test_light_and_dark_differ_only_in_colors(store):
    import re

    rep = _report(store)
    strip = lambda s: re.sub(r"#[0-9a-fA-F]{6}", "#", s)  # noqa: E731
    assert strip(get_weekly_svg(rep, "light")) == strip(get_weekly_svg(rep, "dark"))
    assert strip(get_contrib_svg(rep, "light")) == strip(get_contrib_svg(rep, "dark"))


def test_contrib_categories_cover_every_pair():
    from tools.trace_evidence.models import PAIR_KEYS

    assert {get_contrib_category(k) for k in PAIR_KEYS} == set(CONTRIB_CATEGORIES)
    assert get_contrib_category("human→ai") == "Human idea, AI built"
    assert get_contrib_category("ai→human") == "Human or shared execution"
    assert get_contrib_category("unknown→ai") == "Not recorded"


def test_contrib_svg_labels_n_per_project(store):
    svg = get_contrib_svg(_report(store), "light")
    assert "n = 4" in svg and "n = 0" in svg and "No recorded contributions" in svg


def test_contrib_table_matches_pairs(store):
    table = get_rendered(_report(store))["projects/trace/_evidence_contributions.md"]
    assert "| Acme | 1 | 1 | 1 | 1 | 4 |" in table
