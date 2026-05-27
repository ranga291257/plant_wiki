"""Resolve the Python executable for subprocess calls in this repo."""
from __future__ import annotations

import sys


def python_executable() -> str:
    """Use the current interpreter (venv when activated or ./run is used)."""
    return sys.executable
