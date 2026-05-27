# Plant Wiki — Web control panel

Local FastAPI UI (from the archived **llmwiki** control panel, adapted for plant_wiki).

## Start

```bash
./scripts/setup_venv.sh
export LLM_MODEL=gemma4:e2b   # or your Ollama model
./scripts/run_web.sh
```

Open http://127.0.0.1:8765

## What it does

| Section | API | CLI equivalent |
|---------|-----|----------------|
| Full conversion | `POST /api/convert-full` | `convert_raw_to_wiki.py` |
| Upload | `POST /api/upload` | copy into `raw/` manually |
| Ingest one file | `POST /api/ingest` | `oc_ingest.py` |
| Rebuild index + lint | `POST /api/update` | `build_index.py` + `lint_wiki.py` |
| Query | `POST /api/query` | `oc_query.py` |
| Save analysis | `POST /api/file-analysis` | `oc_file_analysis.py` |
| AI lint | `POST /api/lint-llm` | `oc_lint_ai.py` |
| Raw change tracker | `GET /api/changes` | compares `state/raw_snapshot.json` |

## Notes

- **Upload** writes flat files to `raw/` or `raw/assets/`. Topic subfolders (e.g. `raw/thermal-plant/...`) are easiest to add via filesystem, then use **Refresh changes**.
- **Full conversion** can take many minutes; keep the browser tab open.
- **`state/`** is gitignored — stores the raw-file snapshot baseline after a successful update/conversion.
- Not published to GitHub by default; optional local tooling only.

## Branch

Web UI lives on the `webgui` branch (merged to `main` when stable).
