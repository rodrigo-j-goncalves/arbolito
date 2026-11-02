#!/usr/bin/env python3
"""
arbolito  v1.6.0
Reads a CSV file and writes an interactive D3.js mind map HTML file.

Usage:
    python arbolito.py --input mindmap.csv --output mindmap.html
    python arbolito.py --input mindmap.csv --output mindmap.html --save-json tree.json
"""

import csv
import json
import argparse
from pathlib import Path
from html import escape as html_escape


# ── CSV → Tree ────────────────────────────────────────────────────────────────

def csv_to_meta_and_tree(path: Path) -> tuple:
    """
    Read a CSV file. Returns (meta: dict, tree: dict).
    META rows must come before the header row (L1, L2, ...).
    META row format: META, key, value
    """
    with open(path, newline='', encoding='utf-8') as f:
        raw_rows = list(csv.reader(f))

    if not raw_rows:
        raise ValueError("CSV file is empty.")

    # Extract META rows (before the header) and find header row index
    meta = {}
    header_idx = None
    for i, row in enumerate(raw_rows):
        if not row or all(c.strip() == '' for c in row):
            continue
        if row[0].strip().upper() == 'META':
            key   = row[1].strip() if len(row) > 1 else ''
            value = row[2].strip().replace('\\n', '\n') if len(row) > 2 else ''
            if key:
                meta[key] = value
        else:
            header_idx = i
            break

    if header_idx is None:
        raise ValueError("No header row found in CSV.")

    # Re-parse from header row onwards as a DictReader
    import io
    buf = io.StringIO()
    csv.writer(buf).writerows(raw_rows[header_idx:])
    reader = csv.DictReader(io.StringIO(buf.getvalue()))
    rows   = list(reader)
    headers = reader.fieldnames or []

    # Detect level columns (L1, L2, L3 ...)
    level_cols = sorted(
        [h for h in headers if h.strip().upper().startswith('L') and h.strip()[1:].isdigit()],
        key=lambda h: int(h.strip()[1:])
    )
    if not level_cols:
        raise ValueError("No level columns found (expected L1, L2, ...).")

    def parse_collapsed(val):
        if val is None or val.strip() == '':
            return True
        return val.strip().lower() != 'false'

    def parse_fontsize(val):
        if val is None or val.strip() == '':
            return None
        try:
            return int(val.strip())
        except ValueError:
            return None

    def parse_order(val):
        if val is None or val.strip() == '':
            return None
        try:
            return int(val.strip())
        except ValueError:
            return None

    root  = None
    stack = []

    for row in rows:
        depth = None
        name  = None
        for i, col in enumerate(level_cols):
            val = row.get(col, '').strip()
            if val:
                depth = i
                name  = val

        if depth is None or not name:
            continue

        # Convert literal \n sequences (from LibreOffice CSV export) to real newlines
        name = name.replace('\\n', '\n')

        node = {'name': name, 'collapsed': parse_collapsed(row.get('collapsed', ''))}
        fs = parse_fontsize(row.get('fontSize', ''))
        if fs is not None:
            node['fontSize'] = fs
        link = row.get('link', '').strip()
        if link:
            node['link'] = link
        order = parse_order(row.get('order', ''))
        if order is not None:
            node['order'] = order

        if depth == 0:
            root  = node
            stack = [(0, root)]
        else:
            while stack and stack[-1][0] >= depth:
                stack.pop()
            if not stack:
                raise ValueError(
                    f"Node '{name}' at depth {depth+1} has no parent. "
                    "Check indentation in your CSV."
                )
            parent = stack[-1][1]
            parent.setdefault('children', []).append(node)
            stack.append((depth, node))

    if root is None:
        raise ValueError("Could not build tree from CSV. Check your L1 column.")

    return meta, root


# ── HTML Template ─────────────────────────────────────────────────────────────

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"{HTML_CLASS_ATTR}>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{TITLE}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ── Theme variables ─────────────────────────────────────────── */
:root {
  --bg:           #0d1117;
  --toolbar-bg:   #161b22;
  --toolbar-bdr:  #21262d;
  --btn-bg:       #21262d;
  --btn-color:    #8b949e;
  --btn-bdr:      #30363d;
  --btn-hover-bg: #2d333b;
  --btn-hover-c:  #c9d1d9;
  --lbl-color:    #484f58;
  --hint-color:   #3d444d;
  --node-text:    #e6edf3;
  --link-opacity: 0.45;
}

