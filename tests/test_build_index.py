import hashlib
import json
import lzma
import os
import sqlite3
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import build_index  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name):
    with open(os.path.join(FIXTURES, name), "rb") as f:
        return f.read()


class ParseRecordTests(unittest.TestCase):
    def test_text_book_with_epub(self):
        row = build_index.parse_record(fixture("pg1342.rdf"))
        self.assertEqual(row[0], 1342)
        self.assertEqual(row[1], "Pride and Prejudice")
        self.assertEqual(row[2], "Austen, Jane")
        # LCSH subjects only; the LCC class "PR" is left out.
        self.assertEqual(
            row[3],
            "England -- Fiction; Young women -- Fiction; Love stories; Sisters -- Fiction; "
            "Domestic fiction; Courtship -- Fiction; Social classes -- Fiction",
        )
        self.assertTrue(row[4].startswith('"Pride and Prejudice" by Jane Austen is a novel'))
        self.assertEqual(row[5], "en")
        self.assertEqual(row[6], 208430)

    def test_text_placeholder_without_files_is_skipped(self):
        self.assertIsNone(build_index.parse_record(fixture("pg1073.rdf")))

    def test_sound_record_is_skipped(self):
        self.assertIsNone(build_index.parse_record(fixture("pg10152.rdf")))


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tar_path = os.path.join(self.tmp.name, "rdf-files.tar.bz2")
        with tarfile.open(self.tar_path, "w:bz2") as tar:
            for n in (1073, 10152, 1342):
                tar.add(os.path.join(FIXTURES, "pg%d.rdf" % n), "cache/epub/%d/pg%d.rdf" % (n, n))

    def test_main_writes_searchable_index_and_manifest(self):
        out = os.path.join(self.tmp.name, "out")
        build_index.main(["--rdf", self.tar_path, "--out", out])

        with open(os.path.join(out, "gutenberg.json")) as f:
            manifest = json.load(f)
        with open(os.path.join(out, "gutenberg.sqlite.xz"), "rb") as f:
            packed = f.read()
        self.assertEqual(manifest["books"], 1)
        self.assertEqual(manifest["size"], len(packed))
        self.assertEqual(manifest["sha256"], hashlib.sha256(packed).hexdigest())

        db_path = os.path.join(self.tmp.name, "unpacked.sqlite")
        with open(db_path, "wb") as f:
            f.write(lzma.decompress(packed))
        db = sqlite3.connect(db_path)
        self.addCleanup(db.close)
        hits = db.execute(
            "SELECT books.id FROM fts JOIN books ON books.id = fts.rowid WHERE fts MATCH ?",
            ("prejudice",),
        ).fetchall()
        self.assertEqual(hits, [(1342,)])
        # Subjects are searchable, summaries are stored but not indexed.
        self.assertEqual(
            db.execute("SELECT rowid FROM fts WHERE fts MATCH 'courtship'").fetchall(), [(1342,)]
        )
        self.assertEqual(db.execute("SELECT rowid FROM fts WHERE fts MATCH 'darcy'").fetchall(), [])


if __name__ == "__main__":
    unittest.main()
