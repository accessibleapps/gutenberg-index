# gutenberg-index: build the catalog index

## Goal

Step 1 of QRead's Project Gutenberg importer (full plan and measurements:
QRead repo, `agent-notes/gutenberg-importer.md`). Publish a weekly,
xz-compressed SQLite search index of the Gutenberg catalog to this repo's
`latest` release for `gutenberg_UI` to download.

## State

- PR #1 (`feat/build-index`): `build_index.py`, tests on three real RDF
  records, `build.yml` (weekly + manual dispatch, publishes to `latest`),
  `test.yml`.
- Real build on the 2026-11-01 dump: 254 s, 78,091 books, 22,985,420 bytes.
- No release exists yet: `build.yml` can only be dispatched once it is on
  `main`, so the first release comes after the merge (merging is Q's decision).

## Decisions and why

- Only Text books that offer an EPUB: Text placeholders such as 1073 ("No
  title", "See #1069") have no files and would fail to download.
- FTS over title/authors/subjects only; summaries are stored but not indexed
  (indexing them made the file 50 MB compressed instead of 23 MB).
- The manifest is uploaded after the database, so a client never sees a
  manifest describing a database that is not there yet; the client checks
  sha256 anyway.

## Next step

After Q merges: dispatch "Build index", confirm both release assets exist and
the manifest's sha256 matches the database.
