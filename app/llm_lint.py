from __future__ import annotations

import json
from pathlib import Path
import urllib.request

from app.llm_ingest import DEFAULT_MODEL, OLLAMA_URL

LLM_LINT_PROMPT = """
You are performing semantic lint on an engineering wiki.

Analyze these wiki pages and return strict JSON:
{{
  "issues": [
    "CONTRADICTION wiki/pathA.md vs wiki/pathB.md -> short description",
    "STALE_CLAIM wiki/path.md -> short description",
    "MISSING_LINK wiki/path.md -> concept/entity name"
  ]
}}

Rules:
- Only report concrete, evidence-based issues.
- Keep each issue on one line and actionable.
- If no issues, return {{"issues": []}}.
- Output JSON only.

Pages:
{pages_bundle}
"""


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


def _page_bundle(wiki_root: Path) -> str:
    pages: list[str] = []
    for family in ("concepts", "entities", "analyses", "sources"):
        for path in sorted((wiki_root / family).glob("*.md")):
            rel = f"wiki/{path.relative_to(wiki_root).as_posix()}"
            content = path.read_text(encoding="utf-8")
            pages.append(f"## FILE: {rel}\n{content}\n")
    return "\n".join(pages)


def run_llm_lint(wiki_root: Path, model: str = DEFAULT_MODEL) -> list[str]:
    bundle = _page_bundle(wiki_root)
    if not bundle:
        return []
    prompt = LLM_LINT_PROMPT.format(pages_bundle=bundle)
    raw = _ollama_generate(prompt, model)
    try:
        parsed = json.loads(raw)
        issues = parsed.get("issues", [])
        if isinstance(issues, list):
            return [str(i) for i in issues]
    except json.JSONDecodeError:
        pass
    # Fallback when model emits non-JSON text.
    lines = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]
    return [line for line in lines if line]