:root.light {
  --bg:           #f4f6f9;
  --toolbar-bg:   #eaecf0;
  --toolbar-bdr:  #d0d5dd;
  --btn-bg:       #dde1e9;
  --btn-color:    #3a4050;
  --btn-bdr:      #b8bec9;
  --btn-hover-bg: #cdd2dc;
  --btn-hover-c:  #1a202c;
  --lbl-color:    #8a909e;
  --hint-color:   #adb3bf;
  --node-text:    #1a202c;
  --link-opacity: 0.55;
}

{BG_OVERRIDE}
body {
  background: var(--bg);
  font-family: 'Atkinson Hyperlegible', sans-serif;
  overflow: hidden;
  width: 100vw;
  height: 100vh;
  position: relative;
  -webkit-user-select: none;
  user-select: none;
  transition: background .3s;
}

#toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  background: var(--toolbar-bg);
  border-bottom: 1px solid var(--toolbar-bdr);
  transition: background .3s, border-color .3s;
}

.lbl { font-size: 11px; color: var(--lbl-color); text-transform: uppercase; letter-spacing: .08em; }

.btn {
  background: var(--btn-bg);
  color: var(--btn-color);
  border: 1px solid var(--btn-bdr);
  border-radius: 6px;
  padding: 5px 14px;
  font-size: 12px;
  font-family: 'Atkinson Hyperlegible', sans-serif;
  cursor: pointer;
  transition: all .15s;
  letter-spacing: .03em;
}
.btn:hover  { background: var(--btn-hover-bg); color: var(--btn-hover-c); }
.btn.active { background: #1f4068; color: #79c0ff; border-color: #388bfd; }

/* theme toggle button — never gets .active style */
#btn-theme { width: 100%; }

#toolbar-right {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 4px;
  margin-left: 10px;
}

#brand-link {
  font-size: 10px;
  color: var(--hint-color);
  text-decoration: none;
  text-align: center;
  letter-spacing: .06em;
  transition: color .15s;
}
#brand-link:hover { color: var(--btn-hover-c); }

.hint { margin-left: auto; font-size: 11px; color: var(--hint-color); }

#meta-bar {
  display: flex;
  align-items: center;
  padding: 5px 16px;
  background: var(--toolbar-bg);
  border-bottom: 1px solid var(--toolbar-bdr);
  gap: 0;
  transition: background .3s, border-color .3s;
}

#meta-bar span {
  font-size: 12px;
  color: var(--btn-color);
  white-space: nowrap;
}

#meta-bar .sep {
  margin: 0 8px;
  color: var(--toolbar-bdr);
}

#header-outer {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 50;
}

#settings-btn {
  position: fixed;
  top: 6px;
  left: 8px;
  z-index: 100;
  background: var(--btn-bg);
  color: var(--btn-color);
  border: 1px solid var(--btn-bdr);
  border-radius: 6px;
  width: 28px;
  height: 28px;
  padding: 5px;
  cursor: pointer;
  opacity: 0.5;
  transition: opacity .2s, background .15s, color .15s;
  display: flex;
  align-items: center;
  justify-content: center;
}
#settings-btn:hover, #settings-btn.open { opacity: 1; background: var(--btn-hover-bg); color: var(--btn-hover-c); }

#meta-bar { padding-left: 44px; }

#header-wrap {
  max-height: 0;
  overflow: hidden;
  transition: max-height .3s ease;
}

#header-wrap.open { max-height: 200px; }

#canvas { position: absolute; top: 0; left: 0; right: 0; bottom: 0; overflow: hidden; }
svg { width: 100%; height: 100%; cursor: grab; }
svg:active { cursor: grabbing; }
</style>
</head>
<body>

<button id="settings-btn" onclick="toggleSettings(event)" aria-label="Settings">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>
</button>

