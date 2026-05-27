#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.llm_ingest import DEFAULT_MODEL
from app.llm_query import write_analysis
from app.run_env import python_executable
WIKI = ROOT / "wiki"


def run_update_pipeline() -> None:
    py = python_executable()
    commands = [
        [py, "scripts/build_index.py"],
        [py, "scripts/lint_wiki.py"],
        [py, "scripts/log_event.py", "update", "OpenClaw analysis file", "trigger=openclaw"],
    ]
    for cmd in commands:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            raise SystemExit(
                f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenClaw: file query answer into wiki/analyses")
    parser.add_argument("question", help="Original question")
    parser.add_argument("answer", help="Answer markdown/text")
    parser.add_argument("--slug", default="analysis", help="Analysis file slug")
    parser.add_argument("--citations", default="[]", help="JSON list string of citations")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    args = parser.parse_args()

    try:
        citations = json.loads(args.citations)
        if not isinstance(citations, list):
            citations = []
    except json.JSONDecodeError:
        citations = []

    path = write_analysis(
        WIKI,
        question=args.question,
        answer=args.answer,
        citations=[str(c) for c in citations],
        slug=args.slug,
        model=args.model,
    )
    run_update_pipeline()
    print(json.dumps({"analysis_path": path.relative_to(ROOT).as_posix()}, indent=2))


if __name__ == "__main__":
    main()
