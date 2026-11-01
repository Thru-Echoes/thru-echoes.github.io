"""Read-only loading of a TRACE store.

Exports:
    RegistryError, StoreError
    get_alias_map(registry_path) -> dict[str, str]
    get_release_map(path) -> dict[str, ProjectDisplay]
    get_snapshot(store_dir) -> Snapshot

Side effects: reads files under the given store directory. Never writes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import ValidationError

from .models import ProjectDisplay, SessionRecord, Snapshot


class RegistryError(ValueError):
    """The alias registry is ambiguous (one normalized alias, two keys)."""


def _norm(s: str) -> str:
    return s.strip().lower()


def get_alias_map(registry_path: Path) -> dict[str, str]:
    """Map every normalized registry key and alias to its canonical key.

    Input: path to `projects.json` (`{"projects": {key: {"aliases": [...]}}}`).
    Output: {normalized alias or key: key}. Raises RegistryError when one
    normalized alias belongs to two keys (never silently picks a winner).
    Side effects: reads one file.
    """
    data = json.loads(registry_path.read_text())
    projects = data.get("projects", data)
    out: dict[str, str] = {}
    for key, entry in projects.items():
        for alias in [key, *((entry or {}).get("aliases") or [])]:
            a = _norm(str(alias))
            if a in out and out[a] != key:
                raise RegistryError("registry alias maps to two project keys")
            out[a] = key
    return out


def get_release_map(path: Path) -> dict[str, ProjectDisplay]:
    """Load the private release mapping: registry key -> public slug, name, link.

    The mapping is the allowlist. It lives outside the public repository so
    that unapproved project names never appear in committed code. Order in
    the file is display order. Raises ValueError on duplicate slugs.
    Side effects: reads one file.
    """
    data = json.loads(path.read_text())
    out = {str(k): ProjectDisplay.model_validate(v) for k, v in data["projects"].items()}
    slugs = [d.slug for d in out.values()]
    if len(slugs) != len(set(slugs)) or "all" in slugs:
        raise ValueError("release map slugs must be unique and not 'all'")
    return out


class StoreError(ValueError):
    """The store is missing or unreadable (never silently treated as empty)."""


def _raw_id(raw: bytes) -> str | None:
    """Session id from the raw JSON object, read before full validation."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    sid = data.get("id") if isinstance(data, dict) else None
    return sid if isinstance(sid, str) and sid else None


def _parse(raw: bytes) -> SessionRecord | None:
    """Parse one session file's bytes, or None if not a valid session object."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        return SessionRecord.model_validate(data)
    except ValidationError:
        return None


def get_snapshot(store_dir: Path) -> Snapshot:
    """Read every `sessions/*.json` file exactly once and de-duplicate by id.

    Files are grouped by the session id read from the raw JSON, before model
    validation, so an invalid copy still counts toward its id. A group whose
    copies are all byte-identical collapses to one session. A group with any
    differing copy (including a copy that fails validation) is quarantined in
    full, because no copy can be trusted to carry the right project or meeting
    status. Files with no readable id are malformed.

    Raises StoreError if the sessions directory does not exist.
    Output: Snapshot with per-id digests of the bytes parsed.
    Side effects: reads files only.
    """
    sessions_dir = store_dir / "sessions"
    if not sessions_dir.is_dir():
        raise StoreError("store has no sessions directory")
    paths = sorted(sessions_dir.glob("*.json"))
    groups: dict[str, list[tuple[Path, bytes]]] = {}
    malformed = 0
    for path in paths:
        try:
            raw = path.read_bytes()
        except OSError:
            malformed += 1
            continue
        sid = _raw_id(raw)
        if sid is None:
            malformed += 1
            continue
        groups.setdefault(sid, []).append((path, raw))
    kept: dict[str, tuple[SessionRecord, str, str]] = {}
    duplicate_copies = conflicting_ids = conflicting_files = 0
    for sid in sorted(groups):
        copies = groups[sid]
        digests = {hashlib.sha256(raw).hexdigest() for _, raw in copies}
        if len(digests) > 1:
            conflicting_ids += 1
            conflicting_files += len(copies)
            continue
        rec = _parse(copies[0][1])
        if rec is None:
            malformed += len(copies)
            continue
        duplicate_copies += len(copies) - 1
        kept[sid] = (rec, str(copies[0][0]), digests.pop())
    return Snapshot(
        sessions=[kept[sid][0] for sid in sorted(kept)],
        paths={sid: kept[sid][1] for sid in sorted(kept)},
        digests={sid: kept[sid][2] for sid in sorted(kept)},
        files_read=len(paths),
        malformed=malformed,
        duplicate_copies=duplicate_copies,
        conflicting_ids=conflicting_ids,
        conflicting_files=conflicting_files,
    )
