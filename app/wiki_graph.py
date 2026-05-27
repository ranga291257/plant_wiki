"""Build an interactive wiki link graph (pyvis) from markdown internal links."""
from __future__ import annotations

import math
import re
import tempfile
from pathlib import Path

import networkx as nx
from pyvis.network import Network

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

GROUP_COLORS: dict[str, str] = {
    "concepts": "#2d6a4f",
    "entities": "#1b5e3b",
    "mocs": "#40916c",
    "sources": "#52b788",
    "analyses": "#74c69d",
    "guides": "#95d5b2",
    "archive": "#b7e4c7",
    "other": "#6c757d",
}

EMPTY_WIKI_HTML = """<!doctype html>
<html lang="en"><head><meta charset="UTF-8"/><title>Plant Wiki Graph</title></head>
<body style="font-family:system-ui,sans-serif;padding:2rem;color:#1a2e1a;">
<h1>Wiki graph</h1>
<p>No wiki pages found. Run <strong>Convert all</strong> or <strong>Scaffold only</strong> first, then reopen this page.</p>
<p><a href="/">Back to control panel</a></p>
</body></html>"""


def _title_from_file(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    except OSError:
        pass
    return path.stem.replace("-", " ").replace("_", " ").title()


def _node_hover_title(rel_path: str, page: Path | None = None) -> str:
    """Full name + path for tooltip; kept off the canvas to reduce clutter."""
    if page is not None:
        heading = _title_from_file(page)
    else:
        heading = Path(rel_path).stem.replace("-", " ").title()
    return f"{heading}\n{rel_path}"


ENTITY_LABEL_FONT = 9
ENTITY_NODE_SIZE = 20
CONCEPT_LABEL_FONT = 8
CONCEPT_NODE_SIZE = 18
DEFAULT_NODE_SIZE = 16
LABEL_MAX_LEN = 18


def _truncate_label(text: str, max_len: int = LABEL_MAX_LEN) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _entity_canvas_label(rel_path: str) -> str:
    """Short tag for entities (e.g. tt-102, fcv-103)."""
    stem = Path(rel_path).stem
    if stem.endswith("-corpus"):
        return "corpus"
    return _truncate_label(stem, max_len=14)


def _concept_canvas_label(rel_path: str, page: Path | None = None) -> str:
    """Readable short label for concepts (title or humanized slug)."""
    if page is not None:
        return _truncate_label(_title_from_file(page))
    stem = Path(rel_path).stem.replace("-", " ")
    return _truncate_label(stem)


def _node_visual_attrs(rel_path: str, page: Path | None = None) -> dict[str, object]:
    group = _node_group(rel_path)
    label_font = {"face": "arial", "color": "#1a2e1a"}
    if group == "entities":
        return {
            "label": _entity_canvas_label(rel_path),
            "font": {**label_font, "size": ENTITY_LABEL_FONT},
            "size": ENTITY_NODE_SIZE,
        }
    if group == "concepts":
        return {
            "label": _concept_canvas_label(rel_path, page),
            "font": {**label_font, "size": CONCEPT_LABEL_FONT},
            "size": CONCEPT_NODE_SIZE,
        }
    return {
        "label": "\u200b",  # zero-width space (pyvis replaces empty label with node id)
        "font": {"size": 0},
        "size": DEFAULT_NODE_SIZE,
    }


def _wiki_rel(path: Path, wiki_root: Path) -> str:
    return path.relative_to(wiki_root).as_posix()


def _node_group(rel_path: str) -> str:
    parts = rel_path.split("/")
    if len(parts) > 1 and parts[0] in GROUP_COLORS:
        return parts[0]
    return "other"


def _should_skip_page(path: Path, wiki_root: Path) -> bool:
    rel = path.relative_to(wiki_root)
    if any(part.startswith(".") for part in rel.parts):
        return True
    return False


def iter_wiki_pages(wiki_root: Path) -> list[Path]:
    if not wiki_root.exists():
        return []
    pages = [
        p
        for p in sorted(wiki_root.rglob("*.md"))
        if p.is_file() and not _should_skip_page(p, wiki_root)
    ]
    return pages


def collect_edges(wiki_root: Path, pages: list[Path]) -> list[tuple[str, str]]:
    wiki_resolved = wiki_root.resolve()
    edges: list[tuple[str, str]] = []
    for page in pages:
        source = _wiki_rel(page, wiki_root)
        try:
            text = page.read_text(encoding="utf-8")
        except OSError:
            continue
        for target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "#")):
                continue
            resolved = (page.parent / target).resolve()
            try:
                target_rel = resolved.relative_to(wiki_resolved)
            except ValueError:
                continue
            if not resolved.is_file():
                continue
            edges.append((source, target_rel.as_posix()))
    return edges


