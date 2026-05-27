# How Plant Wiki Works

This guide explains the whole system in plain English: what it does, what each folder is for, what each script does, and how to browse the result in Obsidian.

---

## 1. The story in one page

You start with **original notes** (field notes, datasheets, procedures) saved as markdown files.

You put them in **`raw/`** and leave them alone after that. They are your **source of truth** — like original photocopies you never scribble on.

You run **one command**. A local **LLM** (Large Language Model — an AI program running on your computer via Ollama) reads each raw file and writes **organized wiki pages** in **`wiki/`**. Those pages:

- use the same headings every time (Purpose, Sources, Related Pages, etc.)
- **link to each other** so topics connect
- always say which **`raw/...` file** each fact came from (a **citation**)

You open **`wiki/` in Obsidian** (a note-taking app). Obsidian draws a **graph** — a map of dots (notes) and lines (links). You click a dot to open a note and follow links to drill down.

```text
raw/  -->  LLM + scripts  -->  wiki/  -->  Obsidian graph
(original)   (organize)         (structured)   (browse & explore)
```

**Human approval is optional.** For this exercise, pages are marked **Converted** (auto-generated). You can review them later if you want; you do not need to approve them before using the wiki.

---

## 2. Folder tour

Think of the repo like a small factory:

| Folder | Plain meaning |
|--------|----------------|
| **`raw/`** | Incoming originals. **Do not edit** after you add them. |
| **`wiki/`** | Finished, organized pages the system writes. Safe to read and browse. |
| **`schema/`** | Rule book for the LLM and scripts (required sections, citation rules). |
| **`templates/`** | Blank forms the LLM fills in (concept page shape, entity page shape, etc.). |
| **`app/`** | Python code brains (ingest, linking, lint helpers). |
| **`scripts/`** | Commands you actually run from the terminal. |
| **`docs/`** | Human guides (this file, usage, upgrade). |

### What lives inside `wiki/`

| Subfolder | What it holds |
|-----------|----------------|
| **`mocs/`** | **Maps of Content (MOCs)** — hub pages that link to everything in one topic area. Start here to navigate. |
| **`sources/`** | Summaries of raw files and catalogs listing all files in a collection. |
| **`entities/`** | Things with tags: equipment (SC-101), valves (FCV-103), loops (TIC-102). |
| **`concepts/`** | Ideas: heat balance, PID tuning, integral windup. |
| **`analyses/`** | Longer write-ups from Q&A (optional; not part of basic conversion). |
| **`guides/`** | Help pages about using Obsidian with this wiki. |
| **`index.md`** | Table of contents (auto-rebuilt). |
| **`overview.md`** | Short summary of what collections exist. |

---

## 3. Glossary

| Term | Simple meaning |
|------|----------------|
| **LLM** | AI text model (here: via Ollama on your machine) that reads raw notes and writes structured pages. |
| **Ollama** | Program that runs LLM models locally. Must be running for full conversion. |
| **Vault** | In Obsidian, the folder you open as your notebook. Here: the **`wiki/`** folder. |
| **MOC** | “Map of Content” — a hub page that links to related notes (e.g. Thermal Plant Hub). |
| **Scaffold** | Skeleton pages (index, hub, catalog) built **without** the LLM — structure only, no topic depth. |
| **Citation** | A line like `` `raw/thermal-plant/equipment/steam-coil-sc101-datasheet.md` `` proving where info came from. |
| **Graph filter** | Obsidian setting that hides some folders so the map is less cluttered. |
| **Converted** | Status meaning “auto-built from raw; not yet human-reviewed.” Fine for this exercise. |

---

## 4. Step-by-step: convert your raw notes

### Before you start

1. **Python 3** installed.
2. **Project virtual environment** (recommended — keeps Python isolated to this repo):

```bash
./scripts/setup_venv.sh
```

Then always run scripts via:

```bash
./run scripts/convert_raw_to_wiki.py
```

In **Cursor**, opening a terminal in this folder should auto-activate `.venv` (see `.vscode/settings.json`).

3. **Ollama** installed and running (for full conversion, not scaffold-only).
3. Raw files are **markdown** (`.md`) under a folder like `raw/thermal-plant/`.

Check Ollama (optional):

```bash
curl -s http://localhost:11434/api/tags
```

If that fails, start Ollama first.

### Convert everything

From the repo root:

```bash
./run scripts/convert_raw_to_wiki.py
```

That single command:

1. Reads every markdown file under `raw/`
2. Calls the LLM to create source, concept, and entity pages
3. Builds hub, catalog, and overview pages
4. Links pages together for Obsidian
5. Rebuilds `wiki/index.md`
6. Checks structure with the linter

### Scaffold only (no LLM)

If Ollama is not available, you can build the skeleton only:

```bash
python3 scripts/convert_raw_to_wiki.py --scaffold-only
```

You get index, hub, and catalog — but **no concept/entity pages** and a sparse graph. Useful for testing folder layout, not for real content.

### What appears after a full conversion

For each raw file, the LLM typically creates:

- one **source summary** in `wiki/sources/`
- up to **3 concept pages** in `wiki/concepts/`
- up to **2 entity pages** in `wiki/entities/`

Plus, for each top-level folder under `raw/` (e.g. `thermal-plant/`):

- a **catalog** listing all raw files
- a **corpus entity** representing the whole folder
- a **hub MOC** linking concepts, entities, and summaries

---

## 5. Step-by-step: browse in Obsidian

### Open the vault

