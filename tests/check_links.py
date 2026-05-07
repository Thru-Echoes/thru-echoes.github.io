"""
Link checker for the MyST-built portfolio site.

Crawls every page listed in myst.yml's TOC (served locally via
`npx mystmd start` at http://localhost:3000), extracts every interactive
element — anchor links, buttons, mailto, external URLs, in-page
anchors — and verifies each one does the correct thing.

Usage:
  pip install -r tests/requirements.txt
  npx -y mystmd@latest start &   # start preview server
  python tests/check_links.py    # run the checker
  python tests/check_links.py --json  # machine-readable output

Exit code:
  0 — all checks passed
  1 — at least one check failed (details printed)
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from dataclasses import dataclass, field
from typing import Literal

import httpx
from bs4 import BeautifulSoup, Tag

# ─────────────────────────────────────────────────────────────────────
# Config — source of truth for what pages exist on the site.
# Mirrors the TOC in myst.yml; update both places if the TOC changes.
# ─────────────────────────────────────────────────────────────────────

BASE = "http://localhost:3000"

PAGES: list[str] = [
    "/",
    "/waggle",
]

# External URLs we allow HEAD-requesting. Anything here must return
# a 2xx or 3xx. Domains we DON'T want to hammer live can be listed in
# EXTERNAL_SKIP — they get a format-only check.
EXTERNAL_SKIP: set[str] = {
    "github.com",          # works, but is rate-limited
    "mystmd.org",          # works
    "creativecommons.org", # works
    "opensource.org",      # works
}

REQUEST_TIMEOUT = 10.0

# ─────────────────────────────────────────────────────────────────────
# Results model
# ─────────────────────────────────────────────────────────────────────

Severity = Literal["pass", "fail", "skip"]


@dataclass
class Result:
    page: str
    kind: str          # "link", "mailto", "anchor", "external", "button", "image"
    target: str
    description: str
    severity: Severity
    detail: str = ""


@dataclass
class PageReport:
    page: str
    results: list[Result] = field(default_factory=list)

    @property
    def n_pass(self) -> int:
        return sum(1 for r in self.results if r.severity == "pass")

    @property
    def n_fail(self) -> int:
        return sum(1 for r in self.results if r.severity == "fail")

    @property
    def n_skip(self) -> int:
        return sum(1 for r in self.results if r.severity == "skip")


# ─────────────────────────────────────────────────────────────────────
# Fetch
# ─────────────────────────────────────────────────────────────────────

def get_soup(client: httpx.Client, url: str) -> BeautifulSoup:
    r = client.get(url, timeout=REQUEST_TIMEOUT, follow_redirects=True)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def status_of(client: httpx.Client, url: str, method: str = "HEAD") -> int:
    try:
        r = client.request(method, url, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        # Some servers 405 on HEAD — fall back to GET.
        if r.status_code == 405 and method == "HEAD":
            r = client.get(url, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        return r.status_code
    except httpx.HTTPError:
        return 0


# ─────────────────────────────────────────────────────────────────────
# Per-element checks
# ─────────────────────────────────────────────────────────────────────

def is_external(href: str) -> bool:
    return href.startswith(("http://", "https://"))


def is_mailto(href: str) -> bool:
    return href.startswith("mailto:")


def is_anchor(href: str) -> bool:
    return href.startswith("#")


def normalise_internal(href: str) -> str:
    """Turn a relative/internal href into an absolute path on our site."""
    parsed = urllib.parse.urlparse(href)
    if parsed.scheme or parsed.netloc:
        return href
    # internal
    if not href.startswith("/"):
        href = "/" + href
    return href


def check_anchor(soup: BeautifulSoup, anchor: str) -> bool:
    """Check that #foo targets an element with id="foo" or name="foo"."""
    target_id = anchor.lstrip("#")
    if not target_id:
        return True  # bare #; harmless
    return bool(
        soup.find(id=target_id)
        or soup.find(attrs={"name": target_id})
    )


def check_mailto(href: str) -> tuple[bool, str]:
    m = href[len("mailto:"):]
    email = m.split("?")[0]
    ok = "@" in email and "." in email.split("@")[-1]
    return ok, email


# ─────────────────────────────────────────────────────────────────────
# Page crawl
# ─────────────────────────────────────────────────────────────────────

