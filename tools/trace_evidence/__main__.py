"""CLI: generate the TRACE evidence page data from a local store, or re-render it.

Store mode (local, reads the TRACE store read-only):

    python -m tools.trace_evidence --store ~/.trace \\
        --release-map ../private/release-map.json --private-dir ../private \\
        [--excerpts ../private/approved_excerpts.yaml] [--as-of 2026-11-01T06:00:00Z]

Render mode (no store access; used by CI to prove the committed outputs are
exactly what the committed evidence.json renders to):

    python -m tools.trace_evidence --from-json static/evidence/evidence.json --check

Side effects:
  * store mode writes the 9 PUBLIC_FILES (atomically: all are rendered and
    validated in a temp dir before any is replaced) and two private files,
    evidence-diagnostics.json and evidence-manifest.json, into --private-dir,
    which must be outside the git worktree;
  * render mode writes the rendered files, or with --check writes nothing
    and exits 1 if any committed file differs.
Exit codes: 0 ok, 1 check failed, 2 input rejected, 3 unsafe private dir.

Exports: PUBLIC_FILES, get_rendered(report) -> dict[str, str], main(argv) -> int
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import yaml

from .aggregate import get_cutoff, get_report
from .charts import get_contrib_svg, get_weekly_svg
from .excerpts import ExcerptError, get_excerpts
from .load import get_alias_map, get_release_map, get_snapshot
from .models import EvidenceReport
from .render_md import get_claim_md, get_contrib_table_md, get_methods_md, get_table_md

OUT_DIR = Path("static/evidence")
MD_DIR = Path("projects/trace")
PUBLIC_FILES: tuple[Path, ...] = (
    OUT_DIR / "evidence.json",
    OUT_DIR / "sessions-weekly-light.svg",
    OUT_DIR / "sessions-weekly-dark.svg",
    OUT_DIR / "contributions-light.svg",
    OUT_DIR / "contributions-dark.svg",
    MD_DIR / "_evidence_claim.md",
    MD_DIR / "_evidence_table.md",
    MD_DIR / "_evidence_methods.md",
    MD_DIR / "_evidence_contributions.md",
)
_BANNED = ("—", "–", " -- ")


def get_report_json(report: EvidenceReport) -> str:
    """Deterministic serialization of the public report."""
    return json.dumps(json.loads(report.model_dump_json()), indent=2, sort_keys=False, ensure_ascii=False) + "\n"


def get_rendered(report: EvidenceReport) -> dict[str, str]:
    """Every public file's content keyed by repo-relative path. Pure."""
    return {
        str(OUT_DIR / "evidence.json"): get_report_json(report),
        str(OUT_DIR / "sessions-weekly-light.svg"): get_weekly_svg(report, "light"),
        str(OUT_DIR / "sessions-weekly-dark.svg"): get_weekly_svg(report, "dark"),
        str(OUT_DIR / "contributions-light.svg"): get_contrib_svg(report, "light"),
        str(OUT_DIR / "contributions-dark.svg"): get_contrib_svg(report, "dark"),
        str(MD_DIR / "_evidence_claim.md"): get_claim_md(report),
        str(MD_DIR / "_evidence_table.md"): get_table_md(report),
        str(MD_DIR / "_evidence_methods.md"): get_methods_md(report),
        str(MD_DIR / "_evidence_contributions.md"): get_contrib_table_md(report),
    }


def _validate(files: dict[str, str]) -> None:
    """Raise ValueError if the rendered set is incomplete or malformed."""
    if set(files) != {str(p) for p in PUBLIC_FILES}:
        raise ValueError("rendered file set does not match PUBLIC_FILES")
    for path, text in files.items():
        if path.endswith(".svg"):
            ET.fromstring(text)
        elif path.endswith(".json"):
            EvidenceReport.model_validate_json(text)
        if any(b in text for b in _BANNED):
            raise ValueError(f"banned dash sequence in {path}")


