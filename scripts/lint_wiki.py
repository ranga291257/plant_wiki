#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.schema_loader import (
    REQUIRED_REVIEW_LINES,
    REQUIRED_SECTIONS,
    WIKI_PAGE_FAMILIES,
)
from app.wikiignore import PATTERNS as WIKIIGNORE_PATTERNS, is_ignored

WIKI = ROOT / "wiki"
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
RAW_CITATION_RE = re.compile(r"`raw/([^`]+)`")
STATUS_RE = re.compile(r"- Status:\s*(\S+)")
VALID_STATUSES = frozenset({"Draft", "Converted", "Reviewed", "Approved"})
ORPHAN_EXEMPT_PREFIXES = (
    (WIKI / "guides").resolve(),
    (WIKI / "archive").resolve(),
)
SUBSTANTIVE_PREFIXES = tuple(
    (WIKI / family).resolve() for family in WIKI_PAGE_FAMILIES
)


def iter_pages():
    for path in WIKI.rglob("*.md"):
        yield path


def is_substantive(path: Path) -> bool:
    resolved = path.resolve()
    return any(str(resolved).startswith(str(prefix)) for prefix in SUBSTANTIVE_PREFIXES)


def is_orphan_exempt(path: Path) -> bool:
    resolved = path.resolve()
    return any(str(resolved).startswith(str(prefix)) for prefix in ORPHAN_EXEMPT_PREFIXES)


def main() -> None:
    parser = argparse.ArgumentParser(description="Structural lint for wiki pages")
    parser.add_argument(
        "--conversion-only",
        action="store_true",
        help="Accept Converted status; relax orphan checks for guides/archive",
    )
    args = parser.parse_args()

    issues = []
    pages = list(iter_pages())
    inbound = {p: 0 for p in pages}

    for page in pages:
        text = page.read_text(encoding="utf-8")
        for target in LINK_RE.findall(text):
            if target.startswith("http://") or target.startswith("https://") or target.startswith("#"):
                continue
            resolved = (page.parent / target).resolve()
            try:
                target_path = resolved.relative_to(WIKI.resolve())
                full_target = WIKI / target_path
            except ValueError:
                issues.append(f"OUTSIDE_WIKI_LINK {page.relative_to(ROOT)} -> {target}")
                continue
            if not full_target.exists():
                issues.append(f"BROKEN_LINK {page.relative_to(ROOT)} -> {target}")
            else:
                inbound[full_target] = inbound.get(full_target, 0) + 1

        if is_substantive(page):
            for section in REQUIRED_SECTIONS:
                if section not in text:
                    issues.append(f"MISSING_SECTION {page.relative_to(ROOT)} -> {section}")
            for line in REQUIRED_REVIEW_LINES:
                if line not in text:
                    issues.append(f"MISSING_REVIEW_FIELD {page.relative_to(ROOT)} -> {line}")
            status_match = STATUS_RE.search(text)
            if status_match and status_match.group(1) not in VALID_STATUSES:
                issues.append(
                    f"INVALID_STATUS {page.relative_to(ROOT)} -> {status_match.group(1)}"
                )
            citations = RAW_CITATION_RE.findall(text)
            if not citations:
                issues.append(f"MISSING_RAW_CITATION {page.relative_to(ROOT)}")
            for raw_rel in citations:
                if is_ignored(raw_rel, WIKIIGNORE_PATTERNS):
                    issues.append(
                        f"CITES_IGNORED_RAW {page.relative_to(ROOT)} -> raw/{raw_rel}"
                    )

    for page in pages:
        if page.name in {"index.md", "log.md"}:
            continue
        if is_orphan_exempt(page):
            continue
        if inbound.get(page, 0) == 0:
            issues.append(f"ORPHAN_PAGE {page.relative_to(ROOT)}")

    if issues:
        print("Wiki lint issues:")
        for issue in issues:
            print(f"- {issue}")
        raise SystemExit(1)
    else:
        print("No wiki lint issues found.")


if __name__ == "__main__":
    main()
