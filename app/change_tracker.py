from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def build_snapshot(root: Path) -> dict[str, dict[str, str | int]]:
    tracked: dict[str, dict[str, str | int]] = {}
    for rel_base in ["raw", "raw/assets"]:
        base = root / rel_base
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and not path.name.startswith("."):
                rel = path.relative_to(root).as_posix()
                stat = path.stat()
                tracked[rel] = {
                    "sha256": _file_hash(path),
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                }
    return tracked


def load_snapshot(path: Path) -> dict[str, dict[str, str | int]]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_snapshot(path: Path, snapshot: dict[str, dict[str, str | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def diff_snapshots(
    old: dict[str, dict[str, str | int]],
    new: dict[str, dict[str, str | int]],
) -> dict[str, list[str]]:
    old_keys = set(old)
    new_keys = set(new)
    added = sorted(new_keys - old_keys)
    deleted = sorted(old_keys - new_keys)
    modified = sorted(
        path for path in (old_keys & new_keys) if old[path].get("sha256") != new[path].get("sha256")
    )
    return {"added": added, "modified": modified, "deleted": deleted}
