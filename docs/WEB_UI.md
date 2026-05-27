# Plant Wiki — Web control panel

Local FastAPI UI (from the archived **llmwiki** control panel, adapted for plant_wiki).

**This file is the canonical reference** for the browser UI. [README.md](../README.md) and [OPERATOR.md](OPERATOR.md) link here instead of repeating the same tables.

## Start

```bash
./scripts/setup_venv.sh
./scripts/run_web.sh
```

Open http://127.0.0.1:8765. **Ollama must be running** before you open the page (models load automatically on load).

## UI layout (tabs)

The panel uses a **sticky header** plus five tabs (no long scroll of numbered sections):

| Tab | Purpose |
|-----|---------|
| **Convert** | Full batch conversion (LLM or scaffold only) |
| **Documents** | Upload one file + ingest one raw file |
| **Maintain** | Raw change tracker, rebuild index + lint, AI lint |
| **Ask** | Query wiki; save analysis (answers stay on this tab) |
| **Run log** | Command output table for convert, ingest, rebuild, AI lint |

**Run log on failure:** failed runs switch to **Run log** automatically; the tab and header chip turn red. Warnings use an amber dot/chip without auto-switching.

**Global model** (header): one dropdown for all LLM actions. Changing the model asks for confirmation, then re-fetches the model list from Ollama (no separate Refresh models button). Choice is stored in `sessionStorage`.

## Model list

The web UI loads models from `GET /api/ollama/models`, which queries local Ollama `GET /api/tags` and filters:

| Excluded | Rule |
|----------|------|
| Cloud models | name contains `:cloud` or ends with `-cloud` |
| Embedding models | `"embed"` in name, or family `nomic-bert` / `bert` |

Set `LLM_MODEL` in the environment to pre-select a model when it passes the filter. If Ollama is down, LLM actions are disabled (scaffold-only conversion still works).

## Tab details

### Convert

- **Convert all (LLM)** — `POST /api/convert-full` → `scripts/convert_raw_to_wiki.py` (LLM ingest on all markdown under `raw/`, scaffold/hub pages, `build_index.py`, `lint_wiki.py`). Can take several minutes.
- **Scaffold only** — see below.
- On **success**, updates `state/raw_snapshot.json` (raw change baseline).

#### Scaffold only

Builds the **wiki skeleton** from folder layout only — **no Ollama**, no reading note content.

| Step | What happens |
|------|----------------|
| Clean | Removes generated pages under `wiki/concepts/`, `entities/`, `sources/`, `analyses/`, `mocs/`, and `wiki/overview.md` (default; not `--no-clean`) |
| Skip LLM | No concept/entity pages from raw content |
| Scaffold | Per topic folder under `raw/` (e.g. `thermal-plant/`): catalog, corpus entity, hub MOC, plus `overview.md` |
| Link | Cross-links hub pages |
| Post | `build_index.py` + `lint_wiki.py --conversion-only` |

Use for layout tests or an empty graph shell. For real equipment/concept pages, run **Convert all (LLM)** or **Documents → Ingest**.

## Wiki graph (pyvis)

Interactive **link graph** (like Obsidian’s graph view): nodes = wiki `.md` pages, edges = resolved markdown links.

| Open from | URL / action |
|-----------|----------------|
| Control panel header | **Open graph** (new tab) |
| Direct | http://127.0.0.1:8765/wiki-graph |
| Offline CLI | `./run scripts/render_wiki_graph.py -o /tmp/wiki_graph.html` |

Nodes are colored by folder (`concepts`, `entities`, `mocs`, `sources`, etc.). **Orphan pages** (no links in or out) are omitted. Entity and concept nodes show short labels; other folders are dots only. Hover for the full path. Use the **Show:** checkboxes on the graph page to filter by folder (concepts, entities, …); **All** / **None** reset the selection.

**Expectations:** graph richness follows **links** in your pages (`## Related Pages`, body links). Scaffold-only wikis show a **small** graph (hub + catalog). Full LLM conversion produces more nodes. This is not Obsidian — no in-graph note editor or vault plugins. Re-open the tab after conversion to refresh.

Requires `pyvis` (`pip install -r requirements-web.txt`).

### Documents — Upload

- **Upload** — `POST /api/upload` → writes one file flat into `raw/` or `raw/assets/`.
- Does **not** create topic subfolders. For `raw/thermal-plant/equipment/...`, copy files on disk, then use **Maintain → Refresh changes**.

### Documents — Ingest one file

- **Ingest** — `POST /api/ingest` → `scripts/oc_ingest.py` for the selected raw markdown file (source summary + concept/entity pages).
- Does **not** automatically rebuild `wiki/index.md` or run structural lint; use **Maintain → Rebuild index + lint** after ingest unless you used full conversion.

