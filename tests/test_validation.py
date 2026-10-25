import gzip
from contextlib import closing
import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('obm', Path(__file__).resolve().parents[1] / 'scripts/openbaremap.py')
obm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(obm)

class TileValidationTests(unittest.TestCase):
    def database(self, root, name, rows):
        path = Path(root) / name
        with closing(sqlite3.connect(path)) as db:
            db.execute('CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB)')
            db.executemany('INSERT INTO tiles VALUES (?,?,?,?)', rows)
            db.commit()
        return path

    def test_comparison_ignores_gzip_timestamp_and_insertion_order(self):
        with tempfile.TemporaryDirectory() as root:
            a = self.database(root, 'a', [(1,0,0,gzip.compress(b'one',mtime=1)), (1,1,0,gzip.compress(b'two',mtime=1))])
            b = self.database(root, 'b', [(1,1,0,gzip.compress(b'two',mtime=2)), (1,0,0,gzip.compress(b'one',mtime=2))])
            self.assertEqual(obm.inspect_tiles(a), obm.inspect_tiles(b))
            c = self.database(root, 'c', [(1,0,0,gzip.compress(b'changed',mtime=1))])
            self.assertNotEqual(obm.inspect_tiles(a), obm.inspect_tiles(c))

    def test_empty_and_invalid_tiles_fail(self):
        with tempfile.TemporaryDirectory() as root:
            for name, rows in [('empty', []), ('invalid', [(1,2,0,b'x')]), ('payload', [(1,0,0,b'')])]:
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        obm.inspect_tiles(self.database(root, name, rows))

    def test_blank_tile_with_real_content_is_valid(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.database(root, 'mixed', [(1,0,0,gzip.compress(b'',mtime=1)), (1,1,0,gzip.compress(b'content',mtime=1))])
            result = obm.inspect_tiles(path)
            self.assertEqual(result['tile_count'], 2)
            self.assertEqual(result['empty_tile_count'], 1)

    def test_build_names_cannot_escape_the_build_directory(self):
        import argparse
        for name in ['../outside','/tmp/output','.', '', 'two words']:
            with self.subTest(name=name):
                with self.assertRaises(argparse.ArgumentTypeError):obm.build_name(name)
        self.assertEqual(obm.build_name('ireland-outdoors-2026-a'),'ireland-outdoors-2026-a')
