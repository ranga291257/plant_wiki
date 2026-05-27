# Plant Wiki — Operator Guide

Runbook for day-to-day use. Start with [README.md](../README.md) if you are new here.

## Mental model

- `raw/` — source truth (local only; do not edit after intake)
- `wiki/` — generated knowledge (local only)
- `schema/` — required page structure and lint rules
- `./run scripts/...` — preferred way to invoke Python (uses `.venv` when present)

## Primary workflow

**Full conversion (recommended):**

```bash
./run scripts/convert_raw_to_wiki.py --model <your-ollama-model>
```

**Step-by-step equivalent:**

```bash
./run scripts/bootstrap_wiki.py --conversion-only
./run scripts/build_index.py
./run scripts/lint_wiki.py --conversion-only
```

**Scaffold only (no LLM):**

```bash
./run scripts/convert_raw_to_wiki.py --scaffold-only
```

## Optional incremental scripts

| Script | Purpose |
|--------|---------|
| `oc_ingest.py` | Ingest one new `raw/` file |
| `oc_query.py` | Ask a question using existing wiki pages |
| `oc_file_analysis.py` | Save Q&A into `wiki/analyses/` |
| `oc_lint_ai.py` | Semantic lint (optional) |
| `build_index.py` | Rebuild `wiki/index.md` |
| `lint_wiki.py` | Structural lint |
| `log_event.py` | Append to `wiki/log.md` |

Example — add one source file:

```bash
./run scripts/oc_ingest.py raw/thermal-plant/procedures/new-sop.md --model <model>
```

## After schema or template changes

1. Edit `schema/*.md` and/or `templates/*.md`
2. `./run scripts/bootstrap_wiki.py`
3. `./run scripts/build_index.py`
4. `./run scripts/lint_wiki.py`

## Required wiki sections

Every substantive page must include (from `schema/AGENTS.md`):

- `## Purpose`, `## Assumptions`, `## Review`, `## Sources`, `## Related Pages`, `## Unresolved Questions`

Use `- None yet` for empty sections. Every substantive page needs `` `raw/...` `` citations in `## Sources`.

## Common mistakes

- Editing files in `raw/` after intake
- Committing `raw/` or `wiki/` to Git (they are gitignored by design)
- Broken `` `raw/...` `` paths (use full paths, e.g. `raw/thermal-plant/...`)
- Skipping lint after ingest

## Web control panel

Optional browser UI: `./scripts/run_web.sh` → http://127.0.0.1:8765. All sections, APIs, and Step 3 (refresh vs rebuild vs AI lint): **[WEB_UI.md](WEB_UI.md)**.

CLI-only maintenance after edits: `./run scripts/build_index.py` then `./run scripts/lint_wiki.py --conversion-only`.

## See also

- [HOW_IT_WORKS.md](HOW_IT_WORKS.md) — conceptual tour
- [WEB_UI.md](WEB_UI.md) — control panel sections 0–5
- [USAGE.md](USAGE.md) — new topic from template
- [UPGRADE.md](UPGRADE.md) — engine upgrades