def _write_atomic(root: Path, files: dict[str, str]) -> None:
    """Write all files to a temp dir first, then replace each target. Side effect: writes files."""
    _validate(files)
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        staged: list[tuple[Path, Path]] = []
        for rel, text in files.items():
            p = Path(tmp) / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
            staged.append((p, root / rel))
        for src, dst in staged:
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.replace(src, dst)


def _git_toplevel(root: Path) -> Path | None:
    """The git worktree containing `root`, or None if `root` is not in one."""
    try:
        out = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return Path(out.stdout.strip()).resolve()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _parse_as_of(s: str) -> datetime:
    """ISO timestamp with an explicit offset or Z; naive values are rejected."""
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise argparse.ArgumentTypeError("--as-of needs an explicit UTC offset or Z")
    return dt


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.trace_evidence")
    ap.add_argument("--store", type=Path, default=Path.home() / ".trace")
    ap.add_argument("--release-map", type=Path)
    ap.add_argument("--private-dir", type=Path)
    ap.add_argument("--excerpts", type=Path)
    ap.add_argument("--as-of", type=_parse_as_of)
    ap.add_argument("--root", type=Path, default=Path("."), help="site root to write into")
    ap.add_argument("--from-json", type=Path)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    root = a.root.resolve()

    if a.from_json:
        report = EvidenceReport.model_validate_json(a.from_json.read_text())
        files = get_rendered(report)
        if a.check:
            bad = [rel for rel, text in files.items() if not (root / rel).exists() or (root / rel).read_text() != text]
            for rel in bad:
                print(f"out of date: {rel}", file=sys.stderr)
            return 1 if bad else 0
        _write_atomic(root, files)
        return 0

    if a.check:
        ap.error("--check only applies with --from-json; store mode always writes")
    if a.release_map is None or a.private_dir is None:
        ap.error("store mode needs --release-map and --private-dir")
    private = a.private_dir.resolve()
    top = _git_toplevel(root)
    if top is None:
        print("refusing: --root is not inside a git worktree", file=sys.stderr)
        return 3
    if private == top or top in private.parents or root == private or root in private.parents:
        print("refusing: --private-dir is inside the site worktree", file=sys.stderr)
        return 3
    private_out = [private / "evidence-diagnostics.json", private / "evidence-manifest.json"]
    if any(p.is_symlink() for p in private_out):
        print("refusing: a private output path is a symlink", file=sys.stderr)
        return 3
    as_of = (a.as_of or datetime.now(UTC)).astimezone(UTC)
    try:
        allowlist = get_release_map(a.release_map)
        alias_map = get_alias_map(a.store / "projects.json")
        snapshot = get_snapshot(a.store)
        excerpts = get_excerpts(a.excerpts, snapshot, alias_map, allowlist, get_cutoff(as_of))
    except ExcerptError as e:
        print(f"input rejected: {e}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as e:
        print(f"input rejected: {type(e).__name__}", file=sys.stderr)
        return 2
    report, diagnostics = get_report(snapshot, alias_map, as_of, excerpts, allowlist)
    if report.coverage.sessions == 0:
        print("input rejected: zero sessions included; refusing to publish an empty snapshot", file=sys.stderr)
        return 2
    _write_atomic(root, get_rendered(report))
    private.mkdir(parents=True, exist_ok=True)
    private_out[0].write_text(diagnostics.model_dump_json(indent=2) + "\n")
    manifest = {
        "as_of": as_of.isoformat(),
        "registry_sha256": _sha(a.store / "projects.json"),
        "release_map_sha256": _sha(a.release_map),
        "sessions": {sid: {"path": snapshot.paths[sid], "sha256": d} for sid, d in diagnostics.digests.items()},
    }
    private_out[1].write_text(json.dumps(manifest, indent=2) + "\n")
    for p in private_out:
        p.chmod(0o600)
    print(f"wrote {len(PUBLIC_FILES)} public files; {diagnostics.included} sessions included")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
