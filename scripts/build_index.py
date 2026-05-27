#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"

SECTIONS = [
    ("Overview", [WIKI / "overview.md"]),
    ("Maps", sorted((WIKI / "mocs").glob("*.md"))),
    ("Sources", sorted((WIKI / "sources").glob("*.md"))),
    ("Entities", sorted((WIKI / "entities").glob("*.md"))),
    ("Concepts", sorted((WIKI / "concepts").glob("*.md"))),
    ("Analyses", sorted((WIKI / "analyses").glob("*.md"))),
]


def title_from_file(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    except OSError:
        pass
    return path.stem.replace("-", " ").replace("_", " ").title()


def rel(path: Path) -> str:
    return path.relative_to(WIKI).as_posix()


def main() -> None:
    lines = ["# Wiki Index", ""]
    for section, paths in SECTIONS:
        lines.append(f"## {section} ({len(paths)})")
        if paths:
            for path in paths:
                lines.append(f"- [{title_from_file(path)}]({rel(path)})")
        else:
            lines.append("- None yet")
        lines.append("")
    (WIKI / "index.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Updated {(WIKI / 'index.md').as_posix()}")


if __name__ == "__main__":
    main()
