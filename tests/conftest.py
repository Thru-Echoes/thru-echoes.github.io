"""
Shared pytest fixtures for the UI test suite.
"""
from __future__ import annotations

import httpx
import pytest

BASE_URL = "http://localhost:3000"


@pytest.fixture(scope="session", autouse=True)
def _require_preview_server() -> None:
    """Fail the whole session fast if the MyST preview server isn't up."""
    try:
        r = httpx.get(BASE_URL, timeout=3.0)
        r.raise_for_status()
    except Exception as e:
        pytest.exit(
            f"FATAL: cannot reach {BASE_URL} — is `npx mystmd start` running?\n  ({e})",
            returncode=2,
        )


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Widen the viewport so desktop nav is visible; disable animations."""
    return {
        **browser_context_args,
        "viewport": {"width": 1440, "height": 900},
        "reduced_motion": "reduce",
    }


@pytest.fixture(scope="session")
def base_url() -> str:
    """Scope=session to match pytest-base-url's expectations."""
    return BASE_URL
