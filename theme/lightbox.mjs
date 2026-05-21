// MyST plugin: image + mermaid lightbox via GLightbox.
//
// Vendored fork of choldgraf/myst-lightbox extended to cover
// :::{mermaid} blocks. The upstream plugin only wraps <img>; mermaid
// renders to inline SVG client-side after page mount, and book-theme
// is a SPA so the article DOM can be replaced on navigation. This
// version delegates clicks at the document level, refreshes the image
// gallery as new lightbox-wrapped images arrive, and renders mermaid
// via a hidden host element (no innerHTML round-trip on cloned SVG).
//
// Once stable, the diff against upstream is small enough to PR back.

const GLIGHTBOX_VERSION = '3.3.0';
const GLIGHTBOX_CSS = `https://cdn.jsdelivr.net/npm/glightbox@${GLIGHTBOX_VERSION}/dist/css/glightbox.min.css`;
const GLIGHTBOX_ESM = `https://cdn.jsdelivr.net/npm/glightbox@${GLIGHTBOX_VERSION}/+esm`;
const LINK_CLASS = 'myst-lightbox-link';
const MERMAID_SELECTOR = 'svg[id^="mermaid-"]';

// Server-side: resolve node:path for the AST transform. Browser skips
// this branch entirely so no failed fetch reaches the console.
let pathMod;
if (typeof process !== 'undefined' && process.versions && process.versions.node) {
  pathMod = await import('node:path');
}

function ensureCss() {
  if (document.querySelector(`link[href="${GLIGHTBOX_CSS}"]`)) return;
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = GLIGHTBOX_CSS;
  document.head.appendChild(link);
}

function ensureMermaidStyles() {
  if (document.getElementById('myst-lightbox-mermaid-style')) return;
  const style = document.createElement('style');
  style.id = 'myst-lightbox-mermaid-style';
  style.textContent = `
    ${MERMAID_SELECTOR} { cursor: zoom-in; }
    .myst-lightbox-mermaid-host { display: none; }
    .myst-lightbox-mermaid svg {
      width: 95vw !important;
      max-width: 95vw !important;
      height: auto !important;
      max-height: 90vh !important;
    }
  `;
  document.head.appendChild(style);
}

let glightboxCtor;
async function getGLightbox() {
  if (!glightboxCtor) {
    const mod = await import(GLIGHTBOX_ESM);
    glightboxCtor = mod.default;
  }
  return glightboxCtor;
}

// One active lightbox instance at a time. Prevents stacking on rapid clicks.
let activeLightbox = null;
function setActive(lb, cleanup) {
  activeLightbox = lb;
  lb.on('close', () => {
    activeLightbox = null;
    cleanup?.();
    try { lb.destroy(); } catch (_) { /* noop */ }
  });
}

// ----- Image lightbox -----------------------------------------------------

let imageGallery = null;
let reloadHandle = null;
function scheduleGalleryReload() {
  if (!imageGallery) return;
  if (reloadHandle) return;
  reloadHandle = setTimeout(() => {
    reloadHandle = null;
    try { imageGallery.reload(); } catch (_) { /* noop */ }
  }, 50);
}

function bindImage(img) {
  if (img.closest('a[href]')) return;
  if (img.parentElement?.classList?.contains(LINK_CLASS)) return;
  const caption = img.closest('figure')?.querySelector('figcaption')?.innerHTML?.trim() || '';
  const anchor = document.createElement('a');
  anchor.href = img.src;
  anchor.className = LINK_CLASS;
  anchor.style.cursor = 'zoom-in';
  if (img.alt) anchor.dataset.title = img.alt;
  if (caption) anchor.dataset.description = caption;
  img.parentNode.insertBefore(anchor, img);
  anchor.appendChild(img);
  scheduleGalleryReload();
}

// ----- Mermaid lightbox ---------------------------------------------------

async function openMermaidLightbox(svg) {
  if (activeLightbox) return;
  // Claim the slot synchronously so a second click during the await
  // below sees a non-null activeLightbox and bails out.
  activeLightbox = 'pending';

  // Host the cloned SVG in a hidden DOM element and point GLightbox at it
  // by selector. Avoids round-tripping through innerHTML.
  const hostId = `myst-lightbox-mermaid-host-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
  const host = document.createElement('div');
  host.id = hostId;
  host.className = 'myst-lightbox-mermaid-host myst-lightbox-mermaid';
  host.appendChild(svg.cloneNode(true));
  document.body.appendChild(host);

  const GLightbox = await getGLightbox();
  const lb = GLightbox({
    elements: [{ href: `#${hostId}`, type: 'inline', width: '95vw', height: '95vh' }],
    zoomable: true,
  });
  setActive(lb, () => host.remove());
  lb.open();
}

// ----- Initialization -----------------------------------------------------

let initialized = false;
async function initialize() {
  if (initialized) return;
  initialized = true;
  ensureCss();
  ensureMermaidStyles();

  const root = document.querySelector('article.article, main') || document.body;
  root.querySelectorAll('img').forEach(bindImage);

  // Late-arriving images (SPA navigation, async mermaid re-render).
  const observer = new MutationObserver((muts) => {
    for (const m of muts) {
      for (const node of m.addedNodes) {
        if (!(node instanceof Element)) continue;
        if (node.tagName === 'IMG') bindImage(node);
        node.querySelectorAll?.('img').forEach(bindImage);
      }
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });

  // Document-level click delegation. Survives SPA reconciliation because
  // no per-element handler or class tag is needed.
  document.addEventListener('click', (ev) => {
    const target = ev.target;
    if (!(target instanceof Element)) return;
    // Image lightbox: click on an anchor we wrapped.
    const lbLink = target.closest(`.${LINK_CLASS}`);
    if (lbLink) {
      // GLightbox's selector binding handles this case; bail and let it run.
      return;
    }
    // Mermaid: any click inside a mermaid SVG that isn't on an anchor.
    if (target.closest('a[href]')) return;
    const svg = target.closest(MERMAID_SELECTOR);
    if (!svg) return;
    ev.preventDefault();
    openMermaidLightbox(svg);
  }, true);

  // Single GLightbox gallery for images, refreshed as new anchors appear.
  const GLightbox = await getGLightbox();
  imageGallery = GLightbox({ selector: `.${LINK_CLASS}`, loop: true, zoomable: true });
}

async function render({ el }) {
  el.style.display = 'none';
  await initialize();
}

// ----- AST transform ------------------------------------------------------

const PLUGIN_PATH = new URL(import.meta.url).pathname;

const injectWidgetTransform = {
  name: 'lightbox-inject-widget',
  doc: 'Injects a hidden anywidget that turns figures, images, and mermaid blocks into a lightbox gallery.',
  stage: 'document',
  plugin: (_, utils) => (tree, file) => {
    const hasLightboxable =
      utils.selectAll('image', tree).length > 0 ||
      utils.selectAll('container[kind="figure"]', tree).length > 0 ||
      utils.selectAll('mermaid', tree).length > 0;
    if (!hasLightboxable) return;
    tree.children.push({
      type: 'block',
      children: [
        {
          type: 'anywidget',
          esm: pathMod.relative(pathMod.dirname(file.path), PLUGIN_PATH),
          model: {},
          id: crypto.randomUUID(),
        },
      ],
    });
  },
};

export default {
  name: 'Lightbox',
  transforms: [injectWidgetTransform],
  render,
};
