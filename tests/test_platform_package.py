from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('package_resources',ROOT/'scripts/package_resources.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class PlatformPackageTests(unittest.TestCase):
    def test_coast_source_caps_metadata_and_preserves_low_zoom_payloads(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'terrain.mbtiles';destination=Path(temp)/'coast.mbtiles'
            with closing(sqlite3.connect(source)) as db:
                db.execute('CREATE TABLE metadata(name,value)');db.execute('CREATE TABLE tiles(zoom_level,tile_column,tile_row,tile_data)')
                db.executemany('INSERT INTO metadata VALUES (?,?)',[('minzoom','4'),('maxzoom','14'),('json',json.dumps({'vector_layers':[{'id':'land','maxzoom':12},{'id':'contour','maxzoom':14}]}))])
                db.executemany('INSERT INTO tiles VALUES (?,?,?,?)',[(12,0,0,b'unchanged'),(13,0,0,b'excluded')])
                db.commit()
            module.build_capped_coast(source,destination)
            with closing(sqlite3.connect(destination)) as db:
                self.assertEqual(db.execute('SELECT tile_data FROM tiles').fetchall(),[(b'unchanged',)])
                metadata=dict(db.execute('SELECT name,value FROM metadata'))
                self.assertEqual(metadata['maxzoom'],'12')
                self.assertTrue(all(l['maxzoom']<=12 for l in json.loads(metadata['json'])['vector_layers']))
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
