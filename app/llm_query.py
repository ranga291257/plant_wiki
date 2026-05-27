from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
import urllib.request

from app.llm_ingest import AGENTS_RULES, DEFAULT_MODEL, OLLAMA_URL
ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"

SELECT_RELEVANT_PAGES_PROMPT = """
You are selecting relevant wiki pages for a diagnostic question.

Question:
{question}

Wiki index:
{index_content}

Return strict JSON with this shape:
{{"paths": ["wiki/path-a.md", "wiki/path-b.md", "..."]}}

Rules:
- Choose 3-8 most relevant pages from the index.
- Only include paths that exist in the index content.
- Output JSON only.
"""

SYNTHESIZE_ANSWER_PROMPT = """
You are an engineering assistant answering from wiki pages.

{rules}

Question:
{question}

Relevant wiki pages:
{pages_bundle}

Provide strict JSON:
{{
  "answer_markdown": "<concise markdown answer with bullet points>",
  "citations": ["wiki/path.md", "raw/file.ext", "..."],
  "suggested_slug": "<short-kebab-slug>"
}}

Rules:
- Cite only paths present in provided pages.
- Keep answer practical and uncertainty-aware.
- If evidence is weak, explicitly say so.
- Output JSON only.
"""

WRITE_ANALYSIS_PROMPT = """
You are writing a wiki analysis page.

{rules}

Question:
{question}

Answer:
{answer}

Citations:
{citations}

Use this page structure template as canonical shape:
{template}

Template adaptation rules:
- Replace `<Analysis Title>` with `{title}`.
- Replace placeholder guidance with concrete answer content.
- Keep `## Sources` aligned to provided citations.
- Keep required sections present and concise.

Output only markdown.
"""


@dataclass
class QueryResult:
    answer: str
    citations: list[str]
    suggested_slug: str
    selected_pages: list[str]


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


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "analysis"


def _extract_json_object(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}


def _load_template(filename: str) -> str:
    path = TEMPLATES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Template file not found: {path}")
    return path.read_text(encoding="utf-8")


def _load_page_bundle(wiki_root: Path, selected_paths: list[str]) -> str:
    bundles: list[str] = []
    for rel in selected_paths:
        rel_path = rel.replace("\\", "/")
        if rel_path.startswith("wiki/"):
            rel_path = rel_path[5:]
        abs_path = wiki_root / rel_path
        if not abs_path.exists():
            continue
        content = abs_path.read_text(encoding="utf-8")
        bundles.append(f"## FILE: wiki/{rel_path}\n{content}\n")
    return "\n".join(bundles)


def run_query(question: str, wiki_root: Path, model: str = DEFAULT_MODEL) -> QueryResult:
    index_path = wiki_root / "index.md"
    index_content = index_path.read_text(encoding="utf-8")

    select_prompt = SELECT_RELEVANT_PAGES_PROMPT.format(
        question=question,
        index_content=index_content,
    )
    selected_raw = _ollama_generate(select_prompt, model)
    selected_json = _extract_json_object(selected_raw)
    selected_paths = selected_json.get("paths", [])
    if not isinstance(selected_paths, list):
        selected_paths = []

    page_bundle = _load_page_bundle(wiki_root, selected_paths[:8])
    if not page_bundle:
        page_bundle = f"## FILE: wiki/index.md\n{index_content}\n"

    synth_prompt = SYNTHESIZE_ANSWER_PROMPT.format(
        rules=AGENTS_RULES.strip(),
        question=question,
        pages_bundle=page_bundle,
    )
    synth_raw = _ollama_generate(synth_prompt, model)
    synth_json = _extract_json_object(synth_raw)

    answer = synth_json.get("answer_markdown") or "No answer generated."
    citations = synth_json.get("citations") if isinstance(synth_json.get("citations"), list) else []
    suggested_slug = _slugify(synth_json.get("suggested_slug", "") or question)

    return QueryResult(
        answer=answer,
        citations=[str(c) for c in citations],
        suggested_slug=suggested_slug,
        selected_pages=selected_paths[:8],
    )


def write_analysis(
    wiki_root: Path,
    question: str,
    answer: str,
    citations: list[str],
    slug: str,
    model: str = DEFAULT_MODEL,
) -> Path:
    safe_slug = _slugify(slug or question)
    analysis_path = wiki_root / "analyses" / f"{safe_slug}.md"

    citation_lines = "\n".join(f"- {c}" for c in citations) if citations else "- None yet"
    analysis_template = _load_template("analysis-template.md")
    prompt = WRITE_ANALYSIS_PROMPT.format(
        rules=AGENTS_RULES.strip(),
        question=question,
        answer=answer,
        citations=citation_lines,
        title=safe_slug.replace("-", " ").title(),
        template=analysis_template,
    )
    analysis_md = _ollama_generate(prompt, model)
    analysis_path.parent.mkdir(parents=True, exist_ok=True)
    analysis_path.write_text(analysis_md, encoding="utf-8")
    return analysis_path
