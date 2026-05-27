from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import urllib.request
import urllib.error

from app.schema_loader import AGENTS_RULES_TEXT as AGENTS_RULES

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "minimax-m2.7:cloud")
ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"

SOURCE_SUMMARY_PROMPT = """
You are an engineering wiki maintainer.

{rules}

Given this raw source file:
Filename: {filename}
Content:
{content}

Use this page structure template as canonical shape:
{template}

Template adaptation rules:
- Replace placeholders like <Source Title>, <path>, and generic guidance with source-specific content.
- Ensure `raw/{filename}` appears in Metadata and Sources.
- Keep all required sections present.
- Keep concise bullet-oriented writing.

Output only the markdown page. No explanation text.
"""

CONCEPT_EXTRACTION_PROMPT = """
You are an engineering wiki maintainer.

{rules}

Given this raw source:
Filename: {filename}
Content:
{content}

List the engineering concepts mentioned that deserve a dedicated wiki concept page.
For each concept, output a JSON object on its own line with keys: name, slug, relevance (one sentence).
Only include genuine process-control or instrumentation concepts (e.g. valve stiction, integral windup, deadtime).
Output only JSON lines, no other text. Maximum 3 concepts.

Example:
{{"name": "Valve Stiction", "slug": "valve-stiction", "relevance": "Valve hesitation near small opening changes is a key oscillation indicator."}}
"""

CONCEPT_PAGE_PROMPT = """
You are an engineering wiki maintainer.

{rules}

Write a concept wiki page for: {concept_name}
Relevance to this source: {relevance}

Raw source for context:
Filename: {filename}
Content:
{content}

Use this page structure template as canonical shape:
{template}

Template adaptation rules:
- Replace `<Concept Name>` with `{concept_name}`.
- Fill all placeholder sections with source-grounded content.
- Include `raw/{filename}` in Sources.
- Keep required sections present and concise.

Output only the markdown page. No explanation text.
"""

ENTITY_EXTRACTION_PROMPT = """
You are an engineering wiki maintainer.

{rules}

Given this raw source:
Filename: {filename}
Content:
{content}

List the key engineering entities (loops, equipment, instruments, valves, systems) mentioned that deserve a wiki entity page.
For each entity, output a JSON object on its own line with keys: name, slug, entity_type, relevance (one sentence).
Output only JSON lines, no other text. Maximum 2 entities.

Example:
{{"name": "FC-101 Control Loop", "slug": "fc-101-control-loop", "entity_type": "loop", "relevance": "Primary loop exhibiting oscillation."}}
"""

ENTITY_PAGE_PROMPT = """
You are an engineering wiki maintainer.

{rules}

Write an entity wiki page for: {entity_name}
Entity type: {entity_type}
Relevance: {relevance}

Raw source for context:
Filename: {filename}
Content:
{content}

Use this page structure template as canonical shape:
{template}

Template adaptation rules:
- Replace `<Entity Name>` with `{entity_name}`.
- Replace entity type placeholder with `{entity_type}`.
- Fill all sections with source-grounded content.
- Include `raw/{filename}` in Sources.
- Keep required sections present and concise.

Output only the markdown page. No explanation text.
"""

UPDATE_CONCEPT_PROMPT = """
You are an engineering wiki maintainer updating an existing concept page.

{rules}

Existing page (preserve existing structure and all prior citations):
{existing_content}

New raw source providing additional evidence:
Filename: {filename}
Content:
{content}
Relevance to this concept from extraction:
{relevance}

Update rules:
- Preserve existing reviewer and status values in frontmatter and the ## Review section.
- Preserve existing sections; do not remove useful prior content.
- Add new evidence and facts from this source where relevant.
- Ensure this source is listed in ## Sources as `raw/{filename}` (without removing existing sources).
- If this source conflicts with existing claims, add a contradiction note in ## Unresolved Questions.
- Keep output concise and markdown only.

Output only the full updated markdown page.
"""