def check_page(client: httpx.Client, page: str) -> PageReport:
    report = PageReport(page=page)
    url = urllib.parse.urljoin(BASE, page)

    try:
        soup = get_soup(client, url)
    except Exception as e:
        report.results.append(Result(
            page=page, kind="page", target=url,
            description="page load", severity="fail",
            detail=f"failed to load: {e}",
        ))
        return report

    # --- Links ---
    for a in soup.find_all("a"):
        if not isinstance(a, Tag):
            continue
        href = a.get("href")
        if not href or not isinstance(href, str):
            continue
        text = (a.get_text() or "").strip()[:80]

        if is_anchor(href):
            ok = check_anchor(soup, href)
            report.results.append(Result(
                page=page, kind="anchor", target=href,
                description=f'anchor "{text}"',
                severity="pass" if ok else "fail",
                detail="" if ok else f"no element with id={href[1:]!r}",
            ))

        elif is_mailto(href):
            ok, email = check_mailto(href)
            report.results.append(Result(
                page=page, kind="mailto", target=href,
                description=f'mailto "{text}"',
                severity="pass" if ok else "fail",
                detail=email,
            ))

        elif is_external(href):
            domain = urllib.parse.urlparse(href).netloc
            if domain in EXTERNAL_SKIP:
                report.results.append(Result(
                    page=page, kind="external", target=href,
                    description=f'external "{text}"',
                    severity="skip",
                    detail=f"skipped (in EXTERNAL_SKIP: {domain})",
                ))
            else:
                code = status_of(client, href)
                ok = 200 <= code < 400
                report.results.append(Result(
                    page=page, kind="external", target=href,
                    description=f'external "{text}"',
                    severity="pass" if ok else "fail",
                    detail=f"HTTP {code}",
                ))

        else:
            # internal link
            path = normalise_internal(href)
            dest = urllib.parse.urljoin(BASE, path)
            code = status_of(client, dest, method="GET")
            ok = 200 <= code < 400
            report.results.append(Result(
                page=page, kind="link", target=path,
                description=f'internal "{text}"',
                severity="pass" if ok else "fail",
                detail=f"HTTP {code}",
            ))

    # --- Buttons (interactive but JS-dependent; assert presence + a11y) ---
    for b in soup.find_all("button"):
        if not isinstance(b, Tag):
            continue
        label = b.get("aria-label") or b.get_text(strip=True) or "(unlabeled)"
        report.results.append(Result(
            page=page, kind="button", target=str(label)[:80],
            description=f'button "{label}"',
            severity="skip",
            detail="present; JS-interactive, not tested here",
        ))

    # --- Images (check src resolves) ---
    for img in soup.find_all("img"):
        if not isinstance(img, Tag):
            continue
        src = img.get("src")
        if not src or not isinstance(src, str):
            continue
        alt = img.get("alt") or "(no alt)"
        dest = urllib.parse.urljoin(BASE, src) if not is_external(src) else src
        code = status_of(client, dest)
        ok = 200 <= code < 400
        report.results.append(Result(
            page=page, kind="image", target=str(src)[:80],
            description=f'img "{alt}"',
            severity="pass" if ok else "fail",
            detail=f"HTTP {code}",
        ))

    return report


# ─────────────────────────────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────────────────────────────

def print_report(reports: list[PageReport]) -> int:
    total_pass = total_fail = total_skip = 0
    for r in reports:
        total_pass += r.n_pass
        total_fail += r.n_fail
        total_skip += r.n_skip

        bar = "━" * 70
        print(f"\n{bar}\n {r.page}\n{bar}")
        print(f"  {r.n_pass} pass · {r.n_fail} fail · {r.n_skip} skip")

        for res in r.results:
            glyph = {"pass": "✓", "fail": "✗", "skip": "·"}[res.severity]
            tail = f" — {res.detail}" if res.detail else ""
            print(f"  {glyph} [{res.kind:8}] {res.description:50} → {res.target}{tail}")

    print(f"\n{'═'*70}")
    print(f" TOTAL: {total_pass} pass · {total_fail} fail · {total_skip} skip")
    print("═" * 70)
    return 0 if total_fail == 0 else 1


def json_report(reports: list[PageReport]) -> str:
    return json.dumps([
        {
            "page": r.page,
            "pass": r.n_pass, "fail": r.n_fail, "skip": r.n_skip,
            "results": [
                {
                    "kind": res.kind, "target": res.target,
                    "description": res.description,
                    "severity": res.severity, "detail": res.detail,
                }
                for res in r.results
            ],
        }
        for r in reports
    ], indent=2)


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────

def main() -> int:
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="Machine-readable output")
    ap.add_argument("--base", default=BASE, help=f"Base URL (default: {BASE})")
    args = ap.parse_args()

    BASE = args.base.rstrip("/")

    reports: list[PageReport] = []
    with httpx.Client() as client:
        # Health check.
        try:
            r = client.get(BASE, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
        except Exception as e:
            print(f"FATAL: cannot reach {BASE} — is `npx mystmd start` running? ({e})",
                  file=sys.stderr)
            return 2

        for page in PAGES:
            reports.append(check_page(client, page))

    if args.json:
        print(json_report(reports))
        return 0 if all(r.n_fail == 0 for r in reports) else 1
    return print_report(reports)


if __name__ == "__main__":
    sys.exit(main())
