#!/usr/bin/env python3
"""Schema-driven wiki rebuild from raw/.

Modes:
- default: clean outputs, run LLM ingest in batch, then rebuild corpus scaffold pages
- --scaffold-only: skip LLM ingest and only rebuild scaffold pages

All required sections/review fields/families come from schema via app.schema_loader.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.link_pages import link_all_corpora
from app.llm_ingest import DEFAULT_MODEL, run_ingest
from app.run_env import python_executable
from app.schema_loader import REQUIRED_REVIEW_LINES, REQUIRED_SECTIONS, WIKI_PAGE_FAMILIES
from app.wikiignore import PATTERNS as WIKIIGNORE_PATTERNS, is_ignored

RAW_DIR = ROOT / "raw"
WIKI_DIR = ROOT / "wiki"


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "page"


def humanize(value: str) -> str:
    return re.sub(r"[_\-]+", " ", value).strip().title()


def required_review_block(conversion_only: bool = False) -> str:
    if conversion_only:
        today = date.today().isoformat()
        defaults = {
            "- Status:": "Converted",
            "- Reviewer:": "auto",
            "- Last reviewed:": today,
            "- Source confidence:": "Medium",
            "- Safety critical:": "No",
        }
    else:
        defaults = {
            "- Status:": "Draft",
            "- Reviewer:": "none",
            "- Last reviewed:": "none",
            "- Source confidence:": "Medium",
            "- Safety critical:": "No",
        }
    return "\n".join(f"{line}{' ' + defaults.get(line, '') if defaults.get(line) else ''}" for line in REQUIRED_REVIEW_LINES)


def render_required_sections(content: dict[str, str]) -> str:
    return "\n".join(
        f"{section}\n{content.get(section, '- None yet').rstrip()}\n" for section in REQUIRED_SECTIONS
    ).rstrip() + "\n"


def _raw_rel_posix(path: Path) -> str:
    return path.relative_to(RAW_DIR).as_posix()


def _is_raw_ignored(path: Path) -> bool:
    return is_ignored(_raw_rel_posix(path), WIKIIGNORE_PATTERNS)


def collect_corpora() -> list[tuple[str, list[Path]]]:
    if not RAW_DIR.exists():
        raise SystemExit(f"raw directory not found: {RAW_DIR}")
    corpora: list[tuple[str, list[Path]]] = []
    for child in sorted(RAW_DIR.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or child.name == "assets":
            continue
        if _is_raw_ignored(child):
            continue
        files = sorted(
            p
            for p in child.rglob("*.md")
            if p.is_file() and not _is_raw_ignored(p)
        )
        if files:
            corpora.append((child.name, [p.relative_to(RAW_DIR) for p in files]))
    return corpora


def collect_raw_markdown_files(max_files: int | None) -> list[Path]:
    files = [
        p
        for p in sorted(RAW_DIR.rglob("*.md"))
        if p.is_file()
        and "/assets/" not in f"/{p.relative_to(RAW_DIR).as_posix()}/"
        and not _is_raw_ignored(p)
    ]
    if max_files is not None:
        return files[:max_files]
    return files


def clean_wiki_outputs() -> None:
    for family in WIKI_PAGE_FAMILIES:
        folder = WIKI_DIR / family
        folder.mkdir(parents=True, exist_ok=True)
        for md in folder.glob("*.md"):
            md.unlink()
    mocs = WIKI_DIR / "mocs"
    mocs.mkdir(parents=True, exist_ok=True)
    for md in mocs.glob("*.md"):
        md.unlink()
    overview = WIKI_DIR / "overview.md"
    if overview.exists():
        overview.unlink()


def write_catalog(slug: str, name: str, files: list[Path], conversion_only: bool = False) -> Path:
    title = f"{humanize(name)} raw corpus catalog"
    body = render_required_sections(
        {
            "## Purpose": f"- Enumerate every markdown capture under `raw/{name}/` for traceability.",
            "## Assumptions": "- Filenames are preserved as captured; trust and dates vary by file.",
            "## Review": required_review_block(conversion_only),
            "## Sources": "\n".join(f"- `raw/{rel.as_posix()}`" for rel in files),
            "## Related Pages": "\n".join(
                [
                    f"- [{humanize(name)} hub](../mocs/{slug}-hub.md)",
                    f"- [{humanize(name)} corpus entity](../entities/{slug}-corpus.md)",
                    "- [Wiki Index](../index.md)",
                ]
            ),
            "## Unresolved Questions": "- Should low-value or empty captures be archived or excluded from future lint scope?",
        }
    )
    review_status = "Converted" if conversion_only else "Draft"
    review_reviewer = "auto" if conversion_only else "none"
    review_date = date.today().isoformat() if conversion_only else "none"
    frontmatter = dedent(
        f"""\
        ---
        topic: {slug}
        type: source-summary
        status: {review_status}
        reviewer: {review_reviewer}
        last_reviewed: {review_date}
        source_confidence: Medium
        safety_critical: No
        tags:
          - {slug}
          - catalog
        ---

        # {title}

        ## Metadata
        - Source folder: `raw/{name}/`
        - Source type: collection of personal/research markdown captures
        - Date: mixed (see individual files)
        - Trust level: variable
        - Scope: see hub page for themed views

        """
    )
    target = WIKI_DIR / "sources" / f"{slug}-corpus-catalog.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(frontmatter + body, encoding="utf-8")
    return target


def write_entity(slug: str, name: str, count: int, conversion_only: bool = False) -> Path:
    body = render_required_sections(
        {
            "## Purpose": f"- Represent the bounded note collection in `raw/{name}/` ({count} markdown files indexed).",
            "## Assumptions": f"- The corpus may grow; this page should stay aligned with `raw/{name}/`.",
            "## Review": required_review_block(conversion_only),
            "## Sources": f"- `raw/{name}/`",
            "## Related Pages": "\n".join(
                [
                    f"- [{humanize(name)} hub](../mocs/{slug}-hub.md)",
                    f"- [{humanize(name)} catalog](../sources/{slug}-corpus-catalog.md)",
                    "- [Wiki Index](../index.md)",
                ]
            ),
            "## Unresolved Questions": "- None yet",
        }
    )
    review_status = "Converted" if conversion_only else "Draft"
    review_reviewer = "auto" if conversion_only else "none"
    review_date = date.today().isoformat() if conversion_only else "none"
    frontmatter = dedent(
        f"""\
        ---
        topic: {slug}
        type: entity
        status: {review_status}
        reviewer: {review_reviewer}
        last_reviewed: {review_date}
        source_confidence: Medium
        safety_critical: No
        tags:
          - {slug}
          - corpus
        ---

        # Note corpus: raw/{name}/

        ## Type
        Note corpus / source folder

        ## Description
        Bounded set of markdown captures collected under `raw/{name}/`.

        """
    )
    target = WIKI_DIR / "entities" / f"{slug}-corpus.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(frontmatter + body, encoding="utf-8")
    return target


def write_hub(slug: str, name: str, count: int) -> Path:
    target = WIKI_DIR / "mocs" / f"{slug}-hub.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        dedent(
            f"""\
            # {humanize(name)} Hub

            ## Purpose
            - Navigate the wiki slice derived from `raw/{name}/` ({count} markdown files).

            ## Corpus
            - [Catalog](../sources/{slug}-corpus-catalog.md)
            - [Corpus entity](../entities/{slug}-corpus.md)

            ## Sources
            - `raw/{name}/`

            ## Related Pages
            - [Wiki Overview](../overview.md)
            - [Wiki Index](../index.md)

            ## Unresolved Questions
            - Which themes (concepts, named entities) deserve dedicated pages next?
            """
        ),
        encoding="utf-8",
    )
    return target


def write_overview(corpora: list[tuple[str, list[Path]]]) -> Path:
    lines = ["# Wiki overview", "", "## Scope"]
    lines.append(
        f"- This wiki is seeded from {len(corpora)} top-level note collection(s) under `raw/`."
        if corpora
        else "- No top-level note collections found under `raw/` yet."
    )
    lines += ["", "## How to read it", "- Start at [Wiki Index](index.md).", "- Each collection has a hub MOC, a catalog source page, and a corpus entity.", "", "## Collections"]
    for name, files in corpora:
        slug = slugify(name)
        lines.append(f"- [{humanize(name)} hub](mocs/{slug}-hub.md) ({len(files)} files) — [catalog](sources/{slug}-corpus-catalog.md), [entity](entities/{slug}-corpus.md)")
    if not corpora:
        lines.append("- None yet")
    lines.append("")
    target = WIKI_DIR / "overview.md"
    target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return target


def run_post_steps(conversion_only: bool = False, skip_lint: bool = False) -> None:
    py = python_executable()
    lint_cmd = [py, "scripts/lint_wiki.py"]
    if conversion_only:
        lint_cmd.append("--conversion-only")
    commands = [
        [py, "scripts/build_index.py"],
        lint_cmd,
    ]
    for cmd in commands:
        if skip_lint and "lint_wiki.py" in cmd[1]:
            continue
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=ROOT)
        if result.returncode != 0:
            raise SystemExit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch rebuild wiki from raw using schema-driven rules")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name for LLM ingest")
    parser.add_argument("--no-clean", action="store_true", help="Do not wipe existing substantive outputs before rebuild")
    parser.add_argument("--scaffold-only", action="store_true", help="Skip LLM ingest and rebuild only overview/hub/catalog/entity scaffold pages")
    parser.add_argument("--max-files", type=int, default=None, help="Optional cap for number of raw markdown files to ingest (for staged rebuilds)")
    parser.add_argument(
        "--conversion-only",
        action="store_true",
        help="Mark pages as Converted (auto) instead of Draft; skip human approval expectations",
    )
    parser.add_argument("--skip-post", action="store_true", help="Do not run build_index.py and lint_wiki.py at the end")
    parser.add_argument("--skip-lint", action="store_true", help="Run build_index but skip lint_wiki.py")
    args = parser.parse_args()

    if not RAW_DIR.exists():
        raise SystemExit(f"raw directory not found: {RAW_DIR}")

    if not args.no_clean:
        clean_wiki_outputs()

    ingest_errors: list[str] = []
    ingested_count = 0
    if not args.scaffold_only:
        raw_files = collect_raw_markdown_files(args.max_files)
        if not raw_files:
            raise SystemExit("No markdown files found under raw/ (excluding raw/assets).")
        print(f"Running LLM ingest for {len(raw_files)} raw file(s)...")
        for i, raw_path in enumerate(raw_files, start=1):
            print(f"[{i}/{len(raw_files)}] ingest {raw_path.relative_to(ROOT).as_posix()}")
            result = run_ingest(
                raw_path,
                WIKI_DIR,
                model=args.model,
                conversion_only=args.conversion_only,
            )
            ingested_count += 1
            for err in result.errors:
                ingest_errors.append(f"{raw_path.relative_to(ROOT).as_posix()}: {err}")

    corpora = collect_corpora()
    written: list[str] = []
    corpus_links: list[tuple[str, str]] = []
    for name, files in corpora:
        slug = slugify(name)
        corpus_links.append((name, slug))
        written.append(str(write_catalog(slug, name, files, args.conversion_only).relative_to(ROOT)))
        written.append(str(write_entity(slug, name, len(files), args.conversion_only).relative_to(ROOT)))
        written.append(str(write_hub(slug, name, len(files)).relative_to(ROOT)))
    written.append(str(write_overview(corpora).relative_to(ROOT)))

    if corpus_links:
        print("Linking hub pages and cross-references...")
        link_all_corpora(WIKI_DIR, corpus_links)

    print(f"Scaffold wrote {len(written)} page(s):")
    for path in written:
        print(f"- {path}")

    if args.scaffold_only:
        print("\nScaffold-only mode complete (no LLM ingest run).")
    else:
        print(f"\nLLM ingest processed {ingested_count} file(s).")
        if ingest_errors:
            print("Ingest completed with errors:")
            for err in ingest_errors:
                print(f"- {err}")
        else:
            print("Ingest completed with no reported per-file errors.")

    if not args.skip_post:
        run_post_steps(conversion_only=args.conversion_only, skip_lint=args.skip_lint)


if __name__ == "__main__":
    main()
