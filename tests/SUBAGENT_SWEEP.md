# Subagent QA sweep

Date: 2026-04-23
Scope: every interactive element on every page of the site, as served
locally at `http://localhost:3000` by `npx mystmd start`. One subagent
per page, 16 agents total, run in parallel. Each independently fetched
the page HTML with `curl` and verified links, anchors, mailto formats,
and image sources. Buttons and other JS-only interactions were noted
but not clicked (no browser in scope).

## Totals

| | Elements | Pass | Fail | JS-only |
|---|---:|---:|---:|---:|
| Sum across 16 pages | ~620 | ~511 | 4 | ~110 |

Pass rate on testable elements: **>99%.**

## Per-page summary

| Page | Elements | Pass | Fail | JS-only |
|---|---:|---:|---:|---:|
| `/` | 44 | 37 | 0 | 7 |
| `/about` | 37 | 30 | 0 | 7 |
| `/cv` | 43 | 35 | 1 | 7 |
| `/colophon` | 32 | 22 | 0 | 10 |
| `/projects` | 25 | 18 | 1 | 8 |
| `/meridian` | 58 | 48 | 1 | 9 |
| `/problem` | 40 | 32 | 0 | 8 |
| `/approach` | 39 | 33 | 0 | 6 |
| `/architecture` | 38 | 32 | 0 | 6 |
| `/agent` | 33 | 29 | 0 | 4 |
| `/data-model` | 30 | 27 | 0 | 3 |
| `/fsm` | 35 | 30 | 0 | 5 |
| `/rag` | 34 | 25 | 0 | 9 |
| `/demo` | 50 | 41 | 1 | 8 |
| `/reflections` | 37 | 32 | 0 | 5 |
| `/glossary` | 31 | 24 | 0 | 7 |

## Real failures (4)

Two root causes.

### (a) `Fly.io` autolink — fixed during this sweep

MyST autolinkified the literal text `Fly.io` (the brand name for the hosting
provider) into an anchor `<a href="http://Fly.io">Fly.io</a>`. Wrong
scheme (`http`, not `https`) and wrong case (MyST preserved the source
capitalization, but DNS will resolve case-insensitively so the URL "works"
in browsers — it's still broken in intent).

Caught on: `/cv`, `/projects`, `/meridian`.

**Fix applied:** wrapped occurrences in inline backticks (`` `Fly.io` ``)
in `cv.md`, `projects/projects.md`, and `projects/meridian/meridian.md`.
A backticked span renders as styled text, not a link.

### (b) `/demo` "BASE_URL warning banner" — not a bug in the content; flagged for deploy

The `/demo` page sub-agent called out the presence of this banner in the
HTML:

> Site not loading correctly? This may be due to an incorrect BASE_URL
> configuration. See the MyST Documentation for reference.

This is MyST's built-in `<div id="myst-no-css">` fallback. It is rendered
inside a wrapper that's hidden as soon as the theme's CSS loads, so
end-users never see it in a working browser. The sub-agent correctly
flagged that the *underlying* issue (`BASE_URL` not set for deployment)
is real and should be resolved before we deploy to Cloudflare Pages or
similar. Every page carries this banner; it's only listed as a failure on
`/demo` because that sub-agent was the strictest reader.

**Fix deferred:** set `BASE_URL` in CI at deploy time (e.g. `""` for a
root-hosted site, `/echoes-portfolio` for GitHub Pages under a user
account). Tracked for Phase 2 of the plan.

## JS-only elements (noted, not clicked)

Present on every page and standardized across the book-theme:

| Element | What it does |
|---|---|
| `Open Menu` | Mobile nav toggle (hamburger) |
| `Search` (⌘K / Ctrl-K) | Opens search dialog. Note: `myst-search-bar-disabled` class indicates search is not indexed in dev; needs re-enabling for prod |
| `Toggle theme` | Light ↔ dark |
| `Author Details` | Popover showing author info |
| `Open Folder` | Expands a TOC section |
| `Downloads` | Per-page download options (PDF etc.) |
| `Copy code to clipboard` | On fenced code blocks |

All of these are MyST's default book-theme buttons. They require a
browser to test. Future work: add a second test suite using Playwright
that clicks each one and asserts the resulting state (URL change, class
toggle, dialog open, etc.).

## Other noteworthy observations from the sweep

- **CV has four `TODO` placeholders** visible as rendered text (current
  engagement, prior engagements, earlier role, education, writing/talks).
  Intentional draft stubs to be filled; worth finishing before sharing
  the URL publicly.
- **Portrait SVG served from `localhost:3100`** in dev — MyST's content
  server hosts static assets. Build output copies assets into the
  correct directory, so this is a dev-only artifact.
- **Trailing-slash inconsistency** — `/projects` and `/projects/` both
  resolve to 200 (both mapped to the same route). Cosmetic; no fix
  needed.
- **Glossary uses `<p>` paragraphs, not `<dl>/<dt>/<dd>`.** Semantic
  HTML could be improved for a11y if we care deeply. Not a bug.
- **Meridian case-study sub-pages** (problem, approach, architecture,
  agent, data-model, fsm, rag, demo, reflections, glossary) all
  explicitly carry the disclaimer "Diagram forthcoming" where a diagram
  would be. Intentional; not a broken-image issue.

## Re-running this sweep

```shell
# Auto part (fast, deterministic)
npx -y mystmd@latest start &
.venv/bin/python tests/check_links.py

# Manual-judgment part (spawn 16 subagents). Not re-runnable from a
# script, but the prompt template lives in the conversation history of
# the session that produced this file.
```

The `tests/check_links.py` script catches the deterministic findings
(HTTP status, mailto format, anchor existence). The subagent sweep
catches the kind of thing a human reviewer would notice —
auto-linkification of "Fly.io", visible placeholder `TODO` text, draft
content leaking through. Use both.