UPDATE_ENTITY_PROMPT = """
You are an engineering wiki maintainer updating an existing entity page.

{rules}

Existing page (preserve existing structure and all prior citations):
{existing_content}

New raw source providing additional evidence:
Filename: {filename}
Content:
{content}
Relevance to this entity from extraction:
{relevance}

Update rules:
- Preserve existing reviewer and status values in frontmatter and the ## Review section.
- Preserve existing sections; do not remove useful prior content.
- Add new evidence and facts from this source where relevant.
- Ensure this source is listed in ## Sources as `raw/{filename}` (without removing existing sources).
- If this source conflicts with existing claims, add a contradiction note in ## Unresolved Questions.
- Keep output concise and markdown only.

Output only the full updated markdown page.
"""

CONVERSION_REVIEW_HINT = """
Conversion mode — set the ## Review section (and matching YAML frontmatter fields if present) to:
- Status: Converted
- Reviewer: auto
- Last reviewed: {today}
- Source confidence: Medium (use Low only if source is clearly weak)
- Safety critical: No (use Yes only if the source is explicitly safety-critical)
Human approval is not required for this conversion run.
"""


@dataclass
class IngestResult:
    source_summary_path: str
    concept_pages_created: list[str]
    concept_pages_updated: list[str]
    entity_pages_created: list[str]
    entity_pages_updated: list[str]
    errors: list[str]


def _ollama_generate(prompt: str, model: str) -> str:
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode())
        return result.get("response", "").strip()


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "page"


def _safe_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _load_template(filename: str) -> str:
    path = TEMPLATES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Template file not found: {path}")
    return path.read_text(encoding="utf-8")


def _conversion_rules_extra(conversion_only: bool) -> str:
    if not conversion_only:
        return ""
    return "\n" + CONVERSION_REVIEW_HINT.format(today=date.today().isoformat())


def _apply_conversion_review(md: str) -> str:
    today = date.today().isoformat()
    md = re.sub(r"^status:\s*.+$", "status: Converted", md, count=1, flags=re.MULTILINE | re.IGNORECASE)
    md = re.sub(r"^reviewer:\s*.+$", "reviewer: auto", md, count=1, flags=re.MULTILINE | re.IGNORECASE)
    md = re.sub(r"^last_reviewed:\s*.+$", f"last_reviewed: {today}", md, count=1, flags=re.MULTILINE | re.IGNORECASE)
    review_block = (
        "## Review\n"
        f"- Status: Converted\n"
        f"- Reviewer: auto\n"
        f"- Last reviewed: {today}\n"
        "- Source confidence: Medium\n"
        "- Safety critical: No\n"
    )
    if "## Review" in md:
        md = re.sub(r"## Review\n.*?(?=\n## |\Z)", review_block.rstrip() + "\n", md, count=1, flags=re.DOTALL)
    return md


def _finalize_page(content: str, conversion_only: bool) -> str:
    if conversion_only:
        return _apply_conversion_review(content)
    return content


