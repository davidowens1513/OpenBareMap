from contextlib import closing
import gzip
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('server',ROOT/'scripts/serve.py')
server=importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)

class ViewerTests(unittest.TestCase):
    def test_xyz_y_is_flipped_to_tms(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'map.mbtiles'
            north=gzip.compress(b'north')
            south=gzip.compress(b'south')
            with closing(sqlite3.connect(path)) as db:
                db.execute('CREATE TABLE tiles (zoom_level, tile_column, tile_row, tile_data)')
                db.executemany('INSERT INTO tiles VALUES (?,?,?,?)',[(1,0,1,north),(1,0,0,south)])
                db.commit()
            self.assertEqual(server.read_tile(path,1,0,0),north)
            self.assertEqual(server.read_tile(path,1,0,1),south)
            self.assertIsNone(server.read_tile(path,1,1,1))
            with self.assertRaises(ValueError):server.read_tile(path,1,0,2)

    def test_style_references_existing_schema_and_font(self):
        style=json.loads((ROOT/'style/openbaremap.json').read_text())
        schema=json.loads((ROOT/'config/tilemaker.json').read_text())['layers']
        ids=[l['id'] for l in style['layers']]
        self.assertEqual(len(ids),len(set(ids)))
        for layer in style['layers']:
            if 'source-layer' in layer:
                expected=schema if layer['source']=='basemap' else {'land','contour'}
                self.assertIn(layer['source-layer'],expected)
        self.assertTrue((ROOT/'viewer/fonts/Open Sans Regular/0-255.pbf').is_file())

    def test_vendored_asset_checksums(self):
        import hashlib
        lock=json.loads((ROOT/'viewer-assets.lock.json').read_text())
        for asset in lock['assets']:
            self.assertEqual(hashlib.sha256((ROOT/asset['path']).read_bytes()).hexdigest(),asset['sha256'])

    def test_coast_overzoom_matches_its_tile_layer_limit(self):
        style=json.loads((ROOT/'style/openbaremap.json').read_text())
        topography=json.loads((ROOT/'config/topography.json').read_text())
        self.assertEqual(style['sources']['coast']['maxzoom'],topography['land_maxzoom'])
        # The coast uses its own capped source so it remains visible at contour z14.
        self.assertLess(style['sources']['coast']['maxzoom'],topography['vector_maxzoom'])

    def test_elevation_grid_covers_the_whole_island(self):
        lock=json.loads((ROOT/'terrain-sources.lock.json').read_text())
        names={Path(asset['path']).name for asset in lock['assets']}
        expected={f'N{lat:02d}W{abs(lon):03d}.hgt.gz' for lat in range(51,56) for lon in range(-11,-5)}
        self.assertEqual(names,expected)

    def test_outdoor_sprite_atlases_are_complete_and_consistent(self):
        import hashlib
        import struct
        first=json.loads((ROOT/'viewer/sprites/outdoors.json').read_text())
        second=json.loads((ROOT/'viewer/sprites/outdoors@2x.json').read_text())
        expected={'outdoor-parking'}
        self.assertEqual(set(first),expected);self.assertEqual(set(second),expected)
        for suffix,index,ratio in [('',first,1),('@2x',second,2)]:
            data=(ROOT/f'viewer/sprites/outdoors{suffix}.png').read_bytes()
            width,height=struct.unpack('>II',data[16:24])
            for item in index.values():
                self.assertEqual(item['pixelRatio'],ratio)
                self.assertLessEqual(item['x']+item['width'],width)
                self.assertLessEqual(item['y']+item['height'],height)
        lock=json.loads((ROOT/'assets/sprites.lock.json').read_text())
        for item in lock['assets']:
            self.assertEqual(hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest(),item['sha256'])
        self.assertEqual(hashlib.sha256((ROOT/'scripts/build_sprites.py').read_bytes()).hexdigest(),lock['generator_sha256'])