The vault is **`wiki/`**, not the whole repo.

**Option A — Obsidian UI**

1. Open Obsidian.
2. Click the vault icon (bottom-left) → **Open folder as vault**.
3. Choose: `.../plant_wiki/wiki`

**Option B — Terminal** (use vault ID to avoid confusion with other repos named `wiki`):

```bash
xdg-open "obsidian://open?vault=d9b7a2712d8874e3"
```

### Show the ribbon (left icon bar)

If you do not see icons on the far left:

- Press **Ctrl+P** → type **Ribbon** → **Ribbon: Show/hide ribbon**

### Start reading

1. Open **`index.md`** or **`mocs/thermal-plant-hub.md`**
2. Click links to move between pages
3. Every page’s **`## Sources`** section points back to `raw/...`

### Open the graph

1. Click the **connected-dots icon** on the ribbon, or **Ctrl+P** → **Graph view: Open graph view**
2. Each **dot** is a note; each **line** is a link between notes
3. **Click a dot** to open that note
4. For a small neighborhood around one note: **Ctrl+P** → **Graph view: Open local graph**

The default graph filter shows plant content (mocs, sources, entities, concepts) and hides setup guides.

More detail: [wiki/guides/obsidian-getting-started.md](../wiki/guides/obsidian-getting-started.md)

---

## 6. What each script does

| Script | What it does | When you use it |
|--------|----------------|-----------------|
| **`convert_raw_to_wiki.py`** | **Main command.** Runs bootstrap + index + lint with conversion defaults. | **Start here.** After adding or changing raw files. |
| **`bootstrap_wiki.py`** | Batch LLM ingest + scaffold + linking. Lower-level; used by convert script. | Advanced control (`--max-files`, `--no-clean`). |
| **`build_index.py`** | Rebuilds `wiki/index.md` from folder contents. | Usually automatic; run alone if you added pages by hand. |
| **`lint_wiki.py`** | Checks required sections, citations, broken links. | Automatic; run alone to verify wiki health. |
| **`oc_ingest.py`** | Convert **one** new raw file + update index/lint/log. | When you add a single file later. |
| **`oc_query.py`** | Ask a question using existing wiki pages. | Optional; not needed for basic conversion. |
| **`init_topic.py`** | Reset repo for a new topic. | When forking the template for a different plant/project. |

### What `app/llm_ingest.py` does (the brain)

For one raw file it:

1. Sends the raw text + rules + template to Ollama
2. Writes a source summary page
3. Asks the LLM which concepts and entities deserve pages
4. Creates or updates those pages
5. In conversion mode, sets **Status: Converted**

### What `app/link_pages.py` does

After pages exist, it:

1. Updates the **hub** with links to all concepts, entities, and source summaries
2. Adds **Related Pages** links back to the hub from each generated page

That is what makes the Obsidian graph useful instead of a few lonely dots.

---

## 7. What the LLM creates per raw file

```text
raw/thermal-plant/equipment/steam-coil-sc101-datasheet.md
        |
        +--> wiki/sources/steam-coil-sc101-datasheet.md  (summary)
        +--> wiki/concepts/heat-exchanger-duty.md       (example concept)
        +--> wiki/entities/sc-101.md                    (example entity)
        |
        +--> all linked from mocs/thermal-plant-hub.md
```

The exact concept and entity names depend on what the raw file mentions and what the LLM extracts.

---

## 8. Troubleshooting

| Problem | Likely cause | What to do |
|---------|----------------|------------|
| Graph shows only 2–5 nodes | Ran **scaffold-only** or LLM failed | Run full `convert_raw_to_wiki.py` with Ollama running |
| `Connection refused` / Ollama errors | Ollama not running | Start Ollama; check `OLLAMA_URL` and `LLM_MODEL` |
| Obsidian “Vault not found” | Wrong URI or unencoded path | Use vault ID: `obsidian://open?vault=d9b7a2712d8874e3` |
| No ribbon / no graph icon | Ribbon hidden | Ctrl+P → Ribbon: Show/hide ribbon |
| Lint fails on orphan pages | Page has no links to it | Run convert again (link step) or add a link from hub/index |
| Empty `wiki/concepts/` | LLM not run or raw files have little extractable content | Check Ollama logs; try a richer raw file |

---

## 9. Optional web control panel

`./scripts/run_web.sh` → http://127.0.0.1:8765 — same workflows as the CLI, in the browser. **Section 3 does not run LLM conversion** (it refreshes the raw change list and rebuilds `wiki/index.md` + structural lint). Details: [WEB_UI.md](WEB_UI.md).

## 10. Optional vs required

- **Required for a useful wiki:** `convert_raw_to_wiki.py` (full run), Obsidian on `wiki/`
- **Optional:** web UI (`run_web.sh`), `oc_ingest.py`, `oc_query.py`, `oc_file_analysis.py`, human review workflow (Draft → Approved)
- **Never:** edit files in `raw/` after intake — add new files instead

Default conversion marks pages **Converted** (auto). You can change **Status** in `## Review` later.

---

## 11. Where to read next

- [README.md](../README.md) — quick start
- [WEB_UI.md](WEB_UI.md) — browser control panel
- [OPERATOR.md](OPERATOR.md) — commands and workflows
- [schema/AGENTS.md](../schema/AGENTS.md) — maintainer rules
- [wiki/guides/obsidian-getting-started.md](../wiki/guides/obsidian-getting-started.md) — Obsidian tips (local vault)
