"""Post-process wiki pages to improve cross-links for Obsidian graph view."""
from __future__ import annotations

import os
import re
from pathlib import Path

LINK_RE = re.compile(r"\[[^\]]+\]\([^)]+\)")
RELATED_PAGES_HEADING = "## Related Pages"
CORPUS_ENTITY_SUFFIX = "-corpus"
CORPUS_CATALOG_SUFFIX = "-corpus-catalog"


def _title_from_file(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    except OSError:
        pass
    return path.stem.replace("-", " ").replace("_", " ").title()


def _rel_link(from_path: Path, to_path: Path) -> str:
    rel = Path(os.path.relpath(to_path, from_path.parent)).as_posix()
    return f"- [{_title_from_file(to_path)}]({rel})"


def _existing_link_targets(text: str) -> set[str]:
    targets: set[str] = set()
    for match in LINK_RE.finditer(text):
        target_match = re.search(r"\]\(([^)]+)\)", match.group(0))
        if target_match:
            targets.add(target_match.group(1))
    return targets


def _append_related_links(page: Path, links: list[str]) -> bool:
    if not links:
        return False
    text = page.read_text(encoding="utf-8")
    existing = _existing_link_targets(text)
    new_links = [link for link in links if not any(t in link for t in existing)]
    if not new_links:
        return False

    block = "\n".join(new_links)
    if RELATED_PAGES_HEADING in text:
        parts = text.split(RELATED_PAGES_HEADING, 1)
        after = parts[1]
        next_heading = re.search(r"\n## ", after)
        if next_heading:
            insert_at = next_heading.start()
            updated = (
                parts[0]
                + RELATED_PAGES_HEADING
                + after[:insert_at].rstrip()
                + "\n"
                + block
                + "\n"
                + after[insert_at:]
            )
        else:
            updated = text.rstrip() + "\n" + block + "\n"
    else:
        updated = text.rstrip() + f"\n\n{RELATED_PAGES_HEADING}\n{block}\n"

    page.write_text(updated, encoding="utf-8")
    return True


def _list_concept_pages(wiki_root: Path) -> list[Path]:
    folder = wiki_root / "concepts"
    if not folder.exists():
        return []
    return sorted(p for p in folder.glob("*.md") if p.is_file())


def _list_tag_entity_pages(wiki_root: Path) -> list[Path]:
    folder = wiki_root / "entities"
    if not folder.exists():
        return []
    return sorted(
        p for p in folder.glob("*.md") if p.is_file() and not p.stem.endswith(CORPUS_ENTITY_SUFFIX)
    )


def _list_llm_source_pages(wiki_root: Path, slug: str) -> list[Path]:
    folder = wiki_root / "sources"
    if not folder.exists():
        return []
    catalog_name = f"{slug}{CORPUS_CATALOG_SUFFIX}.md"
    return sorted(p for p in folder.glob("*.md") if p.is_file() and p.name != catalog_name)


def update_hub(wiki_root: Path, slug: str, display_name: str, raw_folder: str) -> Path | None:
    hub_path = wiki_root / "mocs" / f"{slug}-hub.md"
    if not hub_path.exists():
        return None

    concepts = _list_concept_pages(wiki_root)
    entities = _list_tag_entity_pages(wiki_root)
    sources = _list_llm_source_pages(wiki_root, slug)

    concept_lines = (
        "\n".join(f"- [{_title_from_file(p)}](../concepts/{p.name})" for p in concepts)
        or "- None yet"
    )
    entity_lines = (
        "\n".join(f"- [{_title_from_file(p)}](../entities/{p.name})" for p in entities)
        or "- None yet"
    )
    source_lines = (
        "\n".join(f"- [{_title_from_file(p)}](../sources/{p.name})" for p in sources)
        or "- None yet"
    )

    hub_path.write_text(
        f"""# {display_name} Hub

## Purpose
- Navigate the wiki slice derived from `raw/{raw_folder}/`.

## Corpus
- [Catalog](../sources/{slug}{CORPUS_CATALOG_SUFFIX}.md)
- [Corpus entity](../entities/{slug}{CORPUS_ENTITY_SUFFIX}.md)

## Source summaries
{source_lines}

## Concepts
{concept_lines}

## Entities
{entity_lines}

## Sources
- `raw/{raw_folder}/`

## Related Pages
- [Wiki Overview](../overview.md)
- [Wiki Index](../index.md)

## Unresolved Questions
- Which themes deserve more dedicated pages next?
""",
        encoding="utf-8",
    )
    return hub_path


def cross_link_pages(wiki_root: Path, slug: str) -> int:
    hub_path = wiki_root / "mocs" / f"{slug}-hub.md"
    if not hub_path.exists():
        return 0

    updated = 0
    pages = (
        _list_llm_source_pages(wiki_root, slug)
        + _list_concept_pages(wiki_root)
        + _list_tag_entity_pages(wiki_root)
    )
    catalog = wiki_root / "sources" / f"{slug}{CORPUS_CATALOG_SUFFIX}.md"
    corpus_entity = wiki_root / "entities" / f"{slug}{CORPUS_ENTITY_SUFFIX}.md"

    for page in pages:
        links = [_rel_link(page, hub_path)]
        if catalog.exists():
            links.append(_rel_link(page, catalog))
        if corpus_entity.exists():
            links.append(_rel_link(page, corpus_entity))
        if _append_related_links(page, links):
            updated += 1
    return updated


def link_all_corpora(wiki_root: Path, corpora: list[tuple[str, str]]) -> None:
    """Link hub and cross-references for each corpus (raw_folder_name, slug)."""
    for raw_folder, slug in corpora:
        display_name = raw_folder.replace("_", " ").replace("-", " ").title()
        update_hub(wiki_root, slug, display_name, raw_folder)
        count = cross_link_pages(wiki_root, slug)
        if count:
            print(f"Cross-linked {count} page(s) for corpus {raw_folder}")
