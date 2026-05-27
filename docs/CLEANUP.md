# Folder cleanup (2026-05-27)

Cleanup aligned with the three-folder comparison plan.

## Kept

- **plant_wiki** — primary engine and thermal-plant PoC
- GitHub: https://github.com/ranga291257/plant_wiki

## Archives

Backups stored under `../_archives/` (sibling to this repo):

| Archive | Contents |
|---------|----------|
| `backup-local-wiki-20260527.tar.gz` | `local-wiki` my-wiki, obsidian_llm_wiki, key docs |
| `backup-llmwiki-github-20260527.tar.gz` | Shallow clone of GitHub `llmwiki` repo (if present) |

Restore example:

```bash
tar -xzf ../_archives/backup-local-wiki-20260527.tar.gz -C /path/to/restore/
```

## Removed locally

- `dev/local-wiki/` — after backup
- `dev/llmwiki/` — was already absent on disk before cleanup

## GitHub

- `ranga291257/llmwiki` — archived (superseded by plant_wiki)
- `ranga291257/plant_wiki` — canonical public engine repo
