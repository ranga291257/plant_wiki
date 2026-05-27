"""Shared .wikiignore loader for the wiki engine.

The .wikiignore file lives at the repo root and is the single source of
truth for "do not ingest or cite this raw path". It is consumed by:
- scripts/bootstrap_wiki.py (corpus discovery + per-file ingest list)
- scripts/lint_wiki.py (raw-citation hygiene)

Patterns:
- Comments start with `#`; blank lines are ignored.
- A pattern ending with `/` matches any directory component with that name.
- Otherwise the pattern is an fnmatch glob applied to the file name AND to
  the path relative to raw/ (POSIX form).
"""
from __future__ import annotations

import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIKIIGNORE_FILE = ROOT / ".wikiignore"


def load_patterns(path: Path = WIKIIGNORE_FILE) -> list[str]:
    if not path.exists():
        return []
    patterns: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def is_ignored(rel_posix: str, patterns: list[str]) -> bool:
    """Return True if the given POSIX path (relative to raw/) is ignored."""
    if not patterns or not rel_posix:
        return False
    parts = rel_posix.split("/")
    name = parts[-1]
    for pattern in patterns:
        if pattern.endswith("/"):
            dir_name = pattern.rstrip("/")
            if dir_name and dir_name in parts:
                return True
            continue
        if fnmatch.fnmatch(name, pattern):
            return True
        if fnmatch.fnmatch(rel_posix, pattern):
            return True
    return False


PATTERNS: list[str] = load_patterns()