<div id="header-outer">
  {META_BAR}
  <div id="header-wrap">
    <div id="toolbar">
      <span class="lbl">Layout</span>
      <button class="btn"        id="btn-radial"  onclick="setLayout('radial')">Radial</button>
      <button class="btn"        id="btn-topdown" onclick="setLayout('topdown')">Top-down</button>
      <button class="btn"        id="btn-horiz"   onclick="setLayout('horiz')">Horizontal</button>
      <button class="btn"        id="btn-reset"       onclick="location.reload()">Reset</button>
      <button class="btn"        id="btn-expand-all"  onclick="expandAll()">Expand all</button>
      <button class="btn"        id="btn-collapse-all" onclick="collapseAll()">Collapse all</button>
      <span class="hint">click to expand · drag to pan · scroll to zoom · auto-fits on expand/collapse</span>
      <div id="toolbar-right">
        <button class="btn" id="btn-theme" onclick="toggleTheme()">{THEME_BTN_LABEL}</button>
        <a href="https://github.com/rodrigo-j-goncalves/arbolito" target="_blank" id="brand-link">Arbolito</a>
      </div>
    </div>
  </div>
</div>

<div id="canvas"><svg id="svg"></svg></div>

<script>
const RAW = {JSON_DATA};

// ── Config ───────────────────────────────────────────────────────────────────
const DUR         = 500;
const NH_BASE     = 34;   // single-line node height
const LINE_H      = 18;   // height per extra line
const VPAD_TEXT   = 10;   // vertical padding inside node (top+bottom)
const HPAD        = 16;
const CW          = 7.0;  // avg char width px at 13px Atkinson Hyperlegible
const MIN_W       = 70;
const RX          = 9;
const SIBLING_GAP = 20;
const DEFAULT_FS  = 13;
const FIT_PAD     = 40;   // padding around the fitted tree (px)

const PALETTE = [
  '#2d6a9f','#2d8a64','#8a6a2d','#6a2d8a',
  '#8a2d2d','#2d7a8a','#7a8a2d',
];

let layout  = '{INIT_LAYOUT}';
const INIT_EXPAND = '{INIT_EXPAND}';
let isFirst = true;
let autoFit = true;       // auto-fit viewport to tree; disabled by manual pan/zoom
const stateMap = {};

// ── Utilities ────────────────────────────────────────────────────────────────
function pid(d) {
  return d.ancestors().reverse().map(n => n.data.name).join('\x01');
}

function lines(name) { return name.split('\n'); }

function nw(name, fontSize) {
  const fs = fontSize || DEFAULT_FS;
  const cw = fs * (CW / DEFAULT_FS);
  const longest = Math.max(...lines(name).map(l => l.length));
  return Math.max(MIN_W, longest * cw + HPAD * 2);
}

function nh(name, fontSize) {
  const fs  = fontSize || DEFAULT_FS;
  const lh  = fs * (LINE_H / DEFAULT_FS);
  const n   = lines(name).length;
  return n === 1 ? NH_BASE : n * lh + VPAD_TEXT;
}

function rgba(hex, a) {
  const r = parseInt(hex.slice(1,3),16);
  const g = parseInt(hex.slice(3,5),16);
  const b = parseInt(hex.slice(5,7),16);
  return `rgba(${r},${g},${b},${a})`;
}

function branchColor(d) {
  if (d.depth === 0) return '#1a3a5c';
  let n = d;
  while (n.parent && n.parent.depth > 0) n = n.parent;
  const idx = (n.parent.children || []).indexOf(n);
  return PALETTE[((idx % PALETTE.length) + PALETTE.length) % PALETTE.length];
}

// ── Plain tree ───────────────────────────────────────────────────────────────
function mkPlain(node, pathId) {
  const id = pathId || node.name;
  if (!(id in stateMap)) stateMap[id] = (node.collapsed !== false);
  const hasKids = !!(node.children && node.children.length);
  return {
    name:     node.name,
    fontSize: node.fontSize || null,
    link:     node.link || null,
    _hasKids: hasKids,
    children: (!stateMap[id] && hasKids)
      ? node.children.map(c => mkPlain(c, id + '\x01' + c.name))
      : null,
  };
}

function buildRoot() {
  return d3.hierarchy(mkPlain(RAW), d => d.children);
}

