# echoes-portfolio: Claude Code instructions

Personal portfolio site for **Oliver Muellerklein**, built with [MyST](https://mystmd.org)
(Jupyter Book 2). Static site, deployed to GitHub Pages at
`https://thru-echoes.github.io` (see Deploy below). Public repo, public site.

> This file is the public *how*: build, test, deploy, routing, and copy rules.
> Planning notes and private context live in the maintainer's local workspace,
> outside this repo.

---

## Scope (read first)

This repo is **the portfolio site itself**, not the projects it links to.

- **In scope:** site structure, copy, theme, build pipeline, deploy config, the
  test suites in `tests/`, project-page templates.
- **Out of scope:** building, hosting, or maintaining the projects the site
  features. Each lives in its own repo. This site links *out* to them; it
  doesn't contain their code.

If a request appears to blur this line, ask before scope-creeping. The user has
flagged scope drift as a recurring failure mode in this project.

---

## Voice & copy guardrails

Any prose that ends up on the rendered site, or in PRs, or in user-facing copy,
must follow this rubric. Internal commit messages and code comments are exempt.

**Patterns to use:**
- Lead with the claim, then evidence, then implication. No lead-up.
- Active first-person ownership for things you did (`I built`, `I shipped`).
  Never passive voice for ownership.
- Hedge premises (`I think`, `unless I'm mistaken`), not conclusions.
  Conclusions stay direct.
- Prefer colons over em dashes. Use `:` for "Title: subtitle" patterns
  and list intros, parentheses for parenthetical asides, and a plain
  hyphen `-` only where neither flows. No em dashes (`—`) in site copy
  or in PR / commit prose.
- Site copy stays in formal register. Lowercase / Slack-casual is from chat
  only and does not transfer.

**Anti-patterns, never write these:**
- AI filler: *"Happy to talk about"*, *"I'd be happy to"*, *"Hope that helps"*,
  *"Feel free to"*, *"Let me know if…"*, *"part of the thesis"*.
- *"obviously"*, *"clearly"*, *"of course"* preceding non-obvious points.
- Stacked adverbs (*"really truly deeply"*); business-speak (*"per our
  conversation"*, *"circling back"*, *"at this time"*).
- Self-deprecation. Emoji unless explicitly requested.
- Generic enthusiasm in CTAs.

---

## Framing

The writing target is "senior engineer / founding team material," not
"general visitor."

**Lead with dev.** Hero, project order, and CTAs all foreground full-stack
agentic-systems engineering and MCP tooling. PhD identity is a *credibility
layer underneath*, not the headline.

- **Selected work:** **Waggle** (agentic MCP CRM, flagship) and **TRACE**
  (custom MCP server, framed as product not paper), plus the TRACE evidence
  page. Don't add other projects without explicit go-ahead.
- About: "I build agentic systems and MCP tooling. Currently finishing a PhD
  applying these methods to environmental and social-science problems."
- CTA: founding-team / senior engineering roles in agentic systems for
  sustainability / ESG / environmental applications.
- Waggle is a clean-room implementation. Never describe it as an
  "anonymized version of client work," and never name clients.
- Lead with dev, not research. If earlier research-first framing shows up in
  copy, revise it out.

---

## Stack

- **mystmd**: content engine
- **book-theme**: base, with `theme/overrides.css` (≤300 lines, custom CSS only)
- **Mermaid**: diagrams render live from `:::{mermaid}` blocks in the page
  source; PNG renders under `static/diagrams/` back the "View fullscreen" links
- Static HTML output → `_build/html/`
- Tests: Python venv at `.venv/`; deps in `tests/requirements.txt`

## Quickstart

```shell
# Live preview at http://localhost:3000
NODE_OPTIONS="--no-deprecation" npx -y mystmd@1.12.0 start

# Static build
npx -y mystmd@1.12.0 build --html

# Tests (preview server must be running)
.venv/bin/python tests/check_links.py        # static link/anchor crawler
.venv/bin/pytest tests/check_ui.py -v        # JS interactions via Playwright
```

`NODE_OPTIONS="--no-deprecation"` silences a `DEP0169` warning that originates
upstream in `node-fetch@2` (bundled inside `myst-theme`'s `book-theme`). Not
actionable in this repo.

---

## Repo layout

```
.
├── myst.yml                    project config + ToC
├── index.md                    single-page site (hero, selected work, skills)
├── projects/
│   └── waggle/waggle.md         single-page case study with embedded diagrams
├── theme/overrides.css
├── static/                     portraits, hero image; diagrams/waggle/ PNG renders
├── tests/                      check_links.py, check_ui.py, conftest.py,
│                               SUBAGENT_SWEEP.md, README.md
└── .github/workflows/deploy.yml  build + deploy to GitHub Pages on push to main
```

Gitignored, never committed: `_build/`, `.venv/`, `screenshots/`, and any
local `notes/`, `.claude/`, or `.mcp.json`.

## Routing quirk

MyST's default routing **flattens** the file tree: every page lands at `/<basename>`,
not at the nested path. Two consequences worth knowing:

- `projects/waggle/waggle.md` lives at `/waggle`, not `/projects/waggle/`.
- Index pages were renamed away from `index.md` to avoid `/index-1`, `/index-2`
  deduplication collisions. There is no project landing called `index.md` outside
  the site root.

Use absolute paths in internal links: `[Meridian](/meridian)`, not relative.

## Adding a project

1. Create `projects/<slug>/<slug>.md` (the project landing) plus any of
   `problem.md`, `approach.md`, `architecture.md`, `outcomes.md`, `reflections.md`.
   **Do not name the landing `index.md`** (see routing quirk).
2. Add the new files to `myst.yml`'s `project.toc` under the Projects branch.
3. Restart `mystmd start` so the new TOC entries register.
4. Append the new path to `tests/check_links.py`'s `PAGES` list.
5. Run both test layers before considering the page shipped.

## Test conventions

- **`check_links.py`**: deterministic; HTTP, anchor existence, mailto format,
  image src, external URLs (rate-sensitive hosts skipped via `EXTERNAL_SKIP`).
- **`check_ui.py`**: Playwright + headless Chromium; theme toggle, popovers,
  TOC expand, mobile nav, copy-code, Escape-closes. Skips cleanly when an
  element is absent on a given page.
- **`SUBAGENT_SWEEP.md`**: frozen one-shot QA from 16 parallel subagents
  (2026-04-23). Reference, not re-runnable from a script.

Run **both** layers when touching site copy or structure. Both expect a
running preview server.

---

## Deliberately not in this file

- Detailed voice profile, role background, planning notes, and decision
  rationale: kept in the maintainer's local workspace, not in this repo.
- Custom domain: still open. Don't wire one up without explicit go-ahead.

## Deploy (read before any push)

`.github/workflows/deploy.yml` builds the site and deploys it to GitHub Pages
(`https://thru-echoes.github.io`) on **every push to `main`**. GitHub Pages has
no private pages: anything merged to `main` is public, and a page left out of
`nav` is still reachable by URL. Work on a feature branch and open a PR; never
push to `main` directly. CI runs `npx -y mystmd@latest build --html`, so that
command must pass locally before a PR.

## TRACE evidence page

`/trace-evidence` (`projects/trace/trace-evidence.md`) shows aggregate counts
from the maintainer's local TRACE store. Nothing on that page is hand-typed:

- `tools/trace_evidence/` reads the store **read-only** and writes the 8 files
  listed in `PUBLIC_FILES`: `static/evidence/evidence.json`, four light/dark
  SVG charts, and three `projects/trace/_evidence_*.md` fragments that the
  page includes. Regenerate them all at once; never edit them by hand.
- The allowlist (registry key -> public slug and display name) and every
  exclusion diagnostic are private inputs/outputs kept outside the repo, so
  unapproved project names never appear in committed code.
- Regenerate (local only):

  ```shell
  .venv/bin/python -m tools.trace_evidence --store ~/.trace \
      --release-map <private>/release-map.json --private-dir <private>
  EVIDENCE_RELEASE=1 .venv/bin/pytest tools/trace_evidence/tests -q
  ```

- CI (`.github/workflows/ci.yml`) runs the store-independent tests: committed
  outputs must equal a re-render of the committed `evidence.json`.
- Test fixtures use made-up project names only.

## TRACE

Work on this site is logged with [TRACE](https://github.com/Thru-Echoes/TRACE)
(decisions, contributions, and corrections in AI-assisted development). The
TRACE MCP config and hooks live in the maintainer's local workspace, outside
this repo: `.mcp.json` holds an absolute local path, and `.claude/` is
machine-local. `.gitignore` keeps both out of the repo if either appears here.
