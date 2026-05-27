#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.llm_ingest import DEFAULT_MODEL, run_ingest
from app.run_env import python_executable
WIKI = ROOT / "wiki"


def run_update_pipeline() -> None:
    py = python_executable()
    commands = [
        [py, "scripts/build_index.py"],
        [py, "scripts/lint_wiki.py"],
        [py, "scripts/log_event.py", "update", "OpenClaw ingest", "trigger=openclaw"],
    ]
    for cmd in commands:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            raise SystemExit(
                f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenClaw ingest: raw source -> wiki updates")
    parser.add_argument("raw_file", help="Path relative to repo root, e.g. raw/fc101-loop-narrative.md")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    args = parser.parse_args()

    raw_path = (ROOT / args.raw_file).resolve()
    raw_root = (ROOT / "raw").resolve()
    if not str(raw_path).startswith(str(raw_root)):
        raise SystemExit("raw_file must be inside raw/")
    if not raw_path.exists():
        raise SystemExit(f"file not found: {args.raw_file}")

    result = run_ingest(raw_path, WIKI, model=args.model)
    run_update_pipeline()
    print(
        json.dumps(
            {
                "source_summary": result.source_summary_path,
                "concept_pages_created": result.concept_pages_created,
                "concept_pages_updated": result.concept_pages_updated,
                "entity_pages_created": result.entity_pages_created,
                "entity_pages_updated": result.entity_pages_updated,
                "errors": result.errors,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
