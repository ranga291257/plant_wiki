"""Single source of truth loader for schema/ rules.

Parses `schema/AGENTS.md` and `schema/review-rules.md` and exposes the rules
that the rest of the codebase consumes. No other module should hardcode the
required sections, review fields, or LLM rule block.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schema"
AGENTS_PATH = SCHEMA_DIR / "AGENTS.md"
REVIEW_RULES_PATH = SCHEMA_DIR / "review-rules.md"

REQUIRED_SECTIONS_HEADING = "Required sections on every substantive wiki page"
CORE_RULES_HEADING = "Core rules"
WIKI_PAGE_FAMILIES_HEADING = "Wiki page families"
REQUIRED_REVIEW_FIELDS_HEADING = "Required review fields"


class SchemaError(RuntimeError):
    """Raised when a schema file is missing or no longer parseable."""


def _read(path: Path) -> str:
    if not path.exists():
        raise SchemaError(f"Required schema file not found: {path}")
    return path.read_text(encoding="utf-8")


def _section(markdown: str, heading: str) -> str:
    """Return the body text under an `## <heading>` block, until the next H2 or EOF."""
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    match = pattern.search(markdown)
    if not match:
        raise SchemaError(
            f"Could not find `## {heading}` section in schema. "
            f"Rename or restore that heading."
        )
    return match.group(1).strip("\n")


def _bullets(section_text: str) -> list[str]:
    """Extract `- ...` bullet items from a section, skipping nested bullets."""
    bullets: list[str] = []
    for line in section_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("- ") and not line.startswith("  "):
            bullets.append(stripped[2:].strip())
    return bullets


def _strip_inline_code(value: str) -> str:
    return value.strip().strip("`").strip()


def load_required_sections() -> tuple[str, ...]:
    """Section headings (e.g. `## Purpose`) every substantive wiki page must contain."""
    body = _section(_read(AGENTS_PATH), REQUIRED_SECTIONS_HEADING)
    items: list[str] = []
    for raw in _bullets(body):
        cleaned = _strip_inline_code(raw)
        if cleaned.startswith("##"):
            items.append(cleaned)
    if not items:
        raise SchemaError(
            f"`## {REQUIRED_SECTIONS_HEADING}` section parsed empty. "
            "Each required section must be a `- `## Heading`` bullet."
        )
    return tuple(items)


def load_required_review_lines() -> tuple[str, ...]:
    """Bullets every `## Review` block must contain, formatted as `- <Field>:`."""
    body = _section(_read(REVIEW_RULES_PATH), REQUIRED_REVIEW_FIELDS_HEADING)
    items: list[str] = []
    for raw in _bullets(body):
        cleaned = _strip_inline_code(raw)
        if cleaned:
            items.append(f"- {cleaned}:")
    if not items:
        raise SchemaError(
            f"`## {REQUIRED_REVIEW_FIELDS_HEADING}` section parsed empty in review-rules."
        )
    return tuple(items)


def load_wiki_page_families() -> tuple[str, ...]:
    """Folder names under wiki/ that hold substantive pages (e.g. `concepts`, `entities`)."""
    body = _section(_read(AGENTS_PATH), WIKI_PAGE_FAMILIES_HEADING)
    families: list[str] = []
    for raw in _bullets(body):
        match = re.search(r"`wiki/([^/`]+)/`", raw)
        if match:
            families.append(match.group(1))
    if not families:
        raise SchemaError(
            f"`## {WIKI_PAGE_FAMILIES_HEADING}` section parsed empty. "
            "Each family must be referenced as `wiki/<folder>/`."
        )
    return tuple(families)


def load_agents_rules_text() -> str:
    """Compose the LLM rule block from parsed schema content (no hardcoding)."""
    agents_md = _read(AGENTS_PATH)
    core_rules_body = _section(agents_md, CORE_RULES_HEADING)
    required_sections_body = _section(agents_md, REQUIRED_SECTIONS_HEADING)

    review_lines = "\n".join(f"  {line}" for line in load_required_review_lines())

    parts = [
        "You are a wiki maintainer. Follow these rules strictly:",
        "",
        "Core rules:",
        core_rules_body.rstrip(),
        "",
        "Required sections on every substantive wiki page:",
        required_sections_body.rstrip(),
        "",
        "Required review fields (must appear under `## Review`):",
        review_lines,
    ]
    return "\n".join(parts).strip() + "\n"


REQUIRED_SECTIONS: tuple[str, ...] = load_required_sections()
REQUIRED_REVIEW_LINES: tuple[str, ...] = load_required_review_lines()
WIKI_PAGE_FAMILIES: tuple[str, ...] = load_wiki_page_families()
AGENTS_RULES_TEXT: str = load_agents_rules_text()


__all__ = [
    "AGENTS_RULES_TEXT",
    "REQUIRED_SECTIONS",
    "REQUIRED_REVIEW_LINES",
    "WIKI_PAGE_FAMILIES",
    "SchemaError",
]