### Maintain — Refresh & update wiki

**Purpose:** Maintain the generated vault after `raw/` or `wiki/` changed. This tab **does not** run LLM conversion — use **Convert** or **Documents → Ingest** for that.

#### Refresh changes

| | |
|--|--|
| **API** | `GET /api/changes` |
| **Action** | Hashes every file under `raw/` and `raw/assets/`, compares to `state/raw_snapshot.json`, lists **Added / Modified / Deleted** paths. |
| **Side effects** | None (read-only). Does **not** update the baseline. |
| **When to use** | After copying new notes into `raw/`, after upload, or to see what still differs from the last saved baseline. |

The summary line looks like: `Baseline: 0 | Current: 8 | Added: 8, Modified: 0, Deleted: 0`.

- **Baseline** — file count in the last saved snapshot.
- **Current** — file count now.
- **Added** — paths in `raw/` not in the baseline (or new since last successful rebuild/conversion).

If baseline is `0` and you have files under `raw/`, everything shows as **Added** until you complete **Rebuild index + lint** or a successful **Full conversion**.

#### Rebuild index + lint (primary action)

| | |
|--|--|
| **API** | `POST /api/update` |
| **Action** | Runs, in order: `build_index.py` → `lint_wiki.py --conversion-only` → `log_event.py` (wiki update log). |
| **On success** | Saves a new `state/raw_snapshot.json` so **Refresh changes** can show a clean diff next time. |
| **On failure** | Usually structural lint issues (missing `## Sources`, broken links, missing sections). Output appears in **Run log**. Baseline is **not** updated. |
| **CLI equivalent** | `./run scripts/build_index.py` then `./run scripts/lint_wiki.py --conversion-only` |

**What `build_index.py` does:** Regenerates `wiki/index.md` — table of contents linking overview, MOCs, sources, entities, concepts, and analyses.

**What structural lint does:** Checks required sections, review fields, `` `raw/...` `` backtick citations, broken wiki-internal links, and orphan pages (conversion-only mode relaxes some rules). This is **not** the same as AI lint.

#### AI lint

| | |
|--|--|
| **API** | `POST /api/lint-llm` |
| **Action** | Sends concept/entity/analysis/source pages to the LLM (header model). Reports semantic issues (contradictions, stale claims, missing links). |
| **Side effects** | None — advisory only; does not edit files or rebuild the index. |
| **CLI equivalent** | `./run scripts/oc_lint_ai.py --model <model>` |

#### Typical workflow (Maintain tab)

```text
1. Add or change files in raw/  →  Refresh changes (see Added/Modified)
2. Convert or ingest            →  wiki pages created/updated
3. Rebuild index + lint         →  index.md fresh, structural lint pass, baseline saved
4. (Optional) AI lint           →  semantic review only
```

### Ask

- **Ask** — `POST /api/query` → `oc_query.py` (answer from existing wiki pages).
- **Save as analysis** — `POST /api/file-analysis` → writes `wiki/analyses/<slug>.md`, then runs the same pipeline as **Rebuild index + lint**.

### Run log

Shows stdout/stderr from the last pipeline operation (full conversion, ingest, rebuild, AI lint) in a step table with expandable output.

## API quick reference

| Section | API | CLI equivalent |
|---------|-----|----------------|
| Convert tab | `POST /api/convert-full` | `convert_raw_to_wiki.py` |
| Documents upload | `POST /api/upload` | copy into `raw/` manually |
| Documents ingest | `POST /api/ingest` | `oc_ingest.py` |
| Maintain — refresh | `GET /api/changes` | compare `raw/` to `state/raw_snapshot.json` |
| Maintain — rebuild | `POST /api/update` | `build_index.py` + `lint_wiki.py --conversion-only` |
| Ask | `POST /api/query` | `oc_query.py` |
| Ask — save analysis | `POST /api/file-analysis` | `oc_file_analysis.py` (+ index/lint) |
| Maintain — AI lint | `POST /api/lint-llm` | `oc_lint_ai.py` |
| Header model list | `GET /api/ollama/models` | `ollama list` (filtered) |
| Wiki graph | `GET /wiki-graph` | `scripts/render_wiki_graph.py` |

## State and gitignore

- **`state/raw_snapshot.json`** — SHA-256 snapshot of `raw/` and `raw/assets/`; updated after successful **Rebuild index + lint** or successful **Full conversion**.
- **`state/`** is gitignored (local machine only).

## Notes

- **Full conversion** can take many minutes; keep the browser tab open.
- **Ingest one file** does not replace full conversion for a new corpus; it updates pages for that source only.
- Fix structural lint before expecting a clean **Rebuild index + lint** (missing `` `raw/thermal-plant/...` `` citations are a common failure).
