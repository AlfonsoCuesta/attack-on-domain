from __future__ import annotations

import json
import typing
import webbrowser
from collections import deque
from tempfile import NamedTemporaryFile

from aod._internal.domain.app import App
from aod._internal.domain.bounded_context import BoundedContext
from aod._internal.domain.describe import MethodDoc, extract_fields, extract_methods
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.service import Service
from aod._internal.domain.value_object import ValueObject

TMPL = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Bounded Context Diagram</title>
<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/dagre@0.8.5/dist/dagre.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/roughjs@4.6.6/bundled/rough.min.js"></script>
<style>"""
INTERACTIVE_TEMPLATE = (
    TMPL
    + """
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #f0f2f5; overflow: hidden; font-family: 'Inter', system-ui, sans-serif; }
  #canvas { position: relative; width: 100vw; height: 100vh; overflow: hidden; cursor: grab; }
  #canvas.panning { cursor: grabbing; }
  #viewport { position: absolute; top: 0; left: 0; width: 100%; height: 100%; transform-origin: 0 0; }
  #rough-layer { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; overflow: visible; }
  #connections-layer { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; overflow: visible; }
  #nodes-layer { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
  #status { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.7); color: #fff; padding: 6px 16px; border-radius: 20px; font-size: 13px; z-index: 100; font-family: 'Inter', sans-serif; pointer-events: none; opacity: 0; transition: opacity 0.3s; }
  #status.visible { opacity: 1; }

  .node-card { position: absolute; display: flex; flex-direction: column; border-radius: 10px; cursor: move; user-select: none; }
  .node-card:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.15) !important; }
  .node-card.dragging { box-shadow: 0 8px 30px rgba(0,0,0,0.25) !important; z-index: 100; }

  .node-header { font-family: 'Caveat', cursive; font-size: 18px; font-weight: 700; padding: 8px 14px 2px; display: flex; align-items: center; gap: 6px; }
  .node-header .root-icon { font-size: 16px; flex-shrink: 0; }
  .node-name { flex-shrink: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .node-badge-row { padding: 0 14px 4px; }
  .node-badge { font-family: 'Inter', sans-serif; font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; padding: 2px 8px; border-radius: 10px; display: inline-block; }

  .node-fields { font-family: 'Inter', monospace; font-size: 11px; padding: 4px 14px 10px; line-height: 1.6; }
  .node-fields .field { color: #555; }
  .node-fields .field-name { color: #333; font-weight: 500; }
  .node-fields .field-type { color: #888; }
  .node-methods { font-family: 'Inter', monospace; font-size: 11px; padding: 0 14px 10px; line-height: 1.6; }
  .node-methods .method-name { color: #E65100; }
  .node-methods .method-param { color: #333; }
  .node-methods .method-type { color: #888; }

  .agg-header { font-family: 'Caveat', cursive; font-size: 16px; font-weight: 600; position: absolute; padding: 4px 12px; border-radius: 8px; white-space: nowrap; cursor: move; pointer-events: auto; }

  .edge-label { font-family: 'Inter', sans-serif; font-size: 10px; fill: #666; }
</style>
</head>
<body>
<div id="canvas">
  <div id="viewport">
    <svg id="rough-layer" width="100%" height="100%"></svg>
    <svg id="connections-layer" width="100%" height="100%">
      <defs>
        <marker id="arrowhead-ctx-0" viewBox="0 0 14 10" refX="12" refY="5" markerWidth="10" markerHeight="8" orient="auto">
          <path d="M 0 0 L 12 5 L 0 10 Z" fill="#1a237e"/>
        </marker>
        <marker id="arrowhead-ctx-1" viewBox="0 0 14 10" refX="12" refY="5" markerWidth="10" markerHeight="8" orient="auto">
          <path d="M 0 0 L 12 5 L 0 10 Z" fill="#1b5e20"/>
        </marker>
        <marker id="arrowhead-ctx-2" viewBox="0 0 14 10" refX="12" refY="5" markerWidth="10" markerHeight="8" orient="auto">
          <path d="M 0 0 L 12 5 L 0 10 Z" fill="#e65100"/>
        </marker>
        <marker id="arrowhead-ctx-3" viewBox="0 0 14 10" refX="12" refY="5" markerWidth="10" markerHeight="8" orient="auto">
          <path d="M 0 0 L 12 5 L 0 10 Z" fill="#4a148c"/>
        </marker>
        <marker id="arrowhead-ctx-4" viewBox="0 0 14 10" refX="12" refY="5" markerWidth="10" markerHeight="8" orient="auto">
          <path d="M 0 0 L 12 5 L 0 10 Z" fill="#880e4f"/>
        </marker>
        <marker id="arrowhead-shared" viewBox="0 0 14 10" refX="12" refY="5" markerWidth="10" markerHeight="8" orient="auto">
          <path d="M 0 0 L 12 5 L 0 10 Z" fill="#e65100"/>
        </marker>
      </defs>
    </svg>
    <div id="nodes-layer"></div>
  </div>
</div>
<div id="status"></div>
<script>
var DATA = __DATA__;

var ctxColors = [
  { bg: '#e3f2fd', border: '#1a237e', fill: '#bbdefb', light: '#f0f7ff' },
  { bg: '#e8f5e9', border: '#1b5e20', fill: '#c8e6c9', light: '#f1faf1' },
  { bg: '#fff3e0', border: '#e65100', fill: '#ffe0b2', light: '#fffaf5' },
  { bg: '#f3e5f5', border: '#4a148c', fill: '#e1bee7', light: '#faf5fc' },
  { bg: '#fce4ec', border: '#880e4f', fill: '#f8bbd0', light: '#fdf5f7' },
];

var sharedColor = { bg: '#fffde7', border: '#e65100', fill: '#fff9c4', light: '#fffef0' };

var stereoColors = {
  'RootEntity': { bg: '#e8dff5', border: '#7c4dff', text: '#4a148c' },
  'Entity': { bg: '#e3f2fd', border: '#42a5f5', text: '#1565c0' },
  'ValueObject': { bg: '#e8f5e9', border: '#66bb6a', text: '#2e7d32' },
  'Service': { bg: '#fff3e0', border: '#ffa726', text: '#e65100' },
};

var nodeLookup = {};
DATA.nodes.forEach(function(n) { nodeLookup[n.name] = n; });

var ctxColorsBorder = ctxColors.map(function(c) { return c.border; });

// ── dagre layout ─────────────────────────────────────────────

function runLayout() {
  var g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: 'TB', nodesep: 50, ranksep: 60, marginx: 40, marginy: 40 });
  g.setDefaultEdgeLabel(function() { return {}; });

  DATA.nodes.forEach(function(n) {
    g.setNode(n.name, { width: n.width, height: n.height });
  });
  DATA.edges.forEach(function(e) {
    g.setEdge(e.from, e.to, { label: e.label });
  });

  dagre.layout(g);

  DATA.nodes.forEach(function(n) {
    var dn = g.node(n.name);
    n.x = dn ? dn.x - n.width / 2 : 100;
    n.y = dn ? dn.y - n.height / 2 : 100;
  });

  separateContexts();
}

function separateContexts() {
  var ctxGroups = {};
  DATA.nodes.forEach(function(n) {
    if (!ctxGroups[n.context]) ctxGroups[n.context] = [];
    ctxGroups[n.context].push(n);
  });

  var indices = Object.keys(ctxGroups).sort();
  if (indices.length <= 1) return;

  var bounds = {};
  indices.forEach(function(idx) {
    var minX = Infinity, maxX = -Infinity;
    ctxGroups[idx].forEach(function(n) {
      if (n.x < minX) minX = n.x;
      if (n.x + n.width > maxX) maxX = n.x + n.width;
    });
    bounds[idx] = { minX: minX, maxX: maxX };
  });

  var gap = 200;
  var sorted = indices.slice().sort(function(a, b) {
    return (bounds[a].minX + bounds[a].maxX) - (bounds[b].minX + bounds[b].maxX);
  });

  var shiftX = 0;
  sorted.forEach(function(idx, i) {
    if (i === 0) { shiftX = bounds[idx].maxX; return; }
    var prevMax = shiftX;
    var need = prevMax + gap - bounds[idx].minX;
    if (need > 0) {
      ctxGroups[idx].forEach(function(n) { n.x += need; });
      bounds[idx].minX += need;
      bounds[idx].maxX += need;
    }
    shiftX = bounds[idx].maxX;
  });
}

// ── Geometry ─────────────────────────────────────────────────

function getRectEdge(rx, ry, rw, rh, tx, ty) {
  var cx = rx + rw / 2;
  var cy = ry + rh / 2;
  var dx = tx - cx;
  var dy = ty - cy;
  if (dx === 0 && dy === 0) return { x: cx, y: cy };
  var adx = Math.abs(dx);
  var ady = Math.abs(dy);
  var hw = rw / 2, hh = rh / 2;
  var ix, iy;
  if (adx * hh > ady * hw) {
    ix = dx > 0 ? hw : -hw;
    iy = (ix / dx) * dy || 0;
  } else {
    iy = dy > 0 ? hh : -hh;
    ix = (iy / dy) * dx || 0;
  }
  return { x: cx + ix, y: cy + iy };
}

function edgePoint(e, x, y) {
  var path = e.group.querySelector('path');
  if (!path) return;
  var fromN = e.from, toN = e.to;
  var fpt = getRectEdge(fromN.x, fromN.y, fromN.w, fromN.h, toN.x + toN.w/2, toN.y + toN.h/2);
  var tpt = getRectEdge(toN.x, toN.y, toN.w, toN.h, fromN.x + fromN.w/2, fromN.y + fromN.h/2);
  var mx = (fpt.x + tpt.x) / 2;
  var my = (fpt.y + tpt.y) / 2;
  var dx = tpt.y - fpt.y;
  var dy = -(tpt.x - fpt.x);
  var len = Math.sqrt(dx*dx + dy*dy) || 1;
  var off = Math.min(40, Math.max(10, (tpt.x - fpt.x) * 0.1));
  var cpx = mx + (dx / len) * off;
  var cpy = my + (dy / len) * off;
  path.setAttribute('d', 'M ' + fpt.x + ' ' + fpt.y + ' Q ' + cpx + ' ' + cpy + ' ' + tpt.x + ' ' + tpt.y);
  var label = e.group.querySelector('text');
  if (label) { label.setAttribute('x', cpx); label.setAttribute('y', cpy - 8); }
}

function stereoLabel(s) {
  var map = { RootEntity: 'AGGREGATE ROOT', Entity: 'ENTITY', ValueObject: 'VALUE OBJECT', Service: 'SERVICE' };
  return map[s] || s;
}

function aggColor(rootName) {
  var info = nodeLookup[rootName];
  return (info && info.is_shared) ? sharedColor : ctxColors[info ? info.context % ctxColors.length : 0];
}

// ── State ────────────────────────────────────────────────────

var nodes = {};
var nodeEls = {};
var edgeList = [];
var zoom = 1, panX = 0, panY = 0;
var isPanning = false, panStartX, panStartY;

// Drag state
var dragTarget = null;       // 'node' | 'agg' | null
var dragNodeName = null;
var dragAggRoot = null;
var dragStartX, dragStartY, dragOrigX, dragOrigY, dragOffsets = {};

// DOM refs
var canvasEl = document.getElementById('canvas');
var viewport = document.getElementById('viewport');
var roughLayer = document.getElementById('rough-layer');
var connLayer = document.getElementById('connections-layer');
var nodesLayer = document.getElementById('nodes-layer');
var statusEl = document.getElementById('status');

// ── Status ───────────────────────────────────────────────────

function setStatus(msg) {
  statusEl.innerHTML = msg;
  statusEl.classList.add('visible');
  clearTimeout(statusEl._timer);
  statusEl._timer = setTimeout(function() { statusEl.classList.remove('visible'); }, 2000);
}

// ── Render nodes ─────────────────────────────────────────────

function renderNodes() {
  DATA.nodes.forEach(function(n) {
    var el = document.createElement('div');
    el.className = 'node-card';
    el.style.left = n.x + 'px';
    el.style.top = n.y + 'px';
    el.style.width = n.width + 'px';

    var color = (n.is_shared ? sharedColor : ctxColors[n.context % ctxColors.length]);
    el.style.background = color.bg;
    el.style.border = '1.5px solid ' + color.border;
    el.style.boxShadow = '0 2px 8px rgba(0,0,0,0.06)';

    var sc = stereoColors[n.stereo] || { bg: '#f5f5f5', border: '#999', text: '#666' };

    var header = document.createElement('div');
    header.className = 'node-header';
    if (n.stereo === 'RootEntity') {
      var icon = document.createElement('span');
      icon.className = 'root-icon';
      icon.textContent = '\u2605';
      icon.style.color = sc.border;
      header.appendChild(icon);
    }
    var nameSpan = document.createElement('span');
    nameSpan.className = 'node-name';
    nameSpan.style.color = sc.text;
    nameSpan.textContent = n.display;
    header.appendChild(nameSpan);
    el.appendChild(header);

    var badgeRow = document.createElement('div');
    badgeRow.className = 'node-badge-row';
    var badge = document.createElement('span');
    badge.className = 'node-badge';
    badge.textContent = stereoLabel(n.stereo);
    badge.style.background = sc.bg;
    badge.style.color = sc.border;
    badge.style.border = '1px solid ' + sc.border;
    badgeRow.appendChild(badge);
    el.appendChild(badgeRow);

    if (n.fields && n.fields.length) {
      var fields = document.createElement('div');
      fields.className = 'node-fields';
      n.fields.forEach(function(f) {
        var row = document.createElement('div');
        row.className = 'field';
        var ne = document.createElement('span');
        ne.className = 'field-name';
        ne.textContent = f.name;
        row.appendChild(ne);
        if (f.type) {
          row.appendChild(document.createTextNode(': '));
          var te = document.createElement('span');
          te.className = 'field-type';
          te.textContent = f.type;
          row.appendChild(te);
        }
        fields.appendChild(row);
      });
      el.appendChild(fields);
    }

    if (n.methods && n.methods.length) {
      var methods = document.createElement('div');
      methods.className = 'node-methods';
      n.methods.forEach(function(m) {
        var row = document.createElement('div');
        row.className = 'method';
        var ne = document.createElement('span');
        ne.className = 'method-name';
        ne.textContent = m.name;
        row.appendChild(ne);
        row.appendChild(document.createTextNode('('));
        if (m.params && m.params.length) {
          m.params.forEach(function(p, i) {
            if (i > 0) row.appendChild(document.createTextNode(', '));
            if (p.type) {
              var te = document.createElement('span');
              te.className = 'method-type';
              te.textContent = p.type;
              row.appendChild(te);
              row.appendChild(document.createTextNode(' '));
            }
            var pn = document.createElement('span');
            pn.className = 'method-param';
            pn.textContent = p.name;
            row.appendChild(pn);
          });
        }
        row.appendChild(document.createTextNode(')'));
        if (m.returns) {
          row.appendChild(document.createTextNode(': '));
          var re = document.createElement('span');
          re.className = 'method-type';
          re.textContent = m.returns;
          row.appendChild(re);
        }
        methods.appendChild(row);
      });
      el.appendChild(methods);
    }

    nodesLayer.appendChild(el);

    var h = el.offsetHeight || n.height;
    nodes[n.name] = { x: n.x, y: n.y, w: n.width, h: h };
    nodeEls[n.name] = el;
  });
}

// ── Render aggregate containers (rough.js) ─────────────────

function renderAggContainers() {
  if (typeof rough === 'undefined') { console.warn('rough.js not loaded'); return; }
  var existing = roughLayer.querySelectorAll('.agg-rough');
  for (var i = 0; i < existing.length; i++) existing[i].remove();
  var hdrs = nodesLayer.querySelectorAll('.agg-header');
  for (var i = 0; i < hdrs.length; i++) hdrs[i].remove();

  var rc = rough.svg(roughLayer, { roughness: 1.8, bowing: 1, strokeWidth: 2 });

  Object.keys(DATA.aggregates).forEach(function(rootName) {
    var children = DATA.aggregates[rootName];
    var allNames = [rootName].concat(children);
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    allNames.forEach(function(name) {
      var nd = nodes[name];
      if (!nd) return;
      if (nd.x < minX) minX = nd.x;
      if (nd.y < minY) minY = nd.y;
      if (nd.x + nd.w > maxX) maxX = nd.x + nd.w;
      if (nd.y + nd.h > maxY) maxY = nd.y + nd.h;
    });
    if (minX === Infinity) return;

    var pad = 30;
    var cx = minX - pad, cy = minY - pad;
    var cw = maxX - minX + pad * 2, ch = maxY - minY + pad * 2;
    var color = aggColor(rootName);

    var rect = rc.rectangle(cx, cy, cw, ch, {
      fill: color.light, fillStyle: 'solid',
      stroke: color.border, strokeWidth: 2,
      roughness: 2, bowing: 1.5,
    });
    rect.setAttribute('class', 'agg-rough');
    rect.setAttribute('data-root', rootName);
    roughLayer.appendChild(rect);

    var header = document.createElement('div');
    header.className = 'agg-header';
    header.textContent = (nodeLookup[rootName] ? nodeLookup[rootName].display : rootName) + ' Aggregate';
    header.style.cssText = [
      'left:' + (cx + 14) + 'px',
      'top:' + (cy + 10) + 'px',
      'background:' + color.border,
      'color:#fff',
      'border-radius:8px',
      'pointer-events:auto',
      'z-index:10',
    ].join(';');
    header.setAttribute('data-root', rootName);
    nodesLayer.appendChild(header);
  });
}

// ── Render bounded context containers (rough.js) ────────────

function renderBoundedContexts() {
  if (typeof rough === 'undefined') { console.warn('rough.js not loaded'); return; }
  var existing = roughLayer.querySelectorAll('.ctx-rough');
  for (var i = 0; i < existing.length; i++) existing[i].remove();
  var hdrs = nodesLayer.querySelectorAll('.ctx-header');
  for (var i = 0; i < hdrs.length; i++) hdrs[i].remove();

  var ctxGroups = {};
  DATA.nodes.forEach(function(n) {
    if (!ctxGroups[n.context]) ctxGroups[n.context] = [];
    ctxGroups[n.context].push(n);
  });

  var rc = rough.svg(roughLayer, { roughness: 1.2, bowing: 1, strokeWidth: 1.5 });

  Object.keys(ctxGroups).forEach(function(ctxIdx) {
    var group = ctxGroups[ctxIdx];
    var color = ctxColors[ctxIdx % ctxColors.length];

    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    group.forEach(function(n) {
      var nd = nodes[n.name];
      if (!nd) return;
      if (nd.x < minX) minX = nd.x;
      if (nd.y < minY) minY = nd.y;
      if (nd.x + nd.w > maxX) maxX = nd.x + nd.w;
      if (nd.y + nd.h > maxY) maxY = nd.y + nd.h;
    });
    if (minX === Infinity) return;

    var pad = 50;
    var cx = minX - pad, cy = minY - pad;
    var cw = maxX - minX + pad * 2, ch = maxY - minY + pad * 2;

    var rect = rc.rectangle(cx, cy, cw, ch, {
      fill: color.light, fillStyle: 'solid',
      stroke: color.border, strokeWidth: 2,
      roughness: 1.5, bowing: 1,
    });
    rect.setAttribute('class', 'ctx-rough');
    rect.setAttribute('data-ctx', ctxIdx);
    roughLayer.appendChild(rect);

    var title = document.createElement('div');
    title.className = 'ctx-header';
    title.textContent = (DATA.context_names && DATA.context_names[ctxIdx]) || 'Context ' + ctxIdx;
    title.style.cssText = [
      'left:' + (cx + 16) + 'px',
      'top:' + (cy + 10) + 'px',
      'background:' + color.border,
      'color:#fff',
      'padding:4px 14px',
      'border-radius:8px',
      'font-family:Caveat,cursive',
      'font-size:15px',
      'font-weight:600',
      'position:absolute',
      'pointer-events:none',
      'z-index:5',
    ].join(';');
    nodesLayer.appendChild(title);
  });
}

// ── Build / redraw edges ─────────────────────────────────────

function buildEdges() {
  var existing = connLayer.querySelectorAll('.edge-group');
  for (var i = 0; i < existing.length; i++) existing[i].remove();
  edgeList = [];

  DATA.edges.forEach(function(e) {
    var fromN = nodes[e.from], toN = nodes[e.to];
    if (!fromN || !toN) return;

    var info = nodeLookup[e.from] || nodeLookup[e.to] || { context: 0, is_shared: false };
    var edgeColor = info.is_shared ? '#e65100' : ctxColors[info.context % ctxColors.length].border;
    var markerId = info.is_shared ? 'arrowhead-shared' : ('arrowhead-ctx-' + (info.context % 5));
    var label = e.label || '';
    if (e.via === 'list') label += ' : list';

    var fpt = getRectEdge(fromN.x, fromN.y, fromN.w, fromN.h, toN.x + toN.w/2, toN.y + toN.h/2);
    var tpt = getRectEdge(toN.x, toN.y, toN.w, toN.h, fromN.x + fromN.w/2, fromN.y + fromN.h/2);
    var mx = (fpt.x + tpt.x) / 2, my = (fpt.y + tpt.y) / 2;
    var dx = tpt.y - fpt.y, dy = -(tpt.x - fpt.x);
    var len = Math.sqrt(dx*dx + dy*dy) || 1;
    var off = Math.min(40, Math.max(10, (tpt.x - fpt.x) * 0.1));
    var cpx = mx + (dx / len) * off, cpy = my + (dy / len) * off;

    var group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.setAttribute('class', 'edge-group');

    var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'M ' + fpt.x + ' ' + fpt.y + ' Q ' + cpx + ' ' + cpy + ' ' + tpt.x + ' ' + tpt.y);
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', edgeColor);
    path.setAttribute('stroke-width', '2');
    path.setAttribute('marker-end', 'url(#' + markerId + ')');
    path.setAttribute('opacity', '0.8');
    group.appendChild(path);

    if (label) {
      var lbl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      lbl.setAttribute('x', cpx);
      lbl.setAttribute('y', cpy - 10);
      lbl.setAttribute('text-anchor', 'middle');
      lbl.setAttribute('class', 'edge-label');
      lbl.setAttribute('fill', edgeColor);
      lbl.setAttribute('opacity', '0.85');
      lbl.textContent = label;
      group.appendChild(lbl);
    }

    connLayer.appendChild(group);
    edgeList.push({ group: group, from: fromN, to: toN, label: label });
  });
}

function redrawEdges() {
  if (!edgeList.length) { try { buildEdges(); } catch(e) { console.warn('Edges:', e); } return; }
  edgeList.forEach(function(e) { edgePoint(e); });
}

// ── Transform ────────────────────────────────────────────────

function updateTransform() {
  viewport.style.transform = 'translate(' + panX + 'px, ' + panY + 'px) scale(' + zoom + ')';
}

// ── Drag system (single document-level handlers) ─────────────

document.addEventListener('mousemove', function(e) {
  var dz = zoom || 1;
  if (dragTarget === 'node' || dragTarget === 'agg') {
    var dx = (e.clientX - dragStartX) / dz;
    var dy = (e.clientY - dragStartY) / dz;
    if (dragTarget === 'node' && dragNodeName) {
      var nd = nodes[dragNodeName];
      nd.x = dragOrigX + dx;
      nd.y = dragOrigY + dy;
      var el = nodeEls[dragNodeName];
      if (el) { el.style.left = nd.x + 'px'; el.style.top = nd.y + 'px'; }
      redrawEdges();
      renderBoundedContexts();
      renderAggContainers();
    } else if (dragTarget === 'agg' && dragAggRoot) {
      var allNames = [dragAggRoot].concat(DATA.aggregates[dragAggRoot] || []);
      allNames.forEach(function(name) {
        var nd = nodes[name];
        if (!nd) return;
        nd.x = (dragOffsets[name] ? dragOffsets[name].ox : nd.x) + dx;
        nd.y = (dragOffsets[name] ? dragOffsets[name].oy : nd.y) + dy;
        var el = nodeEls[name];
        if (el) { el.style.left = nd.x + 'px'; el.style.top = nd.y + 'px'; }
      });
      redrawEdges();
      renderBoundedContexts();
      renderAggContainers();
    }
  } else if (isPanning) {
    panX = e.clientX - panStartX;
    panY = e.clientY - panStartY;
    updateTransform();
  }
});

document.addEventListener('mouseup', function(e) {
  if (dragTarget) {
    dragTarget = null;
    dragNodeName = null;
    dragAggRoot = null;
    dragOffsets = {};
    Object.keys(nodeEls).forEach(function(name) {
      var el = nodeEls[name];
      if (el) el.classList.remove('dragging');
    });
  }
  if (isPanning) {
    isPanning = false;
    canvasEl.classList.remove('panning');
  }
});

// ── Node mousedown (via delegation on nodes-layer) ───────────

nodesLayer.addEventListener('mousedown', function(e) {
  var el = e.target.closest('.node-card');
  if (!el) return;
  var name = null;
  for (var k in nodeEls) { if (nodeEls[k] === el) { name = k; break; } }
  if (!name) return;

  var nd = nodes[name];
  if (!nd) return;

  // If clicking the header of a RootEntity that has children → delegate to agg-header
  var info = nodeLookup[name];
  if (info && info.stereo === 'RootEntity' && DATA.aggregates[name] && e.target.closest('.node-header')) {
    // let the agg-header mousedown handle it
    return;
  }

  dragTarget = 'node';
  dragNodeName = name;
  dragStartX = e.clientX;
  dragStartY = e.clientY;
  dragOrigX = nd.x;
  dragOrigY = nd.y;
  el.classList.add('dragging');
  setStatus('Dragging <i>' + ((nodeLookup[name] && nodeLookup[name].display) || name) + '</i>');
  e.stopPropagation();
});

// ── Aggregate header mousedown (via delegation on rough-layer) ──

roughLayer.addEventListener('mousedown', function(e) {
  var hdr = e.target.closest('.agg-header');
  if (!hdr) return;
  var rootName = hdr.getAttribute('data-root');
  if (!rootName) return;

  dragTarget = 'agg';
  dragAggRoot = rootName;
  dragStartX = e.clientX;
  dragStartY = e.clientY;
  var allNames = [rootName].concat(DATA.aggregates[rootName] || []);
  dragOffsets = {};
  allNames.forEach(function(name) {
    var nd = nodes[name];
    if (nd) dragOffsets[name] = { ox: nd.x, oy: nd.y };
  });
  allNames.forEach(function(name) {
    var el = nodeEls[name];
    if (el) el.classList.add('dragging');
  });
  setStatus('Dragging aggregate <i>' + ((nodeLookup[rootName] && nodeLookup[rootName].display) || rootName) + '</i>');
  e.stopPropagation();
});

// ── Canvas pan ───────────────────────────────────────────────

canvasEl.addEventListener('mousedown', function(e) {
  if (e.button === 1 || (e.button === 0 && e.ctrlKey)) {
    isPanning = true;
    panStartX = e.clientX - panX;
    panStartY = e.clientY - panY;
    canvasEl.classList.add('panning');
    e.preventDefault();
  }
});

canvasEl.addEventListener('wheel', function(e) {
  e.preventDefault();
  var delta = e.deltaY > 0 ? 0.9 : 1.1;
  var nz = Math.max(0.2, Math.min(5, zoom * delta));
  var mx = e.clientX, my = e.clientY;
  panX = mx - (mx - panX) * (nz / zoom);
  panY = my - (my - panY) * (nz / zoom);
  zoom = nz;
  updateTransform();
}, { passive: false });

// ── Fit to view ──────────────────────────────────────────────

function fitToView() {
  if (!DATA.nodes.length) return;
  var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  DATA.nodes.forEach(function(n) {
    var nd = nodes[n.name];
    if (!nd) return;
    if (nd.x < minX) minX = nd.x;
    if (nd.y < minY) minY = nd.y;
    if (nd.x + nd.w > maxX) maxX = nd.x + nd.w;
    if (nd.y + nd.h > maxY) maxY = nd.y + nd.h;
  });
  if (minX === Infinity) return;
  var pad = 80;
  var contentW = maxX - minX + pad * 2;
  var contentH = maxY - minY + pad * 2;
  var viewW = canvasEl.clientWidth;
  var viewH = canvasEl.clientHeight;
  if (!viewW || !viewH) return;
  var scaleX = viewW / contentW;
  var scaleY = viewH / contentH;
  zoom = Math.min(scaleX, scaleY, 1.2);
  panX = (viewW - (minX + maxX) * zoom) / 2;
  panY = (viewH - (minY + maxY) * zoom) / 2;
  updateTransform();
}

// ── Init ─────────────────────────────────────────────────────

runLayout();
renderNodes();
try { buildEdges(); } catch(e) { console.warn('Edges:', e); }
try { renderBoundedContexts(); } catch(e) { console.warn('Bounded contexts:', e); }
try { renderAggContainers(); } catch(e) { console.warn('Rough containers:', e); }
fitToView();
setStatus('Ready — drag nodes, scroll to zoom, Ctrl+drag to pan');
</script>
</body>
</html>"""
)


# ---------------------------------------------------------------------------
# Graph model — unified across bounded contexts
# ---------------------------------------------------------------------------


class _Node:
    def __init__(self, name: str, display: str, context_idx: int, cls: type) -> None:
        self.name = name
        self.display = display
        self.context_idx = context_idx
        self.cls = cls
        self.fields: dict[str, tuple[str, list[str]]] = {}
        self.methods: list[MethodDoc] = extract_methods(cls)
        self.outgoing: list[tuple[str, str]] = []

    def stereo(self) -> str:
        if issubclass(self.cls, RootEntity):
            return "RootEntity"
        if issubclass(self.cls, Entity):
            return "Entity"
        if issubclass(self.cls, ValueObject):
            return "ValueObject"
        if issubclass(self.cls, Service):
            return "Service"
        return ""

    def is_root_entity(self) -> bool:
        return self.stereo() == "RootEntity"

    def all_field_names(self) -> set[str]:
        return {fd.name for fd in extract_fields(self.cls)}


def _build_graph(*contexts: BoundedContext) -> dict[str, _Node]:
    nodes: dict[str, _Node] = {}

    for ctx_idx, ctx in enumerate(contexts):
        all_types: list = (
            list(ctx.aggregate_roots)
            + list(ctx.entities)
            + list(ctx.value_objects)
            + list(ctx.services)
        )
        local_map: dict[str, str] = {}
        for cls in all_types:
            key = f"ctx{ctx_idx}.{cls.__name__}"
            local_map[cls.__name__] = key
            nodes[key] = _Node(
                name=key,
                display=cls.__name__,
                context_idx=ctx_idx,
                cls=cls,
            )

        for cls in all_types:
            key = local_map[cls.__name__]
            node = nodes[key]
            for fd in extract_fields(cls):
                ref_keys: list[str] = []
                for t in fd.types:
                    if hasattr(t, "__name__") and t.__name__ in local_map:
                        ref_keys.append(local_map[t.__name__])
                node.fields[fd.name] = (fd.type_name, ref_keys)
                for ref_key in ref_keys:
                    node.outgoing.append((fd.name, ref_key))

    return nodes


def _compute_aggregate_groups(nodes: dict[str, _Node]) -> dict[str, list[str]]:
    roots = [n for n in nodes.values() if n.is_root_entity()]
    groups: dict[str, list[str]] = {}
    assigned: set[str] = set()

    for root in roots:
        children: list[str] = []
        queue = deque([root.name])
        visited = {root.name}
        while queue:
            current = queue.popleft()
            node = nodes[current]
            for _, target in node.outgoing:
                if target in nodes and target not in visited:
                    visited.add(target)
                    target_node = nodes[target]
                    if target_node.stereo() in ("Entity", "ValueObject"):
                        if target not in assigned:
                            assigned.add(target)
                            children.append(target)
                            queue.append(target)
        if children:
            groups[root.name] = children

    return groups


def _estimate_node_size(node: _Node) -> tuple[int, int]:
    fnames = sorted(node.all_field_names())
    num = len(fnames)
    max_len = max((len(f) for f in fnames), default=0)
    for fname in fnames:
        finfo = node.fields.get(fname)
        if finfo:
            max_len = max(max_len, len(f"{fname}: {finfo[0]}"))
    for m in node.methods:
        sig = m.name
        if m.params:
            parts = [f"{p.name}: {p.type_name}" if p.type_name else p.name for p in m.params]
            sig += f"({', '.join(parts)})"
        else:
            sig += "()"
        if m.returns:
            sig += f" -> {m.returns}"
        max_len = max(max_len, len(sig))
    width = max(180, min(380, max_len * 7.5 + 60))
    extra = len(node.methods) * 21 if node.methods else 0
    height = 68 + num * 21 + extra
    return int(width), int(height)


def _method_to_dict(m: MethodDoc) -> dict[str, object]:
    return {
        "name": m.name,
        "params": [{"name": p.name, "type": p.type_name} for p in m.params],
        "returns": m.returns,
    }


def _serialize(nodes: dict[str, _Node], context_names: list[str] | None = None) -> dict:
    agg_groups = _compute_aggregate_groups(nodes)

    all_node_names = set(nodes.keys())

    node_list: list[dict] = []
    for name, node in nodes.items():
        w, h = _estimate_node_size(node)

        fields = []
        for fname in sorted(node.all_field_names()):
            finfo = node.fields.get(fname)
            if not finfo:
                continue
            tname, ref_keys = finfo
            in_graph = [r for r in ref_keys if r in all_node_names]
            if in_graph:
                continue
            fields.append({"name": fname, "type": tname})

        node_list.append(
            {
                "name": name,
                "display": node.display,
                "stereo": node.stereo(),
                "context": node.context_idx,
                "is_shared": False,
                "fields": fields,
                "methods": [_method_to_dict(m) for m in node.methods],
                "width": w,
                "height": h,
            }
        )

    edge_list: list[dict] = []
    for name, node in nodes.items():
        for fname, ref_key in node.outgoing:
            if ref_key not in nodes:
                continue
            finfo = node.fields.get(fname)
            tname = finfo[0] if finfo else ""
            is_list = tname.lower().startswith("list")
            edge_list.append(
                {
                    "from": name,
                    "to": ref_key,
                    "label": fname,
                    "via": "list" if is_list else "ref",
                }
            )

    return {
        "nodes": node_list,
        "edges": edge_list,
        "aggregates": agg_groups,
        "context_names": context_names or [],
    }


def render_html(*args: BoundedContext | App) -> str:
    if len(args) == 1 and isinstance(args[0], App):
        contexts = list(args[0].contexts)
    else:
        contexts = [typing.cast(BoundedContext, a) for a in args]
    ctx_names = [c.name or f"Context {i}" for i, c in enumerate(contexts)]
    nodes = _build_graph(*contexts)
    data = _serialize(nodes, ctx_names)
    return INTERACTIVE_TEMPLATE.replace("__DATA__", json.dumps(data))


def show(*args: BoundedContext | App) -> None:
    html_content = render_html(*args)
    with NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
        f.write(html_content)
        path = f.name
    webbrowser.open(f"file://{path}")
    print(f"Diagram opened in browser. Saved to {path}")