def run_ingest(
    raw_path: Path,
    wiki_root: Path,
    model: str = DEFAULT_MODEL,
    conversion_only: bool = False,
) -> IngestResult:
    errors: list[str] = []
    concept_pages_created: list[str] = []
    concept_pages_updated: list[str] = []
    entity_pages_created: list[str] = []
    entity_pages_updated: list[str] = []

    content = raw_path.read_text(encoding="utf-8")
    filename = raw_path.name
    rules = AGENTS_RULES.strip() + _conversion_rules_extra(conversion_only)
    source_template = _load_template("source-summary-template.md")
    concept_template = _load_template("concept-template.md")
    entity_template = _load_template("entity-template.md")

    # 1. Source summary
    summary_prompt = SOURCE_SUMMARY_PROMPT.format(
        rules=rules,
        filename=filename,
        content=content,
        template=source_template,
    )
    try:
        summary_md = _ollama_generate(summary_prompt, model)
        summary_md = _finalize_page(summary_md, conversion_only)
        slug = _slugify(raw_path.stem)
        summary_path = wiki_root / "sources" / f"{slug}.md"
        _safe_write(summary_path, summary_md)
        source_summary_path = str(summary_path.relative_to(wiki_root.parent))
    except Exception as exc:
        errors.append(f"source summary error: {exc}")
        source_summary_path = ""

    # 2. Concept extraction + pages
    concept_prompt = CONCEPT_EXTRACTION_PROMPT.format(rules=rules, filename=filename, content=content)
    try:
        concept_json_lines = _ollama_generate(concept_prompt, model)
        for line in concept_json_lines.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                concept = json.loads(line)
                slug = concept.get("slug") or _slugify(concept["name"])
                page_path = wiki_root / "concepts" / f"{slug}.md"
                if page_path.exists():
                    existing_content = page_path.read_text(encoding="utf-8")
                    page_prompt = UPDATE_CONCEPT_PROMPT.format(
                        rules=rules,
                        existing_content=existing_content,
                        filename=filename,
                        content=content,
                        relevance=concept["relevance"],
                    )
                    page_md = _ollama_generate(page_prompt, model)
                    page_md = _finalize_page(page_md, conversion_only)
                    _safe_write(page_path, page_md)
                    concept_pages_updated.append(str(page_path.relative_to(wiki_root.parent)))
                    continue

                page_prompt = CONCEPT_PAGE_PROMPT.format(
                    rules=rules,
                    concept_name=concept["name"],
                    relevance=concept["relevance"],
                    filename=filename,
                    content=content,
                    template=concept_template,
                )
                page_md = _ollama_generate(page_prompt, model)
                page_md = _finalize_page(page_md, conversion_only)
                _safe_write(page_path, page_md)
                concept_pages_created.append(str(page_path.relative_to(wiki_root.parent)))
            except Exception as exc:
                errors.append(f"concept page error ({line[:40]}): {exc}")
    except Exception as exc:
        errors.append(f"concept extraction error: {exc}")

    # 3. Entity extraction + pages
    entity_prompt = ENTITY_EXTRACTION_PROMPT.format(rules=rules, filename=filename, content=content)
    try:
        entity_json_lines = _ollama_generate(entity_prompt, model)
        for line in entity_json_lines.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                entity = json.loads(line)
                slug = entity.get("slug") or _slugify(entity["name"])
                page_path = wiki_root / "entities" / f"{slug}.md"
                if page_path.exists():
                    existing_content = page_path.read_text(encoding="utf-8")
                    page_prompt = UPDATE_ENTITY_PROMPT.format(
                        rules=rules,
                        existing_content=existing_content,
                        filename=filename,
                        content=content,
                        relevance=entity["relevance"],
                    )
                    page_md = _ollama_generate(page_prompt, model)
                    page_md = _finalize_page(page_md, conversion_only)
                    _safe_write(page_path, page_md)
                    entity_pages_updated.append(str(page_path.relative_to(wiki_root.parent)))
                    continue

                page_prompt = ENTITY_PAGE_PROMPT.format(
                    rules=rules,
                    entity_name=entity["name"],
                    entity_type=entity["entity_type"],
                    relevance=entity["relevance"],
                    filename=filename,
                    content=content,
                    template=entity_template,
                )
                page_md = _ollama_generate(page_prompt, model)
                page_md = _finalize_page(page_md, conversion_only)
                _safe_write(page_path, page_md)
                entity_pages_created.append(str(page_path.relative_to(wiki_root.parent)))
            except Exception as exc:
                errors.append(f"entity page error ({line[:40]}): {exc}")
    except Exception as exc:
        errors.append(f"entity extraction error: {exc}")

    return IngestResult(
        source_summary_path=source_summary_path,
        concept_pages_created=concept_pages_created,
        concept_pages_updated=concept_pages_updated,
        entity_pages_created=entity_pages_created,
        entity_pages_updated=entity_pages_updated,
        errors=errors,
    )
