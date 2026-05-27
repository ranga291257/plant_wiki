from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.run_env import python_executable


@dataclass
class StepResult:
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str


def run_pipeline(root: Path, *, conversion_only: bool = True) -> tuple[bool, list[StepResult]]:
    py = python_executable()
    commands: list[list[str]] = [
        [py, "scripts/build_index.py"],
        [py, "scripts/lint_wiki.py"] + (["--conversion-only"] if conversion_only else []),
        [py, "scripts/log_event.py", "update", "Web UI update", "trigger=web-ui"],
    ]
    results: list[StepResult] = []

    for cmd in commands:
        proc = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        step = StepResult(
            command=cmd,
            exit_code=proc.returncode,
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
        )
        if cmd[1] == "scripts/lint_wiki.py" and "Wiki lint issues:" in step.stdout:
            step.exit_code = 2
        results.append(step)
        if step.exit_code != 0:
            return False, results

    return True, results


def run_convert(
    root: Path,
    *,
    model: str,
    scaffold_only: bool = False,
) -> tuple[bool, list[StepResult]]:
    py = python_executable()
    cmd = [py, "scripts/convert_raw_to_wiki.py", "--model", model]
    if scaffold_only:
        cmd.append("--scaffold-only")
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=False)
    step = StepResult(
        command=cmd,
        exit_code=proc.returncode,
        stdout=proc.stdout.strip(),
        stderr=proc.stderr.strip(),
    )
    return proc.returncode == 0, [step]
