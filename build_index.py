"""Build the Project Gutenberg search index from the official RDF catalog dump.

Output, in the --out directory:
  gutenberg.sqlite.xz  SQLite database: table books + FTS5 table fts, xz-compressed
  gutenberg.json       build date, book count, size and sha256 of the .xz file
"""

import argparse
import datetime
import hashlib
import json
import lzma
import os
import shutil
import sqlite3
import tarfile
import urllib.request
import xml.etree.ElementTree as ET

RDF_URL = "https://www.gutenberg.org/cache/epub/feeds/rdf-files.tar.bz2"
USER_AGENT = "gutenberg-index (https://github.com/accessibleapps/gutenberg-index)"

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
NS = {
    "rdf": RDF,
    "dcterms": "http://purl.org/dc/terms/",
    "pgterms": "http://www.gutenberg.org/2009/pgterms/",
    "dcam": "http://purl.org/dc/dcam/",
}
LCSH = "http://purl.org/dc/terms/LCSH"

SCHEMA = """
CREATE TABLE books(
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT NOT NULL,
    subjects TEXT NOT NULL,
    summary TEXT NOT NULL,
    language TEXT NOT NULL,
    downloads INTEGER NOT NULL
);
CREATE VIRTUAL TABLE fts USING fts5(
    title, authors, subjects,
    content='books', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2', detail=column
);
"""


def clean(text):
    return " ".join((text or "").split())


def parse_record(data):
    """Return a books row for a Text book that offers an EPUB, otherwise None.

    Sound, image and dataset records are skipped, and so are Text placeholders
    that carry no files (for example #1073, "No title", "See #1069").
    """
    ebook = ET.fromstring(data).find("pgterms:ebook", NS)
    if ebook is None:
        return None
    types = [v.text for v in ebook.findall("dcterms:type/rdf:Description/rdf:value", NS)]
    if "Text" not in types:
        return None
    formats = ebook.findall(
        "dcterms:hasFormat/pgterms:file/dcterms:format/rdf:Description/rdf:value", NS
    )
    if not any(f.text == "application/epub+zip" for f in formats):
        return None
    subjects = []
    for desc in ebook.findall("dcterms:subject/rdf:Description", NS):
        member = desc.find("dcam:memberOf", NS)
        if member is not None and member.get("{%s}resource" % RDF) == LCSH:
            subjects.append(clean(desc.findtext("rdf:value", "", NS)))
    return (
        int(ebook.get("{%s}about" % RDF).rsplit("/", 1)[1]),
        clean(ebook.findtext("dcterms:title", "", NS)),
        "; ".join(
            clean(n.text) for n in ebook.findall("dcterms:creator/pgterms:agent/pgterms:name", NS)
        ),
        "; ".join(subjects),
        "\n\n".join(clean(s.text) for s in ebook.findall("pgterms:marc520", NS)),
        ", ".join(
            clean(v.text)
            for v in ebook.findall("dcterms:language/rdf:Description/rdf:value", NS)
        ),
        int(ebook.findtext("pgterms:downloads", "0", NS)),
    )


def build(rdf_tar_path, db_path):
    """Write the index database from the RDF tarball; return the number of books."""
    if os.path.exists(db_path):
        os.remove(db_path)
    db = sqlite3.connect(db_path)
    db.executescript(SCHEMA)
    count = 0
    with tarfile.open(rdf_tar_path, "r:*") as tar:
        for member in tar:
            if not member.isfile() or not member.name.endswith(".rdf"):
                continue
            row = parse_record(tar.extractfile(member).read())
            if row is not None:
                db.execute("INSERT INTO books VALUES (?, ?, ?, ?, ?, ?, ?)", row)
                count += 1
    db.execute("INSERT INTO fts(fts) VALUES ('rebuild')")
    db.commit()
    db.execute("VACUUM")
    db.close()
    return count


def compress(src, dest):
    """xz-compress src to dest; return (size, sha256 hex) of dest."""
    with open(src, "rb") as fin, lzma.open(dest, "wb", preset=9 | lzma.PRESET_EXTREME) as fout:
        shutil.copyfileobj(fin, fout, 1 << 20)
    digest = hashlib.sha256()
    with open(dest, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return os.path.getsize(dest), digest.hexdigest()


def download(url, dest):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request) as response, open(dest, "wb") as f:
        shutil.copyfileobj(response, f, 1 << 20)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rdf", help="rdf-files.tar.bz2 already on disk (default: download it)")
    parser.add_argument("--out", default="dist", help="output directory")
    args = parser.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    rdf = args.rdf
    if rdf is None:
        rdf = os.path.join(args.out, "rdf-files.tar.bz2")
        download(RDF_URL, rdf)
    db_path = os.path.join(args.out, "gutenberg.sqlite")
    books = build(rdf, db_path)
    size, sha256 = compress(db_path, os.path.join(args.out, "gutenberg.sqlite.xz"))
    manifest = {
        "built": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "books": books,
        "size": size,
        "sha256": sha256,
    }
    with open(os.path.join(args.out, "gutenberg.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
