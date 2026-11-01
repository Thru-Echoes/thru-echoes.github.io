"""CLI, excerpt-gate, renderer, and chart tests against synthetic stores."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
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
    entry: dict[str, object] = {"event_id": "c1", "session_id": "s1", "title": "T", "text": "Approved words.", "approved": True, "approved_on": "2026-04-09"}
    entry.update(over)
    lines = ["excerpts:", "  - " + "\n    ".join(f"{k}: {json.dumps(v) if isinstance(v, str) and k != 'approved_on' else v}" for k, v in entry.items())]
    p = tmp_path / "private" / "approved.yaml"
    p.write_text("\n".join(lines) + "\n")
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
    assert [e.text for e in rep.excerpts] == ["Approved words."] and rep.excerpts[0].project == "acme"


@pytest.mark.parametrize(
    "over,code",
    [
        ({"approved": False}, "not-approved"),
        ({"approved": "yes"}, "not-approved"),
        ({"approved_on": '""'}, "missing-approved-on"),
        ({"session_id": "s3"}, "session-out-of-scope"),
        ({"session_id": "nope"}, "session-not-found"),
        ({"event_id": "zzz"}, "event-not-in-session"),
    ],
)
def test_bad_excerpt_rejected_without_echoing_content(store, release_map, tmp_path, capsys, over, code):
    rc = _cli(store, release_map, tmp_path / "site", "--excerpts", str(_approvals(tmp_path, **over)))
    err = capsys.readouterr().err
    assert rc == 2 and code in err
    assert "Approved words" not in err and "s1" not in err.replace("entry", "")
    assert not (tmp_path / "site" / "static").exists()


def test_missing_excerpts_file_is_empty(store, release_map, tmp_path):
    assert _cli(store, release_map, tmp_path / "site", "--excerpts", str(tmp_path / "nope.yaml")) == 0


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
