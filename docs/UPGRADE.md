# Engine upgrade and release flow

The public [plant_wiki](https://github.com/ranga291257/plant_wiki) repo is the **engine**: `schema/`, `templates/`, `app/`, `scripts/`.

Your **topic content** (`raw/`, `wiki/`) stays local (or in a separate private repo). Engine upgrades should not overwrite those folders.

## Versioning

- Semver Git tags on the engine repo (e.g. `v0.1.0`).
- Downstream topic repos pin to a **tag**, not `main`.

Tag a release on the engine repo:

```bash
git checkout main
git pull --ff-only
git tag -a v0.1.0 -m "Engine v0.1.0: plant wiki template"
git push origin v0.1.0
```

Bump rules:

- **MAJOR** — breaking schema or required-section changes
- **MINOR** — new optional capability
- **PATCH** — fixes and docs with no behavior change

## Downstream upgrade: `git subtree`

In a topic repo that vendors the engine:

### One-time setup

```bash
git remote add plant-wiki-engine https://github.com/ranga291257/plant_wiki.git
git fetch plant-wiki-engine --tags
```

### Pull a new engine version

```bash
git fetch plant-wiki-engine --tags

git subtree pull --prefix=schema    plant-wiki-engine v0.1.0 --squash
git subtree pull --prefix=templates plant-wiki-engine v0.1.0 --squash
git subtree pull --prefix=app       plant-wiki-engine v0.1.0 --squash
git subtree pull --prefix=scripts   plant-wiki-engine v0.1.0 --squash
```

Then rebuild locally:

```bash
./run scripts/bootstrap_wiki.py --scaffold-only
./run scripts/build_index.py
./run scripts/lint_wiki.py
```

After a **MAJOR** schema change, re-ingest affected raw files:

```bash
./run scripts/oc_ingest.py raw/<topic>/<file>.md --model <model>
```

## Full re-template (MAJOR breaks only)

1. Create a fresh repo from the latest engine template.
2. Copy your `raw/` tree and any custom `schema/` edits.
3. `./run scripts/convert_raw_to_wiki.py`

## What not to do

- Do not edit `app/`, `scripts/`, or `templates/` in a downstream repo (changes are lost on subtree pull). Contribute upstream instead.
- Do not pin to engine `main`.
- Do not skip `lint_wiki.py` after an upgrade.
