// Interactive decision-chain graph for the TRACE decision chains page.
//
// Rendered by MyST's anywidget directive. The model's "chains" come from the
// generated _evidence_graph.md, which tools/trace_evidence renders from
// evidence.json, so this file holds no data. Each chain is drawn as a small
// directed graph: boxes are records, arrows are the links stored in them
// (a revision points to the decision it revises, a correction to what it
// corrects, a contribution to the decisions it builds on). Older records sit
// to the left; on narrow screens the chain becomes a vertical list with arcs.
//
// No dependencies. Side effects: renders into `el`, observes its size, and
// mirrors the selected chain in the URL hash.

const SVG = "http://www.w3.org/2000/svg";
const REL = { revises: "revises", corrects: "corrects", builds_on: "builds on" };
const REL_IN = { revises: "revised by", corrects: "corrected by", builds_on: "carried out in" };
const REL_HELP = {
  revises: "a decision that replaces an earlier one",
  corrects: "a correction that points at the mistake",
  builds_on: "work that cites the decisions it carried out",
};
const KIND = { decision: "Decision", correction: "Correction", annotation: "Annotation", contribution: "Contribution", external: "External" };

function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : String(v));
  }
  for (const c of kids.flat()) if (c != null) e.append(c.nodeType ? c : document.createTextNode(String(c)));
  return e;
}

function s(tag, attrs = {}) {
  const e = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, String(v));
  return e;
}

// Who is shown on a node: decision = proposer then resolver; contribution = idea then builder.
function actors(n) {
  const a = (t) => ({ ai: "agent", human: "human", collaborative: "shared" })[t] || "unrecorded";
  if (n.kind === "decision") return [a(n.proposed_by), n.disposition === "proposed" ? null : a(n.resolved_by)].filter(Boolean);
  if (n.kind === "contribution") return [a(n.direction), a(n.execution)];
  return [];
}

// Column = 1 + the deepest record this one points to, so arrows always point left.
function layoutColumns(chain) {
  const out = new Map(chain.nodes.map((n) => [n.id, []]));
  for (const e of chain.edges) out.get(e.source)?.push(e.target);
  const col = new Map();
  const depth = (id, seen = new Set()) => {
    if (col.has(id)) return col.get(id);
    if (seen.has(id)) return 0;
    seen.add(id);
    const t = out.get(id) || [];
    const d = t.length ? 1 + Math.max(...t.map((x) => depth(x, seen))) : 0;
    col.set(id, d);
    return d;
  };
  chain.nodes.forEach((n) => depth(n.id));
  const cols = [];
  chain.nodes.forEach((n, i) => {
    const c = col.get(n.id);
    (cols[c] ||= []).push({ n, i });
  });
  // Order each column by the mean row of what it points to (fewer crossings).
  const row = new Map();
  cols.forEach((list, c) => {
    if (c > 0) {
      const key = ({ n, i }) => {
        const r = (out.get(n.id) || []).map((t) => row.get(t)).filter((x) => x != null);
        return r.length ? r.reduce((a, b) => a + b, 0) / r.length : i;
      };
      list.sort((a, b) => key(a) - key(b) || a.i - b.i);
    }
    list.forEach(({ n }, r) => row.set(n.id, r - (list.length - 1) / 2));
  });
  return cols.map((list) => list.map(({ n }) => n));
}

function edgePath(a, b, mode, span = 1, lane = 0) {
  if (mode === "dag" && span > 1) {
    // Rounded orthogonal route through the reserved band above every node.
    const [x1, x2] = [a.x + a.w / 2, b.x + b.w / 2];
    const y = 8 + 14 * lane;
    const r = 8, dir = x2 < x1 ? -1 : 1;
    const d = `M${x1},${a.y} V${y + r} Q${x1},${y} ${x1 + dir * r},${y} H${x2 - dir * r} Q${x2},${y} ${x2},${y + r} V${b.y}`;
    return { d, mx: (x1 + x2) / 2, my: y };
  }
  if (mode === "dag") {
    const [x1, y1, x2, y2] = [a.x, a.y + a.h / 2, b.x + b.w, b.y + b.h / 2];
    const dx = Math.max(24, (x1 - x2) / 2);
    return { d: `M${x1},${y1} C${x1 - dx},${y1} ${x2 + dx},${y2} ${x2},${y2}`, mx: (x1 + x2) / 2, my: (y1 + y2) / 2 };
  }
  const [y1, y2] = [a.y + a.h / 2, b.y + b.h / 2];
  const x = a.x;
  const bulge = Math.min(a.x - 6, 18 + Math.abs(y1 - y2) * 0.12);
  return { d: `M${x},${y1} C${x - bulge},${y1} ${x - bulge},${y2} ${x},${y2}`, mx: x - bulge * 0.75, my: (y1 + y2) / 2 };
}

