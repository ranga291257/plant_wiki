# AGENTS.md - Plant Wiki Maintainer Schema

## Role
Maintain a persistent wiki from trusted raw source documents.

## Mission
Turn raw material into interlinked, citation-backed markdown pages that stay maintainable over time.

## Core rules
- Never edit files in `raw/`.
- Treat `raw/` as the immutable source of truth.
- Prefer updating existing wiki pages over creating duplicates.
- Preserve uncertainty explicitly when evidence is incomplete.
- Distinguish facts, interpretations, hypotheses, and open questions.
- Add citations to raw source files whenever possible.
- Treat missing `raw/...` citations as invalid knowledge for this workflow.
- Keep pages concise, linked, and scoped.
- Enforce a consistent page structure so linting and retrieval remain predictable.

## Required sections on every substantive wiki page
Every substantive page under `wiki/` should include these sections unless clearly not applicable:
- `## Purpose`
- `## Assumptions`
- `## Review`
- `## Sources`
- `## Related Pages`
- `## Unresolved Questions`

If a section is not yet populated, write `- None yet` instead of omitting it.

## Directory model
- `raw/` -> source documents
- `wiki/` -> generated and maintained markdown pages
- `schema/` -> maintenance rules and conventions
- `templates/` -> page-shape templates used by generation
- `scripts/` -> helper tooling

## Wiki page families
- `wiki/index.md` -> content index
- `wiki/log.md` -> chronological log
- `wiki/overview.md` -> top-level summary
- `wiki/sources/` -> source summary pages
- `wiki/entities/` -> entity pages
- `wiki/concepts/` -> concept pages
- `wiki/analyses/` -> durable analysis pages

## Ingest workflow
When ingesting a new source:
1. Read the raw file.
2. Create or update source, concept, and entity pages.
3. Preserve prior citations while adding new evidence.
4. Update `wiki/index.md`.
5. Append to `wiki/log.md`.

## Query workflow
When answering a question:
1. Read `wiki/index.md` first.
2. Read the most relevant wiki pages.
3. Synthesize an answer with citations to wiki pages and raw sources.
4. If answer is durable, save it under `wiki/analyses/`.

## Lint workflow
Periodically check for:
- orphan pages
- broken links
- missing required sections
- missing review fields
- missing `raw/...` citations
- unresolved contradictions

## Page conventions
- Use markdown.
- Prefer short sections and bullet lists.
- Use internal relative links where possible.
- Add explicit source traceability on every substantive page.
- Apply review rules from `schema/review-rules.md`.

## Suggested maintainer instruction
Read only from `raw/`. Create and update pages in `wiki/`. Preserve source traceability. Keep uncertainty explicit.

## Plant tagging (thermal-plant corpus)

Primary corpus: `raw/thermal-plant/`.

- Use ISA-style entity slugs where possible (examples: `steam-coil-sc101`, `tt-102`, `fcv-103`, `tic-102`, `t-201`, `p-101`).
- On entity pages, when evidence exists in `raw/`, document relationships explicitly:
  - **measures** — what process variable an instrument reads
  - **controls** — what actuator or valve a loop or controller drives
  - **interlocked_with** — safety or process interlocks involving the tag
- Interlock and safety-critical pages must remain `Draft` until a human reviewer signs off in `## Review`.
- Link procedures (SOPs) to the equipment and instruments they reference.
- Link control-logic sources to the loops and tuning concepts they implement.