// ── Layout ───────────────────────────────────────────────────────────────────
function applyLayout(root, W, H) {
  if (layout === 'radial') {
    const R = Math.min(W, H) / 2 - 90;
    d3.tree()
      .size([2 * Math.PI, R])
      .separation((a, b) => {
        const r    = Math.max(a.y || 1, 1);
        const arcA = nw(a.data.name, a.data.fontSize) / r;
        const arcB = nw(b.data.name, b.data.fontSize) / r;
        const base = (a.parent === b.parent) ? 1 : 2;
        return base * (arcA / 2 + arcB / 2 + SIBLING_GAP / r);
      })
    (root);
    root.each(d => {
      d.px =  d.y * Math.sin(d.x);
      d.py = -d.y * Math.cos(d.x);
    });

  } else if (layout === 'topdown') {
    const yStep = 90;
    d3.tree()
      .nodeSize([1, yStep])
      .separation((a, b) => {
        return nw(a.data.name, a.data.fontSize) / 2
             + nw(b.data.name, b.data.fontSize) / 2
             + SIBLING_GAP;
      })
    (root);
    root.each(d => { d.px = d.x; d.py = d.y; });

  } else {
    // Horizontal: depth step = widest node + fixed gap, so links never go backwards
    let maxNodeW = 0;
    root.each(d => { maxNodeW = Math.max(maxNodeW, nw(d.data.name, d.data.fontSize)); });
    const xStep = maxNodeW + 120;
    d3.tree()
      .nodeSize([1, xStep])
      .separation((a, b) => {
        const ha = nh(a.data.name, a.data.fontSize);
        const hb = nh(b.data.name, b.data.fontSize);
        return ha / 2 + hb / 2 + SIBLING_GAP;
      })
    (root);
    root.each(d => { d.px = d.y; d.py = d.x; });
  }
}

// ── Link path ────────────────────────────────────────────────────────────────
function linkPathD(s, t) {
  const sx = s.px, sy = s.py;
  const tx = t.px, ty = t.py;
  const sw  = nw(s.data.name, s.data.fontSize);
  const tw  = nw(t.data.name, t.data.fontSize);
  const sh  = nh(s.data.name, s.data.fontSize);
  const th  = nh(t.data.name, t.data.fontSize);

  if (layout === 'radial') {
    return `M${sx},${sy} Q${(sx+tx)/2},${(sy+ty)/2} ${tx},${ty}`;
  } else if (layout === 'topdown') {
    const y1 = sy + sh / 2;
    const y2 = ty - th / 2;
    const my = (y1 + y2) / 2;
    return `M${sx},${y1} C${sx},${my} ${tx},${my} ${tx},${y2}`;
  } else {
    const x1 = sx + sw / 2;
    const x2 = tx - tw / 2;
    const mx = (x1 + x2) / 2;
    return `M${x1},${sy} C${mx},${sy} ${mx},${ty} ${x2},${ty}`;
  }
}

// ── SVG setup ────────────────────────────────────────────────────────────────
const svgEl   = d3.select('#svg');
const zoomG   = svgEl.append('g');
const centerG = zoomG.append('g');
const linksG  = centerG.append('g');
const nodesG  = centerG.append('g');

const zoomBeh = d3.zoom()
  .scaleExtent([0.1, 5])
  .on('zoom', e => {
    zoomG.attr('transform', e.transform);
    // Disable auto-fit only on genuine pan/zoom gestures, not programmatic transforms
    const t = e.sourceEvent && e.sourceEvent.type;
    if (t === 'wheel' || t === 'mousemove' || t === 'touchmove') autoFit = false;
  });
svgEl.call(zoomBeh).on('dblclick.zoom', null);

function centerTransform(W, H) {
  if (layout === 'radial')  return `translate(${W/2},${H/2})`;
  if (layout === 'topdown') return `translate(${W/2},60)`;
  return `translate(90,${H/2})`;
}

