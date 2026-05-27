# Usage: template and new topics

Use this repo as a **wiki engine**. Your plant notes live under `raw/`; generated pages live under `wiki/`. Neither is published to GitHub — see [README.md](../README.md).

## Documentation map

- [README.md](../README.md) — quick start
- [HOW_IT_WORKS.md](HOW_IT_WORKS.md) — how the system fits together
- [OPERATOR.md](OPERATOR.md) — commands and workflows
- [UPGRADE.md](UPGRADE.md) — engine version upgrades

## Start a new topic locally

1. Clone [plant_wiki](https://github.com/ranga291257/plant_wiki).
2. Initialize the topic (optional — clears any local sample folders and wiki output):

   ```bash
   ./run scripts/init_topic.py --name "Thermal Plant" --slug thermal-plant --yes
   ```

   This rewrites `<topic>` placeholders in `templates/`, updates the README title, and ensures `raw/` and `wiki/` exist. It does not change `schema/`, `app/`, or `scripts/`.

3. Add markdown under `raw/<your-topic>/` (e.g. `raw/thermal-plant/equipment/...`).
4. Run conversion:

   ```bash
   ./run scripts/convert_raw_to_wiki.py --model <your-ollama-model>
   ```

5. Open `wiki/` in Obsidian — start at `wiki/index.md` or `wiki/mocs/<topic>-hub.md`.

## OneNote export workflow

Treat each **section group** as one corpus under `raw/<SectionGroupName>/`.

1. Export pages to Markdown (one `.md` per page).
2. Skip recycle bins and scratch folders; `.wikiignore` also filters common junk names.
3. Run conversion as above.

The engine creates one hub MOC, catalog source page, and corpus entity per top-level folder under `raw/`.

## GitHub template (maintainers)

To offer **Use this template** on GitHub:

1. Repo **Settings → General → Template repository**.
2. Tag a release (e.g. `v0.1.0`) — see [UPGRADE.md](UPGRADE.md).
3. Consumers create `plant-wiki-<topic>` from the template.

Downstream repos should pull engine updates via `git subtree` (engine paths only), not copy `raw/` or `wiki/` from upstream.

## CI note

This repository does **not** run CI that commits `wiki/` or publishes MkDocs. Rebuild and browse locally.

Optional local MkDocs preview of the vault: see `mkdocs.yml` (requires `pip install mkdocs-material`).
