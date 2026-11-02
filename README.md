# gutenberg-index

A compact, searchable index of the Project Gutenberg catalog, used by QRead's
Project Gutenberg importer.

Every Monday a GitHub Action downloads Gutenberg's RDF catalog dump
(`https://www.gutenberg.org/cache/epub/feeds/rdf-files.tar.bz2`), runs
`build_index.py`, and publishes two files to the
[`latest` release](https://github.com/accessibleapps/gutenberg-index/releases/tag/latest):

- `gutenberg.sqlite.xz`: an xz-compressed SQLite database.
- `gutenberg.json`: `built` (UTC time), `books` (row count), and the `size` and
  `sha256` of `gutenberg.sqlite.xz`.

## Database

`books(id, title, authors, subjects, summary, language, downloads)` holds every
Text book that offers an EPUB. `authors` and `subjects` (Library of Congress
subject headings) are joined with `"; "`. `summary` is Gutenberg's summary and
may be empty. `downloads` is Gutenberg's recent download count.

`fts` is an FTS5 index over `title`, `authors` and `subjects`, with `books` as its
external content (`rowid` = `books.id`).

## Build locally

```
python build_index.py --out dist                  # downloads the dump
python build_index.py --rdf rdf-files.tar.bz2     # uses a dump already on disk
python -m unittest discover -s tests
```

Only the Python standard library is needed.

The catalog data comes from Project Gutenberg and is in the public domain
(CC0, as stated in each RDF record).
