#!/usr/bin/env python3
"""Export an interactive wiki link graph as standalone HTML (pyvis)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.wiki_graph import save_wiki_graph_html

WIKI_DIR = ROOT / "wiki"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render wiki/ link graph to HTML")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=ROOT / "state" / "wiki_graph.html",
        help="Output HTML path (default: state/wiki_graph.html)",
    )
    args = parser.parse_args()

    count = save_wiki_graph_html(WIKI_DIR, args.output.resolve())
    print(f"Wrote {args.output} ({count} nodes)")


if __name__ == "__main__":
    main()
