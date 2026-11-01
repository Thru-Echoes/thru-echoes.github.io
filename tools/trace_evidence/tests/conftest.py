"""Fixtures for the trace_evidence pipeline tests.

Builds throwaway TRACE stores on disk with made-up project names (`acme`,
`clientco`, `collab-a`). Real project keys never appear in fixtures.

Exports:
    make_store: factory fixture returning a function that writes a store.
    session_dict: helper that builds one session JSON object.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tools.trace_evidence.models import ProjectDisplay

TEST_ALLOWLIST: dict[str, ProjectDisplay] = {
    "acme": ProjectDisplay(slug="acme", name="Acme", url="https://example.com/acme"),
    "beta": ProjectDisplay(slug="beta", name="Beta project", url=None),
}

TEST_REGISTRY: dict[str, Any] = {
    "projects": {
        "acme": {"key": "acme", "aliases": ["acme", "collab-a"]},
        "beta": {"key": "beta", "aliases": ["beta"]},
        "clientco": {"key": "clientco", "aliases": ["clientco"]},
    }
}


def event(eid: str, etype: str, **sub: Any) -> dict[str, Any]:
    """Return one event dict with every sub-object slot present (null unless given)."""
    base: dict[str, Any] = {
        "id": eid,
        "timestamp": "2026-03-20T10:00:00Z",
        "session_id": "x",
        "type": etype,
        "actor": {"type": "ai", "id": "ai-assistant", "role": None},
        "tool_call": None,
        "decision": None,
        "annotation": None,
        "state_change": None,
        "contribution": None,
        "context": None,
    }
    base.update(sub)
    return base


def session_dict(
    sid: str,
    project: str,
    created: str = "2026-03-20T10:00:00Z",
    events: list[dict[str, Any]] | None = None,
    tags: list[str] | None = None,
    project_key: str | None = None,
    status: str = "completed",
    ended: str | None = "2026-03-20T11:00:00Z",
    version: str = "0.5.1",
) -> dict[str, Any]:
    """Return one session object shaped like a real TRACE session file."""
    meta: dict[str, Any] = {
        "project": project,
        "experiment_id": None,
        "description": "synthetic",
        "participants": [],
        "environment": {},
        "tags": tags or [],
        "doi": None,
        "custom": {},
    }
    if project_key is not None:
        meta["project_key"] = project_key
    return {
        "context": {},
        "trace_version": version,
        "id": sid,
        "created": created,
        "ended": ended,
        "status": status,
        "metadata": meta,
        "summary": None,
        "events": events or [],
    }


@pytest.fixture
def make_store(tmp_path: Path) -> Callable[..., Path]:
    """Return a writer: make_store(sessions, raw_files=None) -> store dir.

    Side effects: writes files under pytest's tmp_path only.
    """

    def _make(sessions: list[dict[str, Any]], raw_files: dict[str, str] | None = None) -> Path:
        store = tmp_path / "store"
        (store / "sessions").mkdir(parents=True, exist_ok=True)
        (store / "projects.json").write_text(json.dumps(TEST_REGISTRY))
        for i, s in enumerate(sessions):
            (store / "sessions" / f"trace_{i:04d}_{s['id']}.json").write_text(json.dumps(s))
        for name, text in (raw_files or {}).items():
            (store / "sessions" / name).write_text(text)
        return store

    return _make
