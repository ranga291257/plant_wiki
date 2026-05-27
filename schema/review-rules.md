# Review Rules

## Purpose
Define acceptance criteria for promoting wiki pages from Draft to Reviewed or Approved.

## Status definitions
- `Draft`: working content, not yet peer-checked.
- `Converted`: auto-generated from raw sources; not yet human-reviewed (used in conversion-only runs).
- `Reviewed`: peer-checked for consistency and citation quality.
- `Approved`: accepted for reuse in this wiki.

## Required review fields
Every substantive page in `wiki/sources/`, `wiki/entities/`, `wiki/concepts/`, and `wiki/analyses/` must include:
- `Status`
- `Reviewer`
- `Last reviewed`
- `Source confidence`
- `Safety critical`

## Citation rule (non-negotiable)
No `raw/...` source citation means the page is invalid for this workflow.

## Citation quality
- Cite source files directly as `` `raw/...` `` in `## Sources`.
- Prefer multiple citations when a claim combines multiple raw files.
- Keep interpretation separate from source facts.

## Safety critical handling
- If `Safety critical: Yes`, keep status at `Draft` until named reviewer signs off.
- Record unresolved safety concerns in `## Unresolved Questions`.
- Avoid prescriptive language without supporting source evidence.
