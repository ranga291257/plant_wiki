#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.llm_ingest import DEFAULT_MODEL
from app.llm_lint import run_llm_lint

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic lint of wiki pages (LLM-assisted)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    args = parser.parse_args()

    issues = run_llm_lint(WIKI, model=args.model)
    print(json.dumps({"issues": issues}, indent=2))


if __name__ == "__main__":
    main()
