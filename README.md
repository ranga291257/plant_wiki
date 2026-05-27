# Plant Wiki

Turn plant documentation in `raw/` into linked, citation-backed Markdown pages in `wiki/`, then browse them in [Obsidian](https://obsidian.md/).

## Attribution

This project is a **derivative implementation** of the workflow described in Andrej Karpathy's [**LLM Wiki**](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern. It is not the original gist. See [LICENSE](LICENSE) for this repository's MIT license and full attribution notice.

## What is in this repository

| Included on GitHub | Local only (gitignored) |
|--------------------|-------------------------|
| `app/`, `scripts/`, `schema/`, `templates/` | `raw/` — your source notes |
| `run`, `requirements.txt`, `.wikiignore` | `wiki/` — generated Obsidian vault |
| This README and [LICENSE](LICENSE) | `.venv/` — create with `setup_venv.sh` |

Never commit plant data, generated wiki pages, or virtual environments.

## Quick start

1. Clone the repository.
2. Add markdown notes under `raw/<your-topic>/` (e.g. `raw/thermal-plant/`).
3. Start [Ollama](https://ollama.com/) (local LLM).
4. Create the Python environment (once):

```bash
./scripts/setup_venv.sh
```

5. Run conversion:

```bash
./run scripts/convert_raw_to_wiki.py --model <your-ollama-model>
```

Scaffold-only (no LLM, structure test):

```bash
./run scripts/convert_raw_to_wiki.py --scaffold-only
```

6. Open the `wiki/` folder in Obsidian — start at `index.md` or your topic hub under `wiki/mocs/`.

## Architecture

```text
raw/       -> source-of-truth notes (immutable after intake; local only)
schema/    -> wiki rules and lint requirements
templates/ -> page blueprints for LLM generation
app/       -> core logic (ingest, link, lint)
scripts/   -> command entrypoints
wiki/      -> generated knowledge pages / Obsidian vault (local only)
```

## Main scripts

| Script | Role |
|--------|------|
| `convert_raw_to_wiki.py` | **Main entry:** LLM convert + scaffold + index + lint |
| `bootstrap_wiki.py` | Lower-level batch rebuild |
| `build_index.py` | Rebuild `wiki/index.md` |
| `lint_wiki.py` | Structural checks |
| `init_topic.py` | Initialize a new topic from this template |
| `oc_ingest.py` | Ingest one raw file (optional) |
| `oc_query.py` | Query existing wiki (optional) |
| `oc_file_analysis.py` | Save analysis to `wiki/analyses/` (optional) |
| `oc_lint_ai.py` | Semantic lint (optional) |

Maintainer rules: `schema/AGENTS.md`, `schema/review-rules.md`.

## Documentation (local)

Extended guides live under `docs/` (not required on GitHub):

- [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) — plain-English system tour
- [docs/OPERATOR.md](docs/OPERATOR.md) — operator runbook
- [docs/USAGE.md](docs/USAGE.md) — new topic / template usage
- [docs/UPGRADE.md](docs/UPGRADE.md) — engine upgrades via `git subtree`

## New topic from template

```bash
./run scripts/init_topic.py --name "<Topic>" --slug <topic-slug> --yes
```

## License

MIT — see [LICENSE](LICENSE).
