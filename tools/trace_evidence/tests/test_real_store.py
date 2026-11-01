"""Local release checks against the real TRACE store and private inputs.

Skipped where the private inputs are absent (CI). With EVIDENCE_RELEASE=1 a
missing input is a failure, so a release run cannot pass by skipping.

Private inputs, all outside the git worktree (default ../notes/evidence, or
EVIDENCE_PRIVATE_DIR): release-map.json, evidence-manifest.json,
private_terms.txt; plus the TRACE registry at ~/.trace/projects.json.

Failure messages report counts and file names only, never matched terms.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import subprocess
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools.trace_evidence.__main__ import PUBLIC_FILES, get_rendered
from tools.trace_evidence.aggregate import get_report
from tools.trace_evidence.load import get_alias_map, get_release_map, get_snapshot
from tools.trace_evidence.models import EvidenceReport

SITE = Path(__file__).resolve().parents[3]
PRIVATE = Path(os.environ.get("EVIDENCE_PRIVATE_DIR", SITE.parent / "notes" / "evidence"))
STORE = Path(os.environ.get("TRACE_STORE", Path.home() / ".trace"))
RELEASE = os.environ.get("EVIDENCE_RELEASE") == "1"
NEEDED = [STORE / "projects.json", PRIVATE / "release-map.json", PRIVATE / "evidence-manifest.json", PRIVATE / "private_terms.txt"]

if not all(p.exists() for p in NEEDED):
    if RELEASE:
        raise RuntimeError(f"release check: {sum(not p.exists() for p in NEEDED)} private input(s) missing")
    pytest.skip("private release inputs not available", allow_module_level=True)

COMMITTED = EvidenceReport.model_validate_json((SITE / "static/evidence/evidence.json").read_text())
MANIFEST = json.loads((PRIVATE / "evidence-manifest.json").read_text())
PUBLIC_OK_TOKENS = {
    "trace", "trace-mcp", "proofpress", "proofpress-experiments", "coeqwal", "rsi-exam-provenance", "waggle", "echoes-portfolio",
}  # fmt: skip
GENERIC_WORDS = {"meeting", "personal", "travel", "tax", "conf"}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKC", html.unescape(text)).lower()


# ── frozen inputs ─────────────────────────────────────────────────────
def test_private_terms_list_not_empty():
    assert len(_private_terms()) >= 5, "private terms list is empty or truncated"


def test_manifest_inputs_unchanged():
    assert _sha(STORE / "projects.json") == MANIFEST["registry_sha256"], "registry changed; regenerate"
    assert _sha(PRIVATE / "release-map.json") == MANIFEST["release_map_sha256"], "release map changed; regenerate"
    changed = sum(_sha(Path(v["path"])) != v["sha256"] for v in MANIFEST["sessions"].values())
    assert changed == 0, f"{changed} included session file(s) changed since generation; regenerate"


def test_committed_outputs_regenerate_exactly():
    rm = get_release_map(PRIVATE / "release-map.json")
    snap = get_snapshot(STORE)
    rep, diag = get_report(snap, get_alias_map(STORE / "projects.json"), COMMITTED.as_of, [], rm)
    assert set(diag.digests) == set(MANIFEST["sessions"])
    for rel, text in get_rendered(rep).items():
        assert (SITE / rel).read_text() == text, rel


# ── independent recount (plain json; restates the definitions) ────────
def _recount() -> dict[str, Counter[str]]:
    reg = json.loads((STORE / "projects.json").read_text())["projects"]
    alias = {a.strip().lower(): k for k, v in reg.items() for a in [k, *(v.get("aliases") or [])]}
    rmap = json.loads((PRIVATE / "release-map.json").read_text())["projects"]
    cutoff = datetime.fromisoformat(COMMITTED.coverage.cutoff.isoformat())
    out: dict[str, Counter[str]] = {}
    for v in MANIFEST["sessions"].values():
        d = json.loads(Path(v["path"]).read_text())
        m = d.get("metadata") or {}
        key = alias.get((m.get("project_key") or "").strip().lower()) if m.get("project_key") else alias.get((m.get("project") or "").strip().lower())
        assert key in rmap
        tags = {str(t).strip().lower() for t in m.get("tags") or []}
        assert not tags & {"meeting", "transcription", "rehome", "duplicate"}
        evs = d.get("events") or []
        assert not any(((e.get("actor") or {}).get("id") or "").strip().lower() in {"whisper-1", "pyannote"} for e in evs)
        stamps = [d.get("created"), d.get("ended"), *(e.get("timestamp") for e in evs)]
        last = max(datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC) for s in stamps if s)
        assert last < cutoff
        c = out.setdefault(rmap[key]["slug"], Counter())
        c["sessions"] += 1
        for e in evs:
            t = e.get("type")
            if t == "decision":
                c["decisions"] += 1
                c["disp:" + ((e.get("decision") or {}).get("disposition") or "unknown")] += 1
            elif t == "contribution":
                x = e.get("contribution") or {}
                c["contributions"] += 1
                c[f"pair:{x.get('direction') or 'unknown'}→{x.get('execution') or 'unknown'}"] += 1
            elif t == "annotation":
                cat = (e.get("annotation") or {}).get("category")
                c["corrections"] += cat == "correction"
                c["discoveries"] += cat == "discovery"
    return out


def test_totals_match_independent_recount():
    recount = _recount()
    assert set(recount) == {p.key for p in COMMITTED.projects}
    for p in COMMITTED.projects:
        r = recount[p.key]
        assert (p.sessions, p.decisions, p.contributions, p.corrections, p.discoveries) == (
            r["sessions"], r["decisions"], r["contributions"], r["corrections"], r["discoveries"]
        ), p.key  # fmt: skip
        assert {k: v for k, v in p.decisions_by_disposition.items()} == {k[5:]: v for k, v in r.items() if k.startswith("disp:")}
        assert dict(p.contributions_by_pair) == {k[5:]: v for k, v in r.items() if k.startswith("pair:")}


# ── leak guards ───────────────────────────────────────────────────────
def _publication_surface() -> dict[str, str]:
    """Repo-authored new/changed files plus the built site, if present."""
    files: dict[str, str] = {}
    changed = subprocess.run(
        ["git", "diff", "-z", "--name-only", "origin/main", "--"], cwd=SITE, capture_output=True, text=True, check=True
    ).stdout.split("\0")
    untracked = subprocess.run(
        ["git", "ls-files", "-z", "--others", "--exclude-standard"], cwd=SITE, capture_output=True, text=True, check=True
    ).stdout.split("\0")
    for rel in {*changed, *untracked, *(str(p) for p in PUBLIC_FILES)} - {""}:
        p = SITE / rel
        files[f"path:{rel}"] = rel  # file names are publication content too
        if p.is_file() and not p.is_symlink():
            files[f"repo:{rel}"] = p.read_text(errors="replace")
    build = SITE / "_build" / "html"
    page = build / "trace-evidence" / "index.html"
    if RELEASE:
        assert page.is_file(), "release check needs a fresh `mystmd build --html` first"
        assert page.stat().st_mtime >= (SITE / "static/evidence/evidence.json").stat().st_mtime, "build is older than evidence.json; rebuild"
    if build.is_dir():
        # Page content lives in .html and per-page .json; the theme's minified
        # JS bundles under build/ (and *.min.js) are fixed third-party code whose
        # identifiers produce false matches, so they are not part of the scan.
        for p in build.rglob("*"):
            rel = p.relative_to(build)
            if not p.is_file() or rel.parts[0] == "build" or p.name.endswith(".js"):
                continue
            if p.suffix in {".html", ".json", ".svg", ".css", ".txt", ".xml"}:
                files[f"build:{rel}"] = p.read_text(errors="replace")
    return files


def _token_hits(text: str, tokens: set[str]) -> int:
    t = _norm(text)
    return sum(len(re.findall(rf"(?<![a-z0-9_-]){re.escape(tok)}(?![a-z0-9_-])", t)) for tok in tokens)


def test_no_foreign_registry_names_published():
    reg = json.loads((STORE / "projects.json").read_text())["projects"]
    tokens = {a.strip().lower() for k, v in reg.items() for a in [k, *(v.get("aliases") or [])]}
    forbidden = tokens - PUBLIC_OK_TOKENS
    surface = _publication_surface()
    bad = []
    for name, text in surface.items():
        toks = forbidden - GENERIC_WORDS
        if _token_hits(text, toks):
            bad.append(name)
    assert not bad, f"{len(bad)} file(s) contain a non-public registry name: {sorted(bad)[:10]}"


def _private_terms() -> list[str]:
    lines = (PRIVATE / "private_terms.txt").read_text().splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]


def _term_hit(text: str, term: str) -> bool:
    if term.startswith("cs:"):
        return re.search(rf"(?<![A-Za-z0-9]){re.escape(term[3:])}(?![A-Za-z0-9])", html.unescape(text)) is not None
    return term.lower() in _norm(text)


def test_no_private_terms_in_publication_surface():
    terms = _private_terms()
    bad = sorted(name for name, text in _publication_surface().items() if any(_term_hit(text, t) for t in terms))
    assert not bad, f"{len(bad)} file(s) contain a private term: {bad[:10]}"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=SITE, capture_output=True, text=True, check=True).stdout


def test_no_private_terms_in_unpushed_commits():
    # Messages and identities are scanned whole. Patches are scanned for added
    # lines only: removed lines ("-") already exist on origin/main.
    messages = _git("log", "--format=%an%n%cn%n%B", "origin/main..HEAD")
    patches = _git("log", "-p", "-m", "--format=", "origin/main..HEAD")
    added = "\n".join(ln for ln in patches.splitlines() if not (ln.startswith("-") and not ln.startswith("---")))
    terms = _private_terms()
    assert not any(_term_hit(messages, t) for t in terms), "an unpushed commit message or name contains a private term"
    assert not any(_term_hit(added, t) for t in terms), "an unpushed commit adds a private term"
    reg = json.loads((STORE / "projects.json").read_text())["projects"]
    forbidden = {a.strip().lower() for k, v in reg.items() for a in [k, *(v.get("aliases") or [])]} - PUBLIC_OK_TOKENS - GENERIC_WORDS
    assert _token_hits(messages + "\n" + added, forbidden) == 0, "an unpushed commit contains a non-public registry name"
    idents = _git("log", "--format=%ae%n%ce", "origin/main..HEAD").split()
    assert set(idents) <= {"omuellerklein@berkeley.edu"}, f"{len(set(idents))} unexpected commit identities"


def test_no_duplicate_event_ids_in_included_sessions():
    diag = json.loads((PRIVATE / "evidence-diagnostics.json").read_text())
    assert diag["duplicate_event_ids"] == 0
