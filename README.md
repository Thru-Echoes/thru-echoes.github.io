# echoes-portfolio

Source of the personal portfolio site for Oliver Muellerklein.
Deployed at <https://thru-echoes.github.io/>.

Built with [MyST (mystmd)](https://mystmd.org/) — a Jupyter-ecosystem
content engine — and hosted as a static site on GitHub Pages.

## Quickstart

```shell
# Live preview at http://localhost:3000
npx mystmd start

# Static build → _build/html
npx mystmd build --html
```

The first `npx` invocation fetches the `mystmd` CLI; later ones are
instant.

## Layout

```
.
├── myst.yml                    top-level MyST config (ToC, theme, nav)
├── index.md                    landing (hero + selected work + skills)
├── projects/
│   └── waggle/waggle.md        case study with embedded diagrams
├── theme/
│   └── overrides.css           minimal CSS overrides on book-theme
├── static/                     portrait, diagram PNGs, favicon (TODO)
├── tests/                      link checker + Playwright UI tests
├── .github/workflows/deploy.yml deploy to GitHub Pages on push to main
└── _build/                     generated; gitignored
```

Only files listed in `myst.yml`'s `project.toc` are rendered as pages.
Planning docs live in `notes/` and iteration screenshots in
`screenshots/`; both are gitignored — they exist locally only.

## Adding a project

1. Create `projects/<slug>/<slug>.md` (note: not `index.md` — see the
   routing-quirk note in `CLAUDE.md`).
2. Add it to `myst.yml`'s `project.toc` under the Projects node.
3. Append the new path to `tests/check_links.py`'s `PAGES` list.
4. Preview with `npx mystmd start`.

## Deploying

Push to `main` → `.github/workflows/deploy.yml` runs MyST's HTML build
and uploads the result to GitHub Pages.

To enable on a fresh repo:

1. Push the repo to GitHub at `Thru-Echoes/thru-echoes.github.io`
   (the repo name itself is what makes this a user-pages site —
   it must match `<username>.github.io`).
2. In the repo settings → Pages → Source, select **GitHub Actions**.
3. Push to `main` (or run the workflow manually from the Actions tab).
   The site appears at `https://thru-echoes.github.io/`.

If you later switch to a custom domain (e.g. `omuellerklein.dev`),
add a `CNAME` file at the repo root with the domain on a single line
and configure DNS at your registrar.

## Stack

- **[mystmd](https://mystmd.org/)** — content engine
- **[book-theme](https://github.com/jupyter-book/myst-theme)** — base theme
- **GitHub Pages** — hosting
- **Mermaid** — pre-rendered to PNG/SVG for the case study

## License

- Content: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- Code (build scripts, theme overrides): MIT
