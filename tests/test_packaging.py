from contextlib import closing
import hashlib
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('packager',Path(__file__).resolve().parents[1]/'scripts/mbtiles.py')
packager=importlib.util.module_from_spec(spec);spec.loader.exec_module(packager)

class PackagingTests(unittest.TestCase):
    def test_row_order_does_not_change_release_bytes_or_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,reverse in [('a',False),('b',True)]:
                metadata=[('name','test'),('format','png')]
                tiles=[(1,0,0,b'north'),(1,0,1,b'south')]
                if reverse:metadata.reverse();tiles.reverse()
                with closing(sqlite3.connect(root/name)) as db:
                    db.execute('CREATE TABLE metadata (name,value)');db.execute('CREATE TABLE tiles (zoom_level,tile_column,tile_row,tile_data)')
                    db.executemany('INSERT INTO metadata VALUES (?,?)',metadata);db.executemany('INSERT INTO tiles VALUES (?,?,?,?)',tiles);db.commit()
                packager.canonicalize(root/name,root/(name+'.mbtiles'))
            self.assertEqual(hashlib.sha256((root/'a.mbtiles').read_bytes()).digest(),hashlib.sha256((root/'b.mbtiles').read_bytes()).digest())
            with closing(sqlite3.connect(root/'a.mbtiles')) as db:
                self.assertEqual(db.execute('SELECT tile_data FROM tiles ORDER BY tile_row').fetchall(),[(b'north',),(b'south',)])
            with self.assertRaises(FileExistsError):packager.canonicalize(root/'a',root/'a.mbtiles')
