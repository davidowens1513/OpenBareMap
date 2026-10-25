"""Canonical MBTiles packaging: stable row order, schema and SQLite page layout."""
from contextlib import closing
from pathlib import Path
import sqlite3


def canonicalize(source, destination):
    source=Path(source).resolve()
    destination=Path(destination).resolve()
    if destination.exists():raise FileExistsError(destination)
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as src, closing(sqlite3.connect(destination)) as dst:
        dst.execute('PRAGMA page_size=4096')
        dst.execute('PRAGMA auto_vacuum=NONE')
        dst.execute('CREATE TABLE metadata (name TEXT NOT NULL, value TEXT)')
        dst.execute('CREATE TABLE tiles (zoom_level INTEGER NOT NULL, tile_column INTEGER NOT NULL, tile_row INTEGER NOT NULL, tile_data BLOB NOT NULL, PRIMARY KEY(zoom_level,tile_column,tile_row))')
        dst.executemany('INSERT INTO metadata VALUES (?,?)',src.execute('SELECT name,value FROM metadata ORDER BY name,value'))
        dst.executemany('INSERT INTO tiles VALUES (?,?,?,?)',src.execute('SELECT zoom_level,tile_column,tile_row,tile_data FROM tiles ORDER BY zoom_level,tile_column,tile_row'))
        dst.commit()
        dst.execute('VACUUM')
        if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Canonical database failed integrity check')