// ── Auto-fit ─────────────────────────────────────────────────────────────────
// Computes the bounding box of all visible nodes in zoomG space and applies
// a zoom transform so they fill the canvas with FIT_PAD margin.
function fitToView(root, W, H, dur) {
  // Parse centerG's own translation (relative to zoomG at identity)
  const ct = centerG.attr('transform') || '';
  const m  = ct.match(/translate\(([^,]+),([^)]+)\)/);
  const cx = m ? +m[1] : 0;
  const cy = m ? +m[2] : 0;

  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  root.each(d => {
    const hw = nw(d.data.name, d.data.fontSize) / 2;
    const hh = nh(d.data.name, d.data.fontSize) / 2;
    x0 = Math.min(x0, cx + d.px - hw);
    x1 = Math.max(x1, cx + d.px + hw);
    y0 = Math.min(y0, cy + d.py - hh);
    y1 = Math.max(y1, cy + d.py + hh);
  });

  const bw = x1 - x0;
  const bh = y1 - y0;
  if (bw <= 0 || bh <= 0) return;

  const k  = Math.min((W - 2 * FIT_PAD) / bw, (H - 2 * FIT_PAD) / bh);
  const tx = (W - k * (x0 + x1)) / 2;
  const ty = (H - k * (y0 + y1)) / 2;

  svgEl.transition().duration(dur).ease(d3.easeCubicInOut)
    .call(zoomBeh.transform, d3.zoomIdentity.translate(tx, ty).scale(k));
}

