# Tests

Re-runnable site verification. Two layers — each catches what the other
misses.

| Suite | What it checks | Needs a browser? |
|---|---|---|
| `check_links.py` | Links, anchors, mailto format, image `src`, external URLs. Static HTML crawl. | No |
| `check_ui.py`    | Theme toggle, TOC expand/collapse, author popover, downloads menu, copy-to-clipboard, mobile nav, search state, keyboard shortcuts. | Yes (headless Chromium via Playwright) |

Both run against a running `npx mystmd start` preview at
`http://localhost:3000`.

## One-time setup

```shell
# Python deps
python3 -m venv .venv
.venv/bin/pip install -r tests/requirements.txt

# Playwright browsers (~180 MB, once)
.venv/bin/playwright install chromium
```

## Run the static link checker

```shell
# Start the preview server in another terminal
npx -y mystmd@latest start

# In this terminal
.venv/bin/python tests/check_links.py
# Machine-readable JSON:
.venv/bin/python tests/check_links.py --json > /tmp/link-report.json
```

**Exit codes:** `0` all passed · `1` at least one fail · `2` server
unreachable.

## Run the UI interaction suite

```shell
# Start the preview server in another terminal
npx -y mystmd@latest start

# Run the suite
.venv/bin/pytest tests/check_ui.py -v

# Just one test class
.venv/bin/pytest tests/check_ui.py::TestThemeToggle -v

# Headed mode (watch it run)
.venv/bin/pytest tests/check_ui.py --headed

# Slow-motion for debugging
.venv/bin/pytest tests/check_ui.py --headed --slowmo=500
```

## What each suite asserts

### `check_links.py`

- Every `<a href>` in every page's HTML points somewhere valid:
  - internal (`/...`) → HTTP 200 via GET
  - external (`https://...`) → 2xx/3xx via HEAD, *or* in `EXTERNAL_SKIP`
  - mailto → well-formed email
  - anchor (`#foo`) → element with `id="foo"` exists on the same page
- Every `<img src>` resolves.
- Every `<button>` is noted but *not* clicked.

Rate-sensitive hosts (GitHub, mystmd.org, license providers) are
format-checked but not fetched. Edit `EXTERNAL_SKIP` at the top of
`check_links.py` to change this.

### `check_ui.py`

One test class per interaction surface. Each test:

1. Navigates to a representative page.
2. Clicks / keys on the element.
3. Asserts a specific post-condition — a class flip on `<html>`, a
   dialog appearing, a menu opening, etc.
4. Gracefully `pytest.skip`s if the element isn't present on that page
   (the site is young; some chrome varies by route).

The search-bar test has two arms: if MyST renders the search button in
disabled state (dev default), the test skips with an explanatory
message; if the button is enabled, the test clicks it and expects a
dialog to appear.

## What neither suite covers (yet)

- **Accessibility audit.** `axe-core` via Playwright would plug in
  here; not yet wired.
- **Visual regression.** Screenshot diffs aren't captured.
- **Link text semantics.** "Does the label describe the destination?"
  is a judgment call that a subagent sweep catches (see
  `SUBAGENT_SWEEP.md`) but the automated suite doesn't.
- **PDF export.** `myst build --pdf` isn't tested here. Add when we
  commit to PDF downloads.

## `SUBAGENT_SWEEP.md`

A one-shot QA sweep performed on 2026-04-23 by 16 parallel
Claude-Code subagents (one per page). They independently enumerated
and tested every interactive element, with human-level judgment about
whether content was coherent and whether placeholder text was visible.
Not re-runnable from a script, but the aggregated findings are
captured in `SUBAGENT_SWEEP.md` for the record.

## CI wiring (future)

A `.github/workflows/test.yml` step:

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-node@v4
  with: { node-version: "20" }
- uses: actions/setup-python@v5
  with: { python-version: "3.12" }
- run: pip install -r tests/requirements.txt
- run: playwright install --with-deps chromium
- run: npx -y mystmd@latest start &
- run: sleep 5 && python tests/check_links.py
- run: pytest tests/check_ui.py -v
```
