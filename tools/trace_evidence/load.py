"""Read-only loading of a TRACE store.

Exports:
    RegistryError
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

    Byte-identical copies of one id collapse to one session. If copies of an
    id differ, every copy is quarantined (counted, never included), because
    no copy can be trusted to carry the right project or meeting status.
    Output: Snapshot with per-id digests of the bytes parsed.
    Side effects: reads files only.
    """
    paths = sorted((store_dir / "sessions").glob("*.json"))
    seen: dict[str, tuple[SessionRecord, str, str]] = {}
    conflicting: set[str] = set()
    file_ids: list[str] = []
    malformed = duplicate_copies = 0
    for path in paths:
        try:
            raw = path.read_bytes()
        except OSError:
            malformed += 1
            continue
        rec = _parse(raw)
        if rec is None:
            malformed += 1
            continue
        file_ids.append(rec.id)
        digest = hashlib.sha256(raw).hexdigest()
        prior = seen.get(rec.id)
        if prior is None:
            seen[rec.id] = (rec, str(path), digest)
        elif prior[2] == digest:
            duplicate_copies += 1
        else:
            conflicting.add(rec.id)
    kept = {sid: v for sid, v in seen.items() if sid not in conflicting}
    conflicting_files = sum(1 for sid in file_ids if sid in conflicting)
    return Snapshot(
        sessions=[kept[sid][0] for sid in sorted(kept)],
        paths={sid: kept[sid][1] for sid in sorted(kept)},
        digests={sid: kept[sid][2] for sid in sorted(kept)},
        files_read=len(paths),
        malformed=malformed,
        duplicate_copies=duplicate_copies,
        conflicting_ids=len(conflicting),
        conflicting_files=conflicting_files,
    )
