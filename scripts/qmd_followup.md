# QMD follow-up for llmwiki

QMD is not active in this repo today. This file is a future option.

## When QMD becomes useful
Use QMD when:
- `wiki/` has many markdown pages
- keyword search alone is insufficient
- you want local hybrid retrieval over markdown content

## Suggested indexing scope
- `wiki/**/*.md`
- optional: `schema/**/*.md`
- optional: curated `raw/**/*.md`

## Guardrail
Do not mix unrelated workspaces into one global memory pool.

## Practical usage (future)
- `qmd search` for exact phrases, identifiers, and field names
- `qmd query` for broader natural-language exploration
- keep `wiki/index.md` as the primary human navigation map
