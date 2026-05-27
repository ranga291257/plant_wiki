#!/usr/bin/env python3
"""Initialize a fresh topic-specific wiki from this template repo.

What this does (in order):
  1. Validates --name and derives --slug if not given.
  2. Removes sample raw/<SampleSection>/ folders (e.g. Digital_transformation),
     unless --keep-raw is passed.
  3. Wipes generated wiki content (mocs/, sources/, entities/, concepts/,
     analyses/, overview.md) so the new topic starts clean,
     unless --keep-wiki is passed.
  4. Rewrites the `<topic>` placeholder in templates/*.md to the topic slug.
  5. Updates the title block in README.md so the repo identifies itself
     with the new topic.
  6. Ensures raw/ and wiki/ are tracked even when empty via .gitkeep files.

What this does NOT touch:
  - schema/  (single source of truth, copied as-is)
  - app/, scripts/, .github/, mkdocs.yml, .wikiignore (engine code)
  - raw/<your topic>/ once you start adding content

Run from the repo root:
  python3 scripts/init_topic.py --name "Industrial AI" --slug industrial-ai --yes
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "raw"
WIKI_DIR = ROOT / "wiki"
TEMPLATES_DIR = ROOT / "templates"
README = ROOT / "README.md"

SAMPLE_RAW_FOLDERS = {"Digital_transformation"}
WIKI_GENERATED_SUBFOLDERS = ("mocs", "sources", "entities", "concepts", "analyses")
WIKI_GENERATED_FILES = ("overview.md",)


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "topic"


def confirm(prompt: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    reply = input(f"{prompt} [y/N] ").strip().lower()
    return reply in {"y", "yes"}


def remove_sample_raw(assume_yes: bool) -> list[str]:
    removed: list[str] = []
    if not RAW_DIR.exists():
        return removed
    targets = [RAW_DIR / name for name in SAMPLE_RAW_FOLDERS if (RAW_DIR / name).is_dir()]
    if not targets:
        return removed
    pretty = ", ".join(t.name for t in targets)
    if not confirm(f"Remove sample raw folder(s) [{pretty}]?", assume_yes):
        print("Skipped sample raw removal.")
        return removed
    for target in targets:
        shutil.rmtree(target)
        removed.append(str(target.relative_to(ROOT)))
    return removed


def wipe_wiki_outputs(assume_yes: bool) -> list[str]:
    wiped: list[str] = []
    if not WIKI_DIR.exists():
        return wiped
    candidates: list[Path] = []
    for sub in WIKI_GENERATED_SUBFOLDERS:
        folder = WIKI_DIR / sub
        if folder.exists():
            candidates.extend(p for p in folder.glob("*.md"))
    for name in WIKI_GENERATED_FILES:
        f = WIKI_DIR / name
        if f.exists():
            candidates.append(f)
    if not candidates:
        return wiped
    if not confirm(f"Wipe {len(candidates)} generated wiki page(s)?", assume_yes):
        print("Skipped wiki wipe.")
        return wiped
    for path in candidates:
        path.unlink()
        wiped.append(str(path.relative_to(ROOT)))
    return wiped


def rewrite_template_placeholders(slug: str) -> list[str]:
    if not TEMPLATES_DIR.exists():
        return []
    changed: list[str] = []
    for path in sorted(TEMPLATES_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        new_text = text.replace("topic: <topic>", f"topic: {slug}")
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed.append(str(path.relative_to(ROOT)))
    return changed


def update_readme_title(name: str) -> bool:
    if not README.exists():
        return False
    text = README.read_text(encoding="utf-8")
    new_text = re.sub(
        r"^# llmwiki.*$",
        f"# llmwiki — {name}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if new_text == text:
        return False
    README.write_text(new_text, encoding="utf-8")
    return True


def ensure_gitkeeps() -> list[str]:
    created: list[str] = []
    for folder in (RAW_DIR, WIKI_DIR):
        folder.mkdir(parents=True, exist_ok=True)
        keep = folder / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")
            created.append(str(keep.relative_to(ROOT)))
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True, help="Human-readable topic name, e.g. 'Industrial AI'")
    parser.add_argument("--slug", default=None, help="Topic slug used in frontmatter; default is slugified --name")
    parser.add_argument("--keep-raw", action="store_true", help="Do not remove the bundled sample raw/ folder(s)")
    parser.add_argument("--keep-wiki", action="store_true", help="Do not wipe existing generated wiki pages")
    parser.add_argument("--yes", action="store_true", help="Skip interactive confirmations")
    args = parser.parse_args()

    name = args.name.strip()
    slug = (args.slug or slugify(name)).strip()
    if not slug:
        print("error: could not derive a non-empty slug", file=sys.stderr)
        return 2

    print(f"Initializing topic: name='{name}', slug='{slug}'")
    print(f"Repo root: {ROOT}")

    summary: dict[str, list[str] | bool] = {}
    summary["sample_raw_removed"] = [] if args.keep_raw else remove_sample_raw(args.yes)
    summary["wiki_wiped"] = [] if args.keep_wiki else wipe_wiki_outputs(args.yes)
    summary["templates_updated"] = rewrite_template_placeholders(slug)
    summary["readme_updated"] = update_readme_title(name)
    summary["gitkeeps_created"] = ensure_gitkeeps()

    print("\nDone. Summary:")
    for key, value in summary.items():
        if isinstance(value, list):
            print(f"  {key}: {len(value)}")
            for entry in value:
                print(f"    - {entry}")
        else:
            print(f"  {key}: {value}")

    print(
        "\nNext steps:\n"
        "  1. Drop your topic content into raw/<YourSectionGroup>/\n"
        "  2. python3 scripts/bootstrap_wiki.py --scaffold-only\n"
        "  3. python3 scripts/build_index.py && python3 scripts/lint_wiki.py\n"
        "  4. Optional LLM enrichment: python3 scripts/bootstrap_wiki.py --max-files 50 --model <model>\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
