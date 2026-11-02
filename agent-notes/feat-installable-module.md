# gutenberg-index: make build_index installable

## Goal

Remove the second copy of the index schema in gutenberg_UI's tests
(`tests/test_catalog.py` typed `SCHEMA` out again). Part of QRead's Project
Gutenberg importer (QRead `agent-notes/feat-gutenberg-importer.md`).

## State

- This branch adds `pyproject.toml` (hatchling, wheel holds only
  `build_index.py`). Installs and imports on 32-bit Python 3.8.
- Follow-up in gutenberg_UI (separate PR, after this merges): tests import
  `build_index.SCHEMA` via
  `--with "gutenberg-index @ git+https://github.com/accessibleapps/gutenberg-index"`
  and delete their copy.

## Next step

Q decides the merge; then open the gutenberg_UI PR and watch its CI.