// ── Main update ───────────────────────────────────────────────────────────────
function update(clickedPid) {
  const W   = document.getElementById('canvas').clientWidth;
  const H   = document.getElementById('canvas').clientHeight;
  const dur = isFirst ? 0 : DUR;

  const root = buildRoot();
  applyLayout(root, W, H);

  let src = root;
  if (clickedPid) root.each(d => { if (pid(d) === clickedPid) src = d; });
  const srcX = src.px, srcY = src.py;
  const fakeSrc = { px: srcX, py: srcY, data: src.data };

  // ── Links ─────────────────────────────────────────────────────────────────
  linksG.selectAll('path.lnk')
    .data(root.links(), d => pid(d.source) + '→' + pid(d.target))
    .join(
      enter => enter.append('path').attr('class','lnk')
        .attr('fill','none')
        .attr('stroke', d => rgba(branchColor(d.target), linkOpacity()))
        .attr('stroke-width', 1.5)
        .attr('d', () => linkPathD(fakeSrc, fakeSrc))
        .call(e => e.transition().duration(dur).ease(d3.easeCubicInOut)
          .attr('d', d => linkPathD(d.source, d.target))
        ),
      upd => upd.transition().duration(dur).ease(d3.easeCubicInOut)
        .attr('d', d => linkPathD(d.source, d.target))
        .attr('stroke', d => rgba(branchColor(d.target), linkOpacity())),
      exit => exit.transition().duration(dur).ease(d3.easeCubicInOut)
        .attr('d', () => linkPathD(fakeSrc, fakeSrc))
        .remove()
    );

  // ── Nodes ─────────────────────────────────────────────────────────────────
  const nodesSel = nodesG.selectAll('g.node')
    .data(root.descendants(), d => pid(d));

  nodesSel.exit()
    .transition().duration(dur).ease(d3.easeCubicInOut)
    .attr('transform', `translate(${srcX},${srcY})`)
    .style('opacity', 0)
    .remove();

  const ne = nodesSel.enter().append('g')
    .attr('class', 'node')
    .attr('transform', `translate(${srcX},${srcY})`)
    .style('opacity', 0)
    .style('cursor', d => d.data._hasKids ? 'pointer' : 'default');

  ne.on('click', (event, d) => {
    event.stopPropagation();
    if (!d.data._hasKids) return;
    stateMap[pid(d)] = !stateMap[pid(d)];
    autoFit = true;   // expand/collapse always re-enables auto-fit
    update(pid(d));
  });

  ne.append('rect')
    .attr('x',      d => -nw(d.data.name, d.data.fontSize) / 2)
    .attr('y',      d => -nh(d.data.name, d.data.fontSize) / 2)
    .attr('width',  d =>  nw(d.data.name, d.data.fontSize))
    .attr('height', d =>  nh(d.data.name, d.data.fontSize))
    .attr('rx', RX).attr('ry', RX)
    .attr('fill',   d => rgba(branchColor(d), d.depth===0 ? 0.45 : (d.data._hasKids ? (darkMode ? 0.20 : 0.15) : (darkMode ? 0.10 : 0.08))))
    .attr('stroke', d => rgba(branchColor(d), d.depth===0 ? 0.90 : (d.data._hasKids ? 0.75 : 0.35)))
    .attr('stroke-width', d => d.depth===0 ? 2 : 1.5);

  // Multiline label using <tspan> per line
  ne.append('text')
    .attr('class', 'node-lbl')
    .attr('text-anchor', 'middle')
    .attr('fill',        () => nodeTextColor())
    .attr('font-size',   d => `${d.data.fontSize || DEFAULT_FS}px`)
    .attr('font-family', "'Atkinson Hyperlegible', sans-serif")
    .attr('font-weight', d => d.depth===0 ? 'bold' : 'normal')
    .style('pointer-events','none')
    .each(function(d) {
      const fs   = d.data.fontSize || DEFAULT_FS;
      const lh   = fs * (LINE_H / DEFAULT_FS);
      const ls   = lines(d.data.name);
      const yOff = -(ls.length - 1) * lh / 2;
      d3.select(this).selectAll('tspan')
        .data(ls)
        .join('tspan')
        .attr('x', 0)
        .attr('dy', (_, i) => i === 0 ? yOff : lh)
        .attr('dominant-baseline', 'central')
        .text(l => l);
    });

  ne.filter(d => d.data._hasKids)
    .append('text')
    .attr('class','ind')
    .attr('x', d =>  nw(d.data.name, d.data.fontSize) / 2 - 11)
    .attr('y', d =>  nh(d.data.name, d.data.fontSize) / 2 - 10)
    .attr('dominant-baseline','central')
    .attr('text-anchor','middle')
    .attr('fill', d => rgba(branchColor(d), 0.75))
    .attr('font-size','9px')
    .style('pointer-events','none')
    .text(d => stateMap[pid(d)] ? '\u25b8' : '\u25be');

  // Link badge: drawn as SVG paths (not a text glyph), so it renders
  // identically regardless of the viewer's fonts/emoji support.
  const linkG = ne.filter(d => d.data.link)
    .append('g')
    .attr('class', 'node-link')
    .style('cursor', 'pointer')
    .attr('transform', d => {
      const hw = nw(d.data.name, d.data.fontSize) / 2;
      const hh = nh(d.data.name, d.data.fontSize) / 2;
      return `translate(${hw - 11},${-hh + 10})`;
    })
    .on('click', (event, d) => {
      event.stopPropagation();
      window.open(d.data.link, '_blank', 'noopener,noreferrer');
    });

  linkG.append('circle')
    .attr('r', 8)
    .attr('fill', 'transparent');

  linkG.append('path')
    .attr('transform', 'scale(0.42) translate(-12,-12)')
    .attr('d', 'M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71')
    .attr('fill', 'none')
    .attr('stroke', d => rgba(branchColor(d), 0.85))
    .attr('stroke-width', 2.4)
    .attr('stroke-linecap', 'round')
    .attr('stroke-linejoin', 'round')
    .style('pointer-events', 'none');

  linkG.append('title')
    .text(d => d.data.link);

  ne.transition().duration(dur).ease(d3.easeCubicInOut)
    .attr('transform', d => `translate(${d.px},${d.py})`)
    .style('opacity', 1);

  nodesSel.transition().duration(dur).ease(d3.easeCubicInOut)
    .attr('transform', d => `translate(${d.px},${d.py})`)
    .style('opacity', 1);

  // Sync text colour on existing nodes when theme changes
  nodesSel.select('text.node-lbl')
    .attr('fill', () => nodeTextColor());

  // Sync rect fill/stroke on existing nodes
  nodesSel.select('rect')
    .attr('fill',   d => rgba(branchColor(d), d.depth===0 ? 0.45 : (d.data._hasKids ? (darkMode ? 0.20 : 0.15) : (darkMode ? 0.10 : 0.08))))
    .attr('stroke', d => rgba(branchColor(d), d.depth===0 ? 0.90 : (d.data._hasKids ? 0.75 : 0.35)));

  nodesSel.select('.ind').text(d => stateMap[pid(d)] ? '\u25b8' : '\u25be');

  // Auto-fit: adjust viewport to show all visible nodes
  if (autoFit) fitToView(root, W, H, dur);

  isFirst = false;
}

// ── Theme toggle ─────────────────────────────────────────────────────────────
let darkMode = {INIT_DARK};

