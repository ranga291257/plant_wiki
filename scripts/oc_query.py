#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.llm_ingest import DEFAULT_MODEL
from app.llm_query import run_query

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenClaw query against wiki")
    parser.add_argument("question", help="Diagnostic question to ask")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    args = parser.parse_args()

    result = run_query(args.question, WIKI, model=args.model)
    print(
        json.dumps(
            {
                "answer": result.answer,
                "citations": result.citations,
                "suggested_slug": result.suggested_slug,
                "selected_pages": result.selected_pages,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
