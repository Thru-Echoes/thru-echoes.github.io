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
const MARKERS = ["revises", "corrects", "builds_on", "rules"];
const REL_HELP = {
  revises: "a decision that replaces an earlier one",
  corrects: "a correction that points at the mistake",
  builds_on: "work that cites the decisions it carried out",
};
const WHO = { ai: "Agent", human: "Human", system: "System", not_recorded: "Unrecorded" };

// A decision a human rejected or revised is drawn as two boxes: the proposal,
// and the human's ruling (stored on the same record) pointing at it. Links
// that revise or build on such a decision attach to the ruling, the later
// state; corrections keep pointing at the proposal they correct.
function expand(c) {
  const rid = (id) => `${id}::ruling`;
  const byId = new Map(c.nodes.map((n) => [n.id, n]));
  const ruled = new Set(c.nodes.filter((n) => n.kind === "decision" && n.resolution).map((n) => n.id));
  const nodes = [];
  for (const n of c.nodes) {
    if (!ruled.has(n.id)) {
      nodes.push(n);
      continue;
    }
    nodes.push({ ...n, split: true });
    nodes.push({
      id: rid(n.id), record: n.id, kind: "ruling", disposition: n.disposition, resolved_by: n.resolved_by,
      headline: n.resolution, text: n.resolution, label: `${WHO[n.resolved_by] || "Unrecorded"} ${n.disposition}`,
    });
  }
  const verb = (id) => (byId.get(id)?.disposition === "rejected" ? ["rejects", "rejected by"] : ["amends", "amended by"]);
  const edges = c.edges.map((e) => (ruled.has(e.target) && e.relation !== "corrects" ? { ...e, target: rid(e.target) } : e));
  for (const id of ruled) {
    const [v, vIn] = verb(id);
    edges.push({ source: rid(id), target: id, relation: "rules", verb: v, verbIn: vIn });
  }
  const key = ruled.has(c.key) ? rid(c.key) : c.key;
  return { ...c, key, nodes, edges, records: c.nodes.length, links: c.edges.length, rulings: ruled.size };
}

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
  if (n.kind === "ruling") return [a(n.resolved_by)];
  if (n.kind === "decision" && n.split) return [a(n.proposed_by)];
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
  return cols.filter(Boolean).map((list) => list.map(({ n }) => n));
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
  const chains = (model.get("chains") || []).map(expand);
  const compact = Boolean(model.get("compact"));
  const projects = model.get("projects") || [];
  if (!chains.length) {
    el.append(h("p", {}, "No decision chains are published in this snapshot."));
    return;
  }
  const state = { project: "all", chain: 0, node: null };
  let fromHash = "";
  if (!compact) {
    try {
      fromHash = decodeURIComponent(location.hash || "").replace(/^#chain=/, "");
    } catch (_) {
      /* a malformed hash just selects the first chain */
    }
  }
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
    h("span", { title: "a human's rejection or revision of the proposal it points at" }, h("i", { class: "tcg-line r-rules" }), "human ruling"),
    ...Object.keys(REL).map((r) => h("span", { title: REL_HELP[r] }, h("i", { class: `tcg-line r-${r}` }), REL[r])),
  );
  const browse = h("h4", { class: "tcg-browse" }, "All chains");
  if (compact) root.classList.add("tcg-compact");
  root.append(head, stage, legend, detail, ...(compact ? [] : [browse, filters, cards]));
  el.append(root);

  // Redraws rebuild buttons; keep keyboard focus on the matching control.
  const shadow = el.getRootNode();
  function keepFocus(fn, nextKey) {
    const active = shadow.activeElement;
    const inside = active && root.contains(active);
    const key = nextKey ?? (inside ? active.dataset.key : null);
    fn();
    if (!key || (!inside && nextKey == null)) return;
    const target = [...root.querySelectorAll("[data-key]")].find((x) => x.dataset.key === key);
    target?.focus({ preventScroll: true });
  }

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
            "data-key": `filter:${p.slug}`,
            onclick: () => {
              state.project = p.slug;
              const v = visible();
              if (v.some(({ i }) => i === state.chain)) keepFocus(update);
              else keepFocus(() => select(v[0].i), `filter:${p.slug}`);
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
      g.append(s("circle", { cx: x, cy: y, r: n.id === chain.key ? 3.6 : 2.6, class: n.id === chain.key ? "key" : n.kind === "ruling" ? "ruling" : "" }));
    }
    return g;
  }

  function drawCards() {
    cards.replaceChildren();
    for (const { c, i } of visible()) {
      const card = h(
        "button",
        {
          class: "tcg-card",
          type: "button",
          "aria-current": i === state.chain ? "true" : "false",
          "data-key": `card:${c.slug}`,
          onclick: () => {
            keepFocus(() => select(i), `node:${c.key}`);
            head.scrollIntoView({ behavior: "smooth", block: "start" });
          },
        },
        glyph(c),
        h("span", { class: "tcg-card-text" }, h("span", { class: "tcg-card-title" }, c.title), h("span", { class: "tcg-card-meta" }, `${c.project_name}, ${c.when}`)),
      );
      cards.append(h("div", { role: "listitem", class: "tcg-card-item" }, card));
    }
  }

  function select(i) {
    state.chain = i;
    state.node = null;
    try {
      history.replaceState(null, "", `#chain=${chains[i].slug}`);
    } catch (_) {
      /* hash sync is a convenience only */
    }
    update();
  }

  function drawHead(chain) {
    const v = visible();
    const at = v.findIndex(({ i }) => i === state.chain);
    const step = (d) => keepFocus(() => select(v[(at + d + v.length) % v.length].i));
    const links = chain.links;
    head.replaceChildren(
      ...[h(
        "div",
        { class: "tcg-title" },
        h("h3", { id: `chain-${chain.slug}` }, chain.title),
        h(
          "p",
          {},
          `${chain.project_name}, ${chain.when}. ${chain.records} ${chain.records === 1 ? "record" : "records"}` +
            (chain.rulings ? `, ${chain.rulings} human ${chain.rulings === 1 ? "ruling" : "rulings"}` : "") +
            (links ? `, ${links} stored ${links === 1 ? "link" : "links"}` : "") +
            ".",
          chain.unshown ? ` ${chain.unshown} further ${chain.unshown === 1 ? "link points" : "links point"} to records not shown.` : "",
        ),
      ),
      compact
        ? null
        : h(
        "div",
        { class: "tcg-nav" },
        h("button", { type: "button", class: "tcg-chip", onclick: () => step(-1), "aria-label": "Previous chain", "data-key": "nav:prev" }, "Previous"),
        h("span", { class: "tcg-count" }, `${at + 1} of ${v.length}`),
        h("button", { type: "button", class: "tcg-chip", onclick: () => step(1), "aria-label": "Next chain", "data-key": "nav:next" }, "Next"),
      )].filter(Boolean),
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
    for (const r of MARKERS) {
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
      if (on || e.relation === "rules") labels.push({ ...p, text: e.verb ?? REL[e.relation], rel: e.relation });
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
          "data-key": `node:${n.id}`,
          onclick: () => {
            state.node = n.id;
            keepFocus(() => {
              drawStage(chain);
              drawDetail(chain);
            });
          },
        },
        h("span", { class: "tcg-node-top" }, h("span", { class: "tcg-kind" }, n.kind === "ruling" ? n.label : n.split ? `${WHO[n.proposed_by] || "Unrecorded"} proposal` : KIND[n.kind]), h("span", { class: "tcg-who" }, ...who.map((a) => h("i", { class: `tcg-dot a-${a}`, title: a })))),
        h("span", { class: "tcg-node-head" }, n.headline),
      );
      stage.append(node);
    }
    for (const l of labels) {
      const x = mode === "list" ? Math.max(l.mx, 32) : l.mx; // keep gutter labels on screen
      stage.append(h("span", { class: `tcg-elabel r-${l.rel}`, style: `left:${x}px;top:${l.my}px` }, l.text));
    }
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
      keepFocus(() => {
        drawStage(chain);
        drawDetail(chain);
      }, `node:${id}`);
    };
    const linkList = (title, items) =>
      items.length
        ? h(
            "div",
            { class: "tcg-rel" },
            h("span", { class: "tcg-rel-title" }, title),
            ...items.map(([rel, id]) => h("button", { type: "button", class: "tcg-chip", onclick: go(id) }, `${rel} `, h("span", { class: "tcg-mono" }, byId.get(id)?.record ? `${byId.get(id).record} ruling` : id), `: ${byId.get(id)?.headline.slice(0, 64) ?? ""}${(byId.get(id)?.headline.length ?? 0) > 64 ? "..." : ""}`)),
          )
        : null;
    const outs = chain.edges.filter((e) => e.source === n.id).map((e) => [e.verb ?? REL[e.relation], e.target]);
    const ins = chain.edges.filter((e) => e.target === n.id).map((e) => [e.verbIn ?? REL_IN[e.relation], e.source]);
    const body = n.url
      ? [h("p", {}, h("a", { href: n.url, target: "_blank", rel: "noopener" }, n.headline))]
      : n.kind === "ruling"
        ? [h("p", {}, n.text)]
        : (n.text || n.headline).split("\n").filter((x) => x.trim()).map(para);
    const meta = n.kind === "ruling" ? `${n.label} (the ruling stored on this decision record)` : n.split ? n.label.replace(/,.*$/, "") : n.label;
    detail.replaceChildren(
      ...[h("div", { class: "tcg-detail-meta" }, h("span", { class: "tcg-mono" }, n.record ?? n.id), ` ${meta}`, n.text ? "" : n.url ? "" : h("span", { class: "tcg-muted" }, " (short excerpt from the record)")),
      h("blockquote", { class: "tcg-quote" }, ...body),
      linkList("This record", outs),
      linkList("Linked from", ins)].filter(Boolean),
    );
  }

  function update() {
    const chain = chains[state.chain];
    if (!compact) {
      drawFilters();
      drawCards();
    }
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
      keepFocus(() => drawStage(chains[state.chain]));
    }
  });
  ro.observe(stage);
  return () => ro.disconnect();
}

export default { render };