def build_networkx_graph(wiki_root: Path) -> nx.DiGraph | None:
    pages = iter_wiki_pages(wiki_root)
    if not pages:
        return None

    graph: nx.DiGraph = nx.DiGraph()
    for page in pages:
        rel = _wiki_rel(page, wiki_root)
        group = _node_group(rel)
        visuals = _node_visual_attrs(rel, page)
        graph.add_node(
            rel,
            title=_node_hover_title(rel, page),
            group=group,
            color=GROUP_COLORS.get(group, GROUP_COLORS["other"]),
            **visuals,
        )

    for source, target in collect_edges(wiki_root, pages):
        if source not in graph:
            continue
        if target not in graph:
            visuals = _node_visual_attrs(target, None)
            group = _node_group(target)
            graph.add_node(
                target,
                title=_node_hover_title(target),
                group=group,
                color=GROUP_COLORS.get(group, GROUP_COLORS["other"]),
                **visuals,
            )
        graph.add_edge(source, target)

    orphans = list(nx.isolates(graph))
    if orphans:
        graph.remove_nodes_from(orphans)

    if graph.number_of_nodes() == 0:
        return None

    return graph


def _circular_layout(graph: nx.DiGraph) -> dict[str, tuple[float, float]]:
    """Fallback layout without numpy (networkx spring/random layouts need it)."""
    nodes = list(graph.nodes())
    n = len(nodes)
    if n == 0:
        return {}
    positions: dict[str, tuple[float, float]] = {}
    for i, node_id in enumerate(nodes):
        angle = 2 * math.pi * i / n
        positions[node_id] = (math.cos(angle), math.sin(angle))
    return positions


def _apply_calm_layout(graph: nx.DiGraph) -> None:
    """Pre-position nodes so the graph is stable without physics jitter."""
    if graph.number_of_nodes() == 0:
        return
    scale = 400.0
    positions: dict[str, tuple[float, float]]
    try:
        import numpy  # noqa: F401

        n = graph.number_of_nodes()
        positions = nx.spring_layout(
            graph, seed=42, k=1.8 / max(n**0.5, 1.0)
        )
    except (ImportError, Exception):
        positions = _circular_layout(graph)
    for node_id, (x, y) in positions.items():
        graph.nodes[node_id]["x"] = float(x * scale)
        graph.nodes[node_id]["y"] = float(y * scale)


def build_pyvis_network(wiki_root: Path) -> Network | None:
    graph = build_networkx_graph(wiki_root)
    if graph is None or graph.number_of_nodes() == 0:
        return None

    _apply_calm_layout(graph)

    net = Network(
        height="100vh",
        width="100%",
        bgcolor="#fafdfa",
        font_color="#1a2e1a",
        directed=True,
        notebook=False,
    )
    net.from_nx(graph)  # type: ignore[arg-type]
    # Physics off after spring_layout — avoids endless jitter; nodes still draggable.
    net.set_options(
        """
    {
      "nodes": {
        "shape": "dot",
        "size": 16,
        "borderWidth": 1,
        "font": {"size": 9, "face": "arial", "color": "#1a2e1a"},
        "scaling": {"label": {"enabled": true, "min": 8, "max": 11}}
      },
      "edges": {
        "arrows": {"to": {"enabled": true, "scaleFactor": 0.35}},
        "color": {"opacity": 0.35},
        "smooth": {"type": "continuous"}
      },
      "interaction": {"hover": true, "navigationButtons": true, "dragNodes": true, "tooltipDelay": 120},
      "physics": {"enabled": false}
    }
    """
    )
    return net