function toggleTheme() {
  darkMode = !darkMode;
  document.documentElement.classList.toggle('light', !darkMode);
  document.getElementById('btn-theme').textContent = darkMode ? '\u2600 Light' : '\u263e Dark';
  // Re-render so node colours update; keep autoFit state as-is
  isFirst = true;
  update(null);
}

function nodeTextColor() {
  return darkMode ? '#e6edf3' : '#1a202c';
}

function linkOpacity() {
  return darkMode ? 0.45 : 0.55;
}

// ── Layout toggle ────────────────────────────────────────────────────────────
function setLayout(l) {
  layout  = l;
  autoFit = true;   // re-enable auto-fit whenever the user changes layout
  ['radial','topdown','horiz'].forEach(id =>
    document.getElementById('btn-'+id).classList.toggle('active', l === id)
  );
  const W = document.getElementById('canvas').clientWidth;
  const H = document.getElementById('canvas').clientHeight;
  svgEl.call(zoomBeh.transform, d3.zoomIdentity);
  centerG.attr('transform', centerTransform(W, H));
  isFirst = true;
  update(null);
}

// ── Expand / Collapse all ────────────────────────────────────────────────────
function setAllStates(collapsed) {
  function walk(node, id) {
    stateMap[id] = collapsed;
    if (node.children) node.children.forEach(c => walk(c, id + '\x01' + c.name));
  }
  walk(RAW, RAW.name);
  autoFit = true;
  isFirst = true;
  update(null);
}

function expandAll()   { setAllStates(false); }
function collapseAll() { setAllStates(true);  }

function toggleSettings(e) {
  e.stopPropagation();
  const wrap = document.getElementById('header-wrap');
  const btn  = document.getElementById('settings-btn');
  const open = wrap.classList.toggle('open');
  btn.classList.toggle('open', open);
}
document.addEventListener('click', function() {
  document.getElementById('header-wrap').classList.remove('open');
  document.getElementById('settings-btn').classList.remove('open');
});

// ── Step sequencing (optional 'order' column) ───────────────────────────────
// Exposes a minimal Reveal.js-compatible surface so this page can be driven
// as a "secondary" presentation by the quarto-splice extension, one node per
// advance keypress. Purely additive: nothing here is triggered by clicking
// or normal use of this page on its own.
const orderNodeId = {};
(function indexOrder(node, id) {
  if (node.order) orderNodeId[node.order] = id;
  if (node.children) node.children.forEach(c => indexOrder(c, id + '\x01' + c.name));
})(RAW, RAW.name);

const maxOrder = Math.max(0, ...Object.keys(orderNodeId).map(Number));
let stepIndex  = 0;
const slidechangedCbs = [];

window.Reveal = {
  getTotalSlides: () => maxOrder + 1,
  getIndices:     () => ({ h: stepIndex }),
  isReady:        () => true,
  on(evt, cb) {
    if (evt === 'ready') cb();
    else if (evt === 'slidechanged') slidechangedCbs.push(cb);
  },
  next() {
    if (stepIndex >= maxOrder) return;
    stepIndex += 1;
    const id = orderNodeId[stepIndex];
    if (id) { stateMap[id] = false; autoFit = true; update(id); }
    slidechangedCbs.forEach(cb => cb({ indexh: stepIndex }));
  },
  prev() {
    if (stepIndex <= 0) return;
    const id = orderNodeId[stepIndex];
    if (id) { stateMap[id] = true; autoFit = true; update(id); }
    stepIndex -= 1;
    slidechangedCbs.forEach(cb => cb({ indexh: stepIndex }));
  },
};

// Standalone fallback: lets the order sequence be stepped through with the
// keyboard when this page is opened on its own (not embedded via splice,
// which drives Reveal.next()/prev() itself and never lets keydown reach
// this document, so this listener is inert in that case).
document.addEventListener('keydown', function (event) {
  const isNext = event.key === 'ArrowRight' || event.key === 'n' || event.key === 'N'
              || (event.key === ' ' && !event.shiftKey);
  const isPrev = event.key === 'ArrowLeft'  || event.key === 'p' || event.key === 'P'
              || (event.key === ' ' && event.shiftKey);
  if (!isNext && !isPrev) return;
  event.preventDefault();
  if (isNext) window.Reveal.next();
  else        window.Reveal.prev();
});

