"""Render the evidence charts as static SVG, one file per theme.

Palettes are the validated dataviz reference slots (categorical, adjacent-pair
CVD-checked against the site's light #fcfaf7 and dark #1a1816 surfaces).
Charts are images, so identity never relies on color alone: every chart has
a legend, the contribution chart carries direct percentage labels and an
n per bar, and the page shows the same numbers as a table.

Exports:
    CONTRIB_CATEGORIES
    get_contrib_category(pair_key) -> str
    get_weekly_svg(report, theme) -> str
    get_contrib_svg(report, theme) -> str

No side effects.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Literal
from xml.sax.saxutils import escape

from .models import EvidenceReport

Theme = Literal["light", "dark"]

_THEME = {
    "light": {
        "surface": "#fcfaf7",
        "text": "#1c1917",
        "muted": "#57534e",
        "grid": "#e7e2da",
        "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"],
        "contrib": ["#008300", "#6250d6", "#e34948", "#a8a29e", "#d6d3d1"],
        "on_mark": "#ffffff",
    },
    "dark": {
        "surface": "#1a1816",
        "text": "#f5f4f1",
        "muted": "#b4afa8",
        "grid": "#3a3632",
        "series": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181"],
        "contrib": ["#008300", "#9085e9", "#e66767", "#78716c", "#57534e"],
        "on_mark": "#ffffff",
    },
}
_FONT = "Inter, Helvetica Neue, Segoe UI, system-ui, sans-serif"

CONTRIB_CATEGORIES: list[str] = [
    "Human idea, AI built",
    "Shared idea, AI built",
    "AI idea, AI built",
    "Human or shared execution",
    "Not recorded",
]


def get_contrib_category(pair_key: str) -> str:
    """Map a 'direction→execution' key to one of CONTRIB_CATEGORIES."""
    direction, _, execution = pair_key.partition("→")
    if "unknown" in (direction, execution):
        return "Not recorded"
    if execution in ("human", "collaborative"):
        return "Human or shared execution"
    return {"human": "Human idea, AI built", "collaborative": "Shared idea, AI built"}.get(direction, "AI idea, AI built")


def _svg_open(w: int, h: int, title: str, desc: str, theme: Theme) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-labelledby="t d" font-family="{_FONT}">'
        f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>'
        f'<rect width="{w}" height="{h}" fill="{_THEME[theme]["surface"]}"/>'
    )


def _top_rounded(x: float, y: float, w: float, h: float, r: float) -> str:
    """Path for a rect with only the top corners rounded (data end)."""
    r = max(0.0, min(r, w / 2, h))
    return (
        f'M{x:.1f},{y + h:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} '
        f'H{x + w - r:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} V{y + h:.1f} Z'
    )


def _nice_max(v: int) -> int:
    for step in (1, 2, 5, 10, 20, 25, 50, 100):
        top = -(-v // step) * step
        if top / step <= 6:
            return max(top, step)
    return v


def get_weekly_svg(report: EvidenceReport, theme: Theme) -> str:
    """Stacked bars: recorded session starts per ISO week, one series per project."""
    t = _THEME[theme]
    w, h, ml, mr, mt, mb = 720, 330, 44, 12, 64, 40
    pw, ph = w - ml - mr, h - mt - mb
    weeks = report.weekly
    slugs = [p.key for p in report.projects]
    names = {p.key: p.name for p in report.projects}
    color = {s: t["series"][i % len(t["series"])] for i, s in enumerate(slugs)}
    totals = [sum(r.counts.values()) for r in weeks]
    ymax = _nice_max(max(totals, default=1) or 1)
    bw = pw / max(len(weeks), 1)
    parts = [
        _svg_open(
            w,
            h,
            "Recorded session starts by week",
            f"Stacked weekly counts of recorded TRACE session starts for {len(slugs)} projects, "
            f"{weeks[0].week if weeks else ''} to {weeks[-1].week if weeks else ''}. The final week is partial.",
            theme,
        )
    ]
    # legend (two rows max)
    lx, ly = ml, 18
    for s in slugs:
        label = escape(names[s])
        parts.append(f'<rect x="{lx}" y="{ly - 9}" width="10" height="10" rx="2" fill="{color[s]}"/>')
        parts.append(f'<text x="{lx + 15}" y="{ly}" font-size="12" fill="{t["text"]}">{label}</text>')
        lx += 15 + int(6.4 * len(names[s])) + 22
        if lx > w - 160:
            lx, ly = ml, ly + 18
    # grid + y ticks
    step = ymax // 4 if ymax % 4 == 0 else (ymax // 5 if ymax % 5 == 0 else ymax)
    for v in range(0, ymax + 1, max(step, 1)):
        y = mt + ph - ph * v / ymax
        parts.append(f'<line x1="{ml}" x2="{w - mr}" y1="{y:.1f}" y2="{y:.1f}" stroke="{t["grid"]}" stroke-width="1"/>')
        parts.append(f'<text x="{ml - 6}" y="{y + 4:.1f}" font-size="11" text-anchor="end" fill="{t["muted"]}">{v}</text>')
    # bars
    for i, row in enumerate(weeks):
        x = ml + i * bw + 1.5
        bwi = bw - 3
        y_cursor = mt + ph
        stack = [(s, row.counts.get(s, 0)) for s in slugs if row.counts.get(s, 0)]
        for j, (s, c) in enumerate(stack):
            seg = ph * c / ymax
            y_top = y_cursor - seg
            gap = 1.0 if j < len(stack) - 1 else 0.0
            if j == len(stack) - 1:
                parts.append(f'<path d="{_top_rounded(x, y_top, bwi, seg, 3)}" fill="{color[s]}"/>')
            else:
                parts.append(f'<rect x="{x:.1f}" y="{y_top + gap:.1f}" width="{bwi:.1f}" height="{max(seg - gap, 0.5):.1f}" fill="{color[s]}"/>')
            y_cursor = y_top
    # month ticks on the first week of each month
    seen: set[tuple[int, int]] = set()
    for i, row in enumerate(weeks):
        y_, wk = row.week.split("-W")
        monday = date.fromisocalendar(int(y_), int(wk), 1)
        key = (monday.year, monday.month)
        if key in seen:
            continue
        seen.add(key)
        x = ml + i * bw + bw / 2
        parts.append(f'<text x="{x:.1f}" y="{h - mb + 18}" font-size="11" text-anchor="middle" fill="{t["muted"]}">{monday.strftime("%b")}</text>')
    parts.append(f'<line x1="{ml}" x2="{w - mr}" y1="{mt + ph}" y2="{mt + ph}" stroke="{t["muted"]}" stroke-width="1"/>')
    parts.append(f'<text x="{ml}" y="{h - 6}" font-size="11" fill="{t["muted"]}">Week of session start (UTC). Final week partial.</text>')
    parts.append("</svg>")
    return "".join(parts) + "\n"


def get_contrib_svg(report: EvidenceReport, theme: Theme) -> str:
    """One 100% stacked bar per project (plus all projects) of contribution records."""
    t = _THEME[theme]
    rows = [*report.projects, report.totals]
    w, row_h, ml, mr, mt = 720, 46, 210, 16, 58
    h = mt + row_h * len(rows) + 30
    pw = w - ml - mr
    parts = [
        _svg_open(
            w,
            h,
            "Share of recorded contribution records by direction and execution",
            "For each project, the share of contribution records by who had the idea (direction) and who "
            "did the work (execution). Shares of records, not of effort or code. n is the record count.",
            theme,
        )
    ]
    present: Counter[str] = Counter()
    for k, v in report.totals.contributions_by_pair.items():
        present[get_contrib_category(k)] += v
    lx, ly = 16, 20
    for i, cat in enumerate(CONTRIB_CATEGORIES):
        if not present.get(cat):
            continue
        parts.append(f'<rect x="{lx}" y="{ly - 9}" width="10" height="10" rx="2" fill="{t["contrib"][i]}"/>')
        parts.append(f'<text x="{lx + 15}" y="{ly}" font-size="12" fill="{t["text"]}">{escape(cat)}</text>')
        lx += 15 + int(6.4 * len(cat)) + 22
        if lx > w - 150:
            lx, ly = 16, ly + 18
    for r, p in enumerate(rows):
        y = mt + r * row_h
        bold = ' font-weight="600"' if p.key == "all" else ""
        parts.append(f'<text x="{ml - 10}" y="{y + 15}" font-size="12" text-anchor="end" fill="{t["text"]}"{bold}>{escape(p.name)}</text>')
        parts.append(f'<text x="{ml - 10}" y="{y + 30}" font-size="11" text-anchor="end" fill="{t["muted"]}">n = {p.contributions:,}</text>')
        if p.contributions == 0:
            parts.append(f'<text x="{ml}" y="{y + 22}" font-size="11" fill="{t["muted"]}">No recorded contributions</text>')
            continue
        counts: Counter[str] = Counter()
        for k, v in p.contributions_by_pair.items():
            counts[get_contrib_category(k)] += v
        x = float(ml)
        for i, cat in enumerate(CONTRIB_CATEGORIES):
            c = counts.get(cat, 0)
            if not c:
                continue
            seg = pw * c / p.contributions
            parts.append(
                f'<rect x="{x + 1:.1f}" y="{y + 6}" width="{max(seg - 2, 0.8):.1f}" height="26" rx="3" fill="{t["contrib"][i]}"/>'
            )
            pct = 100 * c / p.contributions
            if seg >= 42 and i < 3:
                parts.append(
                    f'<text x="{x + seg / 2:.1f}" y="{y + 23}" font-size="11" font-weight="600" text-anchor="middle" fill="{t["on_mark"]}">{pct:.0f}%</text>'
                )
            x += seg
    parts.append(f'<text x="16" y="{h - 8}" font-size="11" fill="{t["muted"]}">Shares of records, not of effort, time, or code.</text>')
    parts.append("</svg>")
    return "".join(parts) + "\n"
