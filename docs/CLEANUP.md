# Folder cleanup (2026-05-27)

Cleanup aligned with the three-folder comparison plan.

## Kept

- **plant_wiki** — primary engine and thermal-plant PoC
- GitHub: https://github.com/ranga291257/plant_wiki

## Archives

Backups stored under `../_archives/` (sibling to this repo):

| Archive | Contents |
|---------|----------|
| `backup-local-wiki-20260527.tar.gz` | `local-wiki` my-wiki, obsidian_llm_wiki, key docs (~7k paths) |
| `backup-llmwiki-local-20260527.tar.gz` | Full `llmwiki/raw` + `llmwiki/wiki` (DT corpus, ~860 paths) |
| `backup-llmwiki-github-20260527.tar.gz` | Shallow GitHub clone only (engine on `main`; not the DT vault) |

Restore example:

```bash
tar -xzf ../_archives/backup-local-wiki-20260527.tar.gz -C /path/to/restore/
```

## Removed locally

- `dev/local-wiki/` — removed after backup (2026-05-27)
- `dev/llmwiki/` — removed after `backup-llmwiki-local-20260527.tar.gz` (re-check found folder had returned)

## GitHub

- `ranga291257/llmwiki` — archived (superseded by plant_wiki)
- `ranga291257/plant_wiki` — canonical public engine repo