function init() {
  const W = document.getElementById('canvas').clientWidth;
  const H = document.getElementById('canvas').clientHeight;
  centerG.attr('transform', centerTransform(W, H));
  ['radial','topdown','horiz'].forEach(id =>
    document.getElementById('btn-'+id).classList.toggle('active', layout === id)
  );
  if (INIT_EXPAND === 'all')       setAllStates(false);
  else if (INIT_EXPAND === 'none') setAllStates(true);
  else                              update(null);
}

window.addEventListener('resize', () => {
  const W = document.getElementById('canvas').clientWidth;
  const H = document.getElementById('canvas').clientHeight;
  centerG.attr('transform', centerTransform(W, H));
  update(null);
});

init();
</script>
</body>
</html>
"""


# ── Main ──────────────────────────────────────────────────────────────────────

def build_meta_bar(meta: dict) -> str:
    """Build the HTML for the metadata bar, or empty string if no metadata."""
    if not meta:
        return ''
    items = [v.replace('\n', ' · ') for v in meta.values() if v]
    if not items:
        return ''
    inner = '<span class="sep">·</span>'.join(f'<span>{v}</span>' for v in items)
    return f'<div id="meta-bar">{inner}</div>'


def main():
    parser = argparse.ArgumentParser(
        description="arbolito — build an interactive mind-map HTML from a CSV file."
    )
    parser.add_argument('--input',     default='arbolito_mindmap.csv',  help='Input CSV file (default: arbolito_mindmap.csv)')
    parser.add_argument('--output',    default='arbolito_mindmap.html', help='Output HTML file (default: arbolito_mindmap.html)')
    parser.add_argument('--save-json', default=None,           metavar='FILE',
                        help='Also save the intermediate JSON tree to this file')
    parser.add_argument('--layout', choices=['radial', 'topdown', 'horizontal'], default='horizontal',
                        help='Initial layout (default: horizontal)')
    parser.add_argument('--theme',  choices=['light', 'dark'], default='dark',
                        help='Initial theme (default: dark)')
    parser.add_argument('--expand', choices=['all', 'none', 'file'], default='file',
                        help="Initial expand state: 'all' expanded, 'none' collapsed, "
                             "or 'file' to respect each row's collapsed column (default: file)")
    parser.add_argument('--bg', default=None, metavar='COLOR',
                        help="Override the canvas background color with any CSS value "
                             "(e.g. '#1a1a2e', 'transparent'). Applies to both themes.")
    args = parser.parse_args()

    src = Path(args.input)
    dst = Path(args.output)

    if not src.exists():
        raise FileNotFoundError(f"Input file not found: {src}")

    meta, tree = csv_to_meta_and_tree(src)
    json_str   = json.dumps(tree, ensure_ascii=False, indent=2)

    if args.save_json:
        Path(args.save_json).write_text(json_str, encoding='utf-8')
        print(f"JSON saved: {args.save_json}")

    title_val = meta.get('title', '').strip()
    page_title = f"{title_val} - Arbolito Mind Map" if title_val else "Arbolito Mind Map"

    init_layout    = {'radial': 'radial', 'topdown': 'topdown', 'horizontal': 'horiz'}[args.layout]
    init_dark      = 'true' if args.theme == 'dark' else 'false'
    html_class_attr = '' if args.theme == 'dark' else ' class="light"'
    theme_btn_label = '&#9728; Light' if args.theme == 'dark' else '&#9790; Dark'

    bg_override = (f':root, :root.light {{ --bg: {args.bg}; }}\n'
                   if args.bg else '')

    html = TEMPLATE.replace('{JSON_DATA}', json_str)
    html = html.replace('{META_BAR}', build_meta_bar(meta))
    html = html.replace('{TITLE}', html_escape(page_title))
    html = html.replace('{HTML_CLASS_ATTR}', html_class_attr)
    html = html.replace('{THEME_BTN_LABEL}', theme_btn_label)
    html = html.replace('{INIT_LAYOUT}', init_layout)
    html = html.replace('{INIT_DARK}', init_dark)
    html = html.replace('{INIT_EXPAND}', args.expand)
    html = html.replace('{BG_OVERRIDE}', bg_override)
    dst.write_text(html, encoding='utf-8')
    print(f"HTML written: {dst}")


if __name__ == '__main__':
    main()
