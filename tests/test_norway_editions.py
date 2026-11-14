"""Coverage contracts for the three independently installable Norway maps."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from regions import profile


class NorwayEditionTests(unittest.TestCase):
    def test_both_join_towns_have_full_detail_in_both_neighbours(self):
        for a, b, town in [('norway-south', 'norway-central', 'trondheim'),
                           ('norway-central', 'norway-north', 'bodo')]:
            left, right = profile(a), profile(b)
            self.assertEqual(left['destinations'][town], right['destinations'][town])
            lon, lat, _ = left['destinations'][town]
            for p in (left, right):
                w, s, e, n = p['bounds']
                self.assertTrue(w < lon < e and s < lat < n)
                self.assertEqual(p['maxzoom'], 14)
                self.assertEqual(p['contourIntervalMetres'], 20)
            self.assertEqual(left['gridCRS'], right['gridCRS'])
            self.assertEqual(left['sourceDate'], right['sourceDate'])
            self.assertEqual(left['sourceCacheRegion'], right['sourceCacheRegion'])
            self.assertEqual(left['bounds'][3] - right['bounds'][1], .5)

    def test_metre_grid_covers_the_complete_rectangular_editions(self):
        from pyproj import Transformer
        for region in ('norway-south', 'norway-central', 'norway-north'):
            p = profile(region)
            transform = Transformer.from_crs('EPSG:4326', p['gridCRS'], always_xy=True)
            w, s, e, n = p['bounds']; x0, x1, y0, y1 = p['gridExtent']
            for i in range(101):
                q = i / 100
                for lon, lat in [(w+(e-w)*q, s), (w+(e-w)*q, n),
                                 (w, s+(n-s)*q), (e, s+(n-s)*q)]:
                    x, y = transform.transform(lon, lat)
                    self.assertTrue(x0 <= x <= x1 and y0 <= y <= y1,
                                    (region, lon, lat, x, y))

    def test_preview_labels_and_norway_ids_match_the_editions(self):
        catalog = json.loads((ROOT / 'config/preview-regions.json').read_text())
        for region in ('norway-south', 'norway-central', 'norway-north'):
            entry, = [e for e in catalog if e['id'] == region]
            self.assertEqual(entry['label'], profile(region)['label'])
            self.assertIn('/' + region + '/index.html', entry['url'])