GRAPH_FILTER_SCRIPT = """
(function () {
  function applyWikiGraphFilters() {
    if (typeof nodes === "undefined" || typeof edges === "undefined") return;
    const active = new Set();
    document.querySelectorAll(".wg-filter-cb:checked").forEach(function (cb) {
      active.add(cb.getAttribute("data-group"));
    });
    const hiddenNodes = new Set();
    nodes.get().forEach(function (n) {
      const g = n.group || "other";
      const hide = !active.has(g);
      if (hide) hiddenNodes.add(n.id);
      nodes.update({ id: n.id, hidden: hide });
    });
    edges.get().forEach(function (e) {
      const hide = hiddenNodes.has(e.from) || hiddenNodes.has(e.to);
      edges.update({ id: e.id, hidden: hide });
    });
  }
  document.querySelectorAll(".wg-filter-cb").forEach(function (cb) {
    cb.addEventListener("change", applyWikiGraphFilters);
  });
  const allBtn = document.getElementById("wg-filter-all");
  const noneBtn = document.getElementById("wg-filter-none");
  if (allBtn) {
    allBtn.addEventListener("click", function () {
      document.querySelectorAll(".wg-filter-cb").forEach(function (cb) {
        cb.checked = true;
      });
      applyWikiGraphFilters();
    });
  }
  if (noneBtn) {
    noneBtn.addEventListener("click", function () {
      document.querySelectorAll(".wg-filter-cb").forEach(function (cb) {
        cb.checked = false;
      });
      applyWikiGraphFilters();
    });
  }
})();
"""


def _graph_filter_controls_html() -> str:
    checks = []
    for group, color in GROUP_COLORS.items():
        checks.append(
            f'<label class="wg-filter-label">'
            f'<input type="checkbox" class="wg-filter-cb" data-group="{group}" checked /> '
            f'<span class="dot" style="background:{color}"></span>{group}</label>'
        )
    return (
        '<div class="graph-filters">'
        '<span class="graph-filters-title">Show:</span>'
        + "".join(checks)
        + '<button type="button" id="wg-filter-all" class="wg-filter-btn">All</button>'
        + '<button type="button" id="wg-filter-none" class="wg-filter-btn">None</button>'
        "</div>"
    )


def _graph_bar_html() -> str:
    return (
        '<div class="graph-bar">'
        "<strong>Plant Wiki link graph</strong> — filter by folder below; "
        "<em>entities</em> and <em>concepts</em> show short labels. Hover for full name. "
        '<a href="/">Control panel</a>'
        + _graph_filter_controls_html()
        + "</div>"
    )


def build_wiki_graph_html(wiki_root: Path) -> str:
    net = build_pyvis_network(wiki_root)
    if net is None:
        return EMPTY_WIKI_HTML

    tmp_path = Path(tempfile.mkstemp(suffix=".html")[1])
    try:
        net.save_graph(str(tmp_path))
        body = tmp_path.read_text(encoding="utf-8")
    finally:
        tmp_path.unlink(missing_ok=True)

    style = (
        "<style>.graph-bar{padding:.5rem 1rem;background:#eef6ee;"
        "border-bottom:1px solid #c5d9c5;font-size:.9rem;}"
        ".graph-bar a{color:#1b5e3b;font-weight:600;}"
        ".graph-filters{margin-top:.5rem;display:flex;flex-wrap:wrap;align-items:center;gap:.35rem .75rem;}"
        ".graph-filters-title{font-weight:600;margin-right:.25rem;}"
        ".wg-filter-label{font-size:.85rem;cursor:pointer;white-space:nowrap;}"
        ".wg-filter-btn{font-size:.8rem;padding:.2rem .5rem;cursor:pointer;border:1px solid #8aab8a;"
        "border-radius:4px;background:#fff;}"
        ".dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px;}"
        "</style>"
    )
    if re.search(r"</head>", body, flags=re.IGNORECASE):
        body = re.sub(r"</head>", style + "</head>", body, count=1, flags=re.IGNORECASE)

    bar = _graph_bar_html()
    match = re.search(r"<body[^>]*>", body, flags=re.IGNORECASE)
    if match:
        pos = match.end()
        body = body[:pos] + bar + body[pos:]

    if "drawGraph();" in body:
        body = body.replace("drawGraph();", "drawGraph();\n" + GRAPH_FILTER_SCRIPT, 1)
    else:
        body = body.replace("</body>", "<script>" + GRAPH_FILTER_SCRIPT + "</script></body>", 1)

    return body


def save_wiki_graph_html(wiki_root: Path, output: Path) -> int:
    """Write graph HTML to output path. Returns node count."""
    html = build_wiki_graph_html(wiki_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    graph = build_networkx_graph(wiki_root)
    return 0 if graph is None else graph.number_of_nodes()