function render({ model, el }) {
  const chains = model.get("chains") || [];
  const projects = model.get("projects") || [];
  if (!chains.length) {
    el.append(h("p", {}, "No decision chains are published in this snapshot."));
    return;
  }
  const state = { project: "all", chain: 0, node: null };
  const fromHash = decodeURIComponent((location.hash || "").slice(1));
  const hashIdx = chains.findIndex((c) => c.slug === fromHash);
  if (hashIdx >= 0) state.chain = hashIdx;

  const root = h("div", { class: "tcg" });
  const filters = h("div", { class: "tcg-filters", role: "group", "aria-label": "Filter chains by project" });
  const cards = h("div", { class: "tcg-cards", role: "list" });
  const head = h("div", { class: "tcg-head" });
  const stage = h("div", { class: "tcg-stage" });
  const detail = h("div", { class: "tcg-detail", "aria-live": "polite" });
  const legend = h(
    "div",
    { class: "tcg-legend" },
    h("span", {}, h("i", { class: "tcg-dot a-agent" }), "agent"),
    h("span", {}, h("i", { class: "tcg-dot a-human" }), "human"),
    h("span", {}, h("i", { class: "tcg-dot a-shared" }), "shared"),
    ...Object.keys(REL).map((r) => h("span", { title: REL_HELP[r] }, h("i", { class: `tcg-line r-${r}` }), REL[r])),
  );
  const browse = h("h4", { class: "tcg-browse" }, "All chains");
  root.append(head, stage, legend, detail, browse, filters, cards);
  el.append(root);

  const visible = () => chains.map((c, i) => ({ c, i })).filter(({ c }) => state.project === "all" || c.project === state.project);

  function drawFilters() {
    filters.replaceChildren();
    const count = (slug) => chains.filter((c) => slug === "all" || c.project === slug).length;
    const opts = [{ slug: "all", name: "All projects" }, ...projects.filter((p) => count(p.slug) > 0)];
    for (const p of opts) {
      filters.append(
        h(
          "button",
          {
            class: "tcg-chip",
            type: "button",
            "aria-pressed": state.project === p.slug ? "true" : "false",
            onclick: () => {
              state.project = p.slug;
              const v = visible();
              if (!v.some(({ i }) => i === state.chain)) state.chain = v[0].i;
              state.node = null;
              update();
            },
          },
          p.name,
          h("span", { class: "tcg-count" }, String(count(p.slug))),
        ),
      );
    }
  }

  function glyph(chain) {
    const cols = layoutColumns(chain);
    const W = 56, H = 28;
    const pos = new Map();
    cols.forEach((list, c) => {
      list.forEach((n, r) => {
        const x = cols.length === 1 ? W / 2 : 5 + (c * (W - 10)) / (cols.length - 1);
        const y = H / 2 + (r - (list.length - 1) / 2) * 8;
        pos.set(n.id, [x, y]);
      });
    });
    const g = s("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, "aria-hidden": "true", class: "tcg-glyph" });
    for (const e of chain.edges) {
      const [a, b] = [pos.get(e.source), pos.get(e.target)];
      if (a && b) g.append(s("line", { x1: a[0], y1: a[1], x2: b[0], y2: b[1], class: `r-${e.relation}` }));
    }
    for (const n of chain.nodes) {
      const [x, y] = pos.get(n.id);
      g.append(s("circle", { cx: x, cy: y, r: n.id === chain.key ? 3.6 : 2.6, class: n.id === chain.key ? "key" : "" }));
    }
    return g;
  }

  function drawCards() {
    cards.replaceChildren();
    for (const { c, i } of visible()) {
      cards.append(
        h(
          "button",
          {
            class: "tcg-card",
            type: "button",
            role: "listitem",
            "aria-current": i === state.chain ? "true" : "false",
            onclick: () => {
              select(i);
              head.scrollIntoView({ behavior: "smooth", block: "start" });
            },
          },
          glyph(c),
          h("span", { class: "tcg-card-text" }, h("span", { class: "tcg-card-title" }, c.title), h("span", { class: "tcg-card-meta" }, `${c.project_name}, ${c.when}`)),
        ),
      );
    }
  }

  function select(i) {
    state.chain = i;
    state.node = null;
    try {
      history.replaceState(null, "", `#${chains[i].slug}`);
    } catch (_) {
      /* hash sync is a convenience only */
    }
    update();
  }

  function drawHead(chain) {
    const v = visible();
    const at = v.findIndex(({ i }) => i === state.chain);
    const step = (d) => select(v[(at + d + v.length) % v.length].i);
    const links = chain.edges.length;
    head.replaceChildren(
      h(
        "div",
        { class: "tcg-title" },
        h("h3", { id: `chain-${chain.slug}` }, chain.title),
        h(
          "p",
          {},
          `${chain.project_name}, ${chain.when}. ${chain.nodes.length} ${chain.nodes.length === 1 ? "record" : "records"}, ${links} ${links === 1 ? "link" : "links"}.`,
          chain.unshown ? ` ${chain.unshown} further ${chain.unshown === 1 ? "link points" : "links point"} to records not shown.` : "",
        ),
      ),
      h(
        "div",
        { class: "tcg-nav" },
        h("button", { type: "button", class: "tcg-chip", onclick: () => step(-1), "aria-label": "Previous chain" }, "Previous"),
        h("span", { class: "tcg-count" }, `${at + 1} of ${v.length}`),
        h("button", { type: "button", class: "tcg-chip", onclick: () => step(1), "aria-label": "Next chain" }, "Next"),
      ),
    );
  }

  function drawStage(chain) {
    stage.replaceChildren();
    const W = stage.clientWidth || el.clientWidth || 640;
    const cols = layoutColumns(chain);
    const GX = 64, GY = 18, MIN_W = 158, MAX_W = 250;
    const mode = cols.length * MIN_W + (cols.length - 1) * GX <= W ? "dag" : "list";
    const box = new Map();
    let H;
    let pad = 0;
    if (mode === "dag") {
      const w = Math.min(MAX_W, (W - (cols.length - 1) * GX) / cols.length);
      const nh = 118;
      const rows = Math.max(...cols.map((c) => c.length));
      const colOf = new Map(cols.flatMap((list, c) => list.map((n) => [n.id, c])));
      const longs = chain.edges.filter((e) => colOf.get(e.source) - colOf.get(e.target) > 1).length;
      pad = longs ? 30 + 14 * (longs - 1) : 0;
      H = rows * nh + (rows - 1) * GY;
      const x0 = (W - (cols.length * w + (cols.length - 1) * GX)) / 2;
      cols.forEach((list, c) => {
        const top = (H - (list.length * nh + (list.length - 1) * GY)) / 2;
        list.forEach((n, r) => box.set(n.id, { x: x0 + c * (w + GX), y: pad + top + r * (nh + GY), w, h: nh }));
      });
      H += pad;
    } else {
      const order = cols.flat();
      const gutter = chain.edges.length ? 44 : 0;
      const nh = 104;
      H = order.length * nh + (order.length - 1) * GY;
      order.forEach((n, r) => box.set(n.id, { x: gutter, y: r * (nh + GY), w: W - gutter, h: nh }));
    }
    stage.style.height = `${H}px`;
    stage.dataset.mode = mode;

    const sel = state.node ?? chain.key;
    const svg = s("svg", { class: "tcg-edges", width: W, height: H, viewBox: `0 0 ${W} ${H}`, "aria-hidden": "true" });
    const defs = s("defs");
    for (const r of Object.keys(REL)) {
      const m = s("marker", { id: `tcg-arrow-${r}`, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" });
      m.append(s("path", { d: "M0,0 L10,5 L0,10 z", class: `tcg-arrow r-${r}` }));
      defs.append(m);
    }
    svg.append(defs);
    const labels = [];
    const colIdx = new Map(cols.flatMap((list, c) => list.map((n) => [n.id, c])));
    let lane = 0;
    for (const e of chain.edges) {
      const [a, b] = [box.get(e.source), box.get(e.target)];
      if (!a || !b) continue;
      const span = colIdx.get(e.source) - colIdx.get(e.target);
      const p = edgePath(a, b, mode, span, span > 1 ? lane++ : 0);
      const on = e.source === sel || e.target === sel;
      svg.append(s("path", { d: p.d, class: `tcg-edge r-${e.relation}${on ? " on" : ""}`, "marker-end": `url(#tcg-arrow-${e.relation})` }));
      if (on) labels.push({ ...p, text: REL[e.relation], rel: e.relation });
    }
    stage.append(svg);

    for (const n of chain.nodes) {
      const b = box.get(n.id);
      const who = actors(n);
      const node = h(
        "button",
        {
          type: "button",
          class: `tcg-node k-${n.kind}${n.id === sel ? " sel" : ""}${n.id === chain.key ? " key" : ""}`,
          style: `left:${b.x}px;top:${b.y}px;width:${b.w}px;height:${b.h}px`,
          "aria-pressed": n.id === sel ? "true" : "false",
          "aria-label": `${n.label}: ${n.headline}`,
          onclick: () => {
            state.node = n.id;
            drawStage(chain);
            drawDetail(chain);
          },
        },
        h("span", { class: "tcg-node-top" }, h("span", { class: "tcg-kind" }, KIND[n.kind]), h("span", { class: "tcg-who" }, ...who.map((a) => h("i", { class: `tcg-dot a-${a}`, title: a })))),
        h("span", { class: "tcg-node-head" }, n.headline),
      );
      stage.append(node);
    }
    for (const l of labels) stage.append(h("span", { class: `tcg-elabel r-${l.rel}`, style: `left:${l.mx}px;top:${l.my}px` }, l.text));
  }

  function para(line) {
    const i = line.indexOf(": ");
    if (i > 0 && i <= 60) return h("p", {}, h("strong", {}, line.slice(0, i) + ": "), line.slice(i + 2));
    return h("p", {}, line);
  }

  function drawDetail(chain) {
    const sel = state.node ?? chain.key;
    const n = chain.nodes.find((x) => x.id === sel) || chain.nodes[0];
    const byId = new Map(chain.nodes.map((x) => [x.id, x]));
    const go = (id) => () => {
      state.node = id;
      drawStage(chain);
      drawDetail(chain);
    };
    const linkList = (title, items, names) =>
      items.length
        ? h(
            "div",
            { class: "tcg-rel" },
            h("span", { class: "tcg-rel-title" }, title),
            ...items.map(([rel, id]) => h("button", { type: "button", class: "tcg-chip", onclick: go(id) }, `${names[rel]} `, h("span", { class: "tcg-mono" }, id), `: ${byId.get(id)?.headline.slice(0, 64) ?? ""}${(byId.get(id)?.headline.length ?? 0) > 64 ? "..." : ""}`)),
          )
        : null;
    const outs = chain.edges.filter((e) => e.source === n.id).map((e) => [e.relation, e.target]);
    const ins = chain.edges.filter((e) => e.target === n.id).map((e) => [e.relation, e.source]);
    const body = n.url
      ? [h("p", {}, h("a", { href: n.url, target: "_blank", rel: "noopener" }, n.headline))]
      : (n.text || n.headline).split("\n").filter((x) => x.trim()).map(para);
    detail.replaceChildren(
      ...[h("div", { class: "tcg-detail-meta" }, h("span", { class: "tcg-mono" }, n.id), ` ${n.label}`, n.text ? "" : n.url ? "" : h("span", { class: "tcg-muted" }, " (first sentence of the record)")),
      h("blockquote", { class: "tcg-quote" }, ...body),
      linkList("This record", outs, REL),
      linkList("Linked from", ins, REL_IN)].filter(Boolean),
    );
  }

  function update() {
    const chain = chains[state.chain];
    drawFilters();
    drawCards();
    drawHead(chain);
    drawStage(chain);
    drawDetail(chain);
  }

  update();
  let last = 0;
  const ro = new ResizeObserver(() => {
    const w = stage.clientWidth;
    if (Math.abs(w - last) > 4) {
      last = w;
      drawStage(chains[state.chain]);
    }
  });
  ro.observe(stage);
  return () => ro.disconnect();
}

export default { render };
