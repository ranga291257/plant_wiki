#!/usr/bin/env python3
"""One-command raw -> wiki conversion.

Runs bootstrap (LLM ingest + scaffold + linking), then build_index and lint.
Uses --conversion-only by default (no human approval step).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.run_env import python_executable


def run(cmd: list[str]) -> None:
    print(f"\n>> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert raw/ notes into linked wiki/ pages (LLM + scaffold + index + lint)"
    )
    parser.add_argument("--model", default=None, help="Ollama model name (passed to bootstrap)")
    parser.add_argument("--scaffold-only", action="store_true", help="Skip LLM; build skeleton pages only")
    parser.add_argument("--max-files", type=int, default=None, help="Cap raw files processed by LLM")
    parser.add_argument("--no-clean", action="store_true", help="Do not wipe existing wiki outputs first")
    parser.add_argument(
        "--no-conversion-only",
        action="store_true",
        help="Use Draft review status instead of Converted (legacy workflow)",
    )
    parser.add_argument("--skip-lint", action="store_true", help="Skip lint_wiki.py at the end")
    args = parser.parse_args()

    py = python_executable()
    bootstrap_cmd = [py, "scripts/bootstrap_wiki.py", "--skip-post"]
    if args.model:
        bootstrap_cmd.extend(["--model", args.model])
    if args.scaffold_only:
        bootstrap_cmd.append("--scaffold-only")
    if args.max_files is not None:
        bootstrap_cmd.extend(["--max-files", str(args.max_files)])
    if args.no_clean:
        bootstrap_cmd.append("--no-clean")
    if not args.no_conversion_only:
        bootstrap_cmd.append("--conversion-only")

    run(bootstrap_cmd)

    lint_cmd = [py, "scripts/lint_wiki.py"]
    if not args.no_conversion_only:
        lint_cmd.append("--conversion-only")

    post_cmds = [[py, "scripts/build_index.py"]]
    if not args.skip_lint:
        post_cmds.append(lint_cmd)
    for cmd in post_cmds:
        run(cmd)

    print("\nConversion complete. Open wiki/ in Obsidian to browse the graph.")


if __name__ == "__main__":
    main()
