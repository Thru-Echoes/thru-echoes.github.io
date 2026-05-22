# echoes-portfolio: Claude Code instructions

Personal portfolio site for **Oliver Muellerklein**, built with [MyST](https://mystmd.org)
(Jupyter Book 2). Static site, intended to be hosted free on GitHub Pages or
Cloudflare Pages. Public repo, public site.

> Long-form context, decisions, and rationale live in
> [`notes/PORTFOLIO_PLAN.md`](notes/PORTFOLIO_PLAN.md) (local only, gitignored).
> Read that for *why*; this file is *how*.

---

## Scope (read first)

This repo is **the portfolio site itself**, not the projects it links to.

- **In scope:** site structure, copy, theme, build pipeline, deploy config, the
  test suites in `tests/`, project-page templates.
- **Out of scope:** building, hosting, or maintaining the projects the site
  features. Meridian / Waggle, TRACE, REAP, the Hye-In paper, the AI-art paper,
  etc. each live in their own repos elsewhere on this machine. This site links
  *out* to them; it doesn't contain their code.

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
- Site copy stays in formal-register (anchor: your email-to-PJ).
  Lowercase / Slack-casual is from chat only and does not transfer.

**Anti-patterns, never write these:**
- AI filler: *"Happy to talk about"*, *"I'd be happy to"*, *"Hope that helps"*,
  *"Feel free to"*, *"Let me know if…"*, *"part of the thesis"*.
- *"obviously"*, *"clearly"*, *"of course"* preceding non-obvious points.
- Stacked adverbs (*"really truly deeply"*); business-speak (*"per our
  conversation"*, *"circling back"*, *"at this time"*).
- Self-deprecation. Emoji unless explicitly requested.
- Generic enthusiasm in CTAs.

The full verbatim-grounded voice profile is in this user's local memory at
`memory/user_voice.md` (loaded automatically via `MEMORY.md`). When drafting
copy, treat it as the rubric, not as inspiration.

---

## Audience and framing: read carefully

This portfolio's **first audience** is a private dev-skills evaluation by a
specific person who is gauging you as a technical co-founder for an ESG
startup raise. Public site, but the writing target is "senior engineer / founding
team material," not "general visitor."

**Lead with dev.** Hero, project order, and CTAs all foreground full-stack
agentic-systems engineering and MCP tooling. PhD identity is a *credibility
layer underneath*, not the headline.

- **v1 selected-work scope** (ship fast): **Waggle** (agentic MCP CRM,
  flagship) and **TRACE** (custom MCP server, framed as product not paper).
  **Only these two.** Deferred to v2+: Corp-Sus Report Extractor, REAP,
  trace-meeting-recorder, all papers and publications. Don't add or
  reintroduce deferred items without explicit go-ahead.
- About: "I build agentic systems and MCP tooling. Currently finishing a PhD
  applying these methods to environmental and social-science problems."
- CTA: founding-team / senior engineering roles in agentic systems for
  sustainability / ESG / environmental applications. **Do not name** the
  specific private opportunity, the company, or the people involved.

**ChemMasters is under NDA: never name it on the site.** Waggle is the
public-facing rebuild; describe it as a clean-room implementation, not an
"anonymized version of client work."

A previous draft of this file said *"lead with research."* That was wrong for
this audience. If you see that earlier framing in copy, revise it out.

Full role background and reasoning: `memory/user_role.md`.

---

## Stack

- **mystmd**: content engine
- **book-theme**: base, with `theme/overrides.css` (≤300 lines, custom CSS only)
- **Mermaid**: diagrams, pre-rendered to PNG/SVG; sources kept alongside renders
- Static HTML output → `_build/html/`
- Tests: Python venv at `.venv/`; deps in `tests/requirements.txt`

## Quickstart

```shell
# Live preview at http://localhost:3000
NODE_OPTIONS="--no-deprecation" npx -y mystmd@latest start

# Static build
npx -y mystmd@latest build --html

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
├── static/                     portrait placeholder; future favicon, OG card
└── tests/                      check_links.py, check_ui.py, conftest.py,
                                SUBAGENT_SWEEP.md, README.md
```

Local-only working dirs (gitignored, exist on your machine but not in the repo):
- `notes/`: `PORTFOLIO_PLAN.{md,pdf}`, `PORTFOLIO_PLAN_ARCHITECTURE.{mmd,png}`, `.pdf-header.tex`
- `screenshots/`: landing/project iteration snapshots

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

- Detailed voice patterns, verbatim quotes, full role/career background: those
  live in `memory/` and load automatically.
- Long-form planning, alternatives considered, decision rationale:
  `notes/PORTFOLIO_PLAN.md` (local only, gitignored).
- Deploy, CI, domain, GitHub repo creation: all open. Don't auto-wire any of
  these without explicit go-ahead.

<!-- trace-mcp:claude-code -->

## TRACE Audit Protocol (v0.4.1+)

This project uses [TRACE](https://github.com/Thru-Echoes/TRACE) for transparent
documentation of AI-human collaboration. The TRACE MCP server is configured in
`.mcp.json` and enforced via `.claude/hooks/`.

**Absolute rule**: Never fabricate, falsify, or retroactively alter TRACE
data. A sparse honest record beats a dense fabricated one.

**Session lifecycle**

- **Start** a TRACE session at the beginning of any multi-step workflow.
- **End** with a summary when the workflow is complete. Review the
  Attribution Audit returned by `trace_end_session` before closing.

**What to log**

- **Decisions** (propose BEFORE acting, resolve when the human responds).
  - **Proposer Identity Rule (v0.4.1, spec §3.6)**: set `proposed_by` to the
    actor who authored the proposal *content* (whose words populate
    `description`), not the speaker of the resolving directive.
    Question→AI-proposal→accept means `proposed_by=ai`, `resolved_by=human`.
- **Corrections** when a participant catches a mistake.
  - If the corrected entity is not a TRACE event (subagent output, tool
    result, external claim), use a URI-form reference per spec §3.7.1:
    `external:<uri>` (universal fallback), `jsonl:<path>#L<line>`,
    `subagent:<id>`, or `tool-result:<id>`. `related_event_ids` is NOT
    for the correction relationship.
- **Discoveries (v0.4.1, `category="discovery"`)**: non-trivial findings
  from autonomous work — log AT THE MOMENT of discovery, not in a
  post-hoc summary.
- **Contributions** — one per artifact, with `direction` (who had the idea)
  and `execution` (who did the work). Always set `conversation_snippet`
  to the relevant user message (~200 chars). If no user message
  motivated the event, use the explicit absence marker
  `<autonomous-stretch>` (no user turn since the last decision) or
  `<no recent user message>` (general fallback) rather than omitting.
  Silent omission is a v0.4.1 protocol violation per spec §3.4.1.
- **Subagent dispatches** when their outcome is summarized by a
  contribution — `trace_log_tool_call(host="internal", server="claude-code",
  parent_event_id=...)` per spec §3.5. Skip routine file reads, greps,
  or TRACE's own calls.

Full protocol, including attribution rules, URI-form references, and
worked examples, lives at the [TRACE specification](https://github.com/Thru-Echoes/TRACE/blob/main/docs/specification.md).

<!-- /trace-mcp:claude-code -->
