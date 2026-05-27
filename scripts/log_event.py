#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "wiki" / "log.md"


def main() -> None:
    parser = argparse.ArgumentParser(description="Append an event to wiki/log.md")
    parser.add_argument("event_type", help="e.g. ingest, query, lint, analysis")
    parser.add_argument("title", help="short event title")
    parser.add_argument("details", nargs="*", help="optional bullet details")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y-%m-%d")
    lines = [f"## [{stamp}] {args.event_type} | {args.title}"]
    if args.details:
        lines.extend(f"- {detail}" for detail in args.details)
    else:
        lines.append("- Event recorded.")
    with LOG.open("a", encoding="utf-8") as f:
        f.write("\n" + "\n".join(lines) + "\n")
    print(f"Appended event to {LOG}")


if __name__ == "__main__":
    main()
