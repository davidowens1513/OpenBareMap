import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from build_region_geometry import permanent_ice_class
from regions import CANADIAN_ROCKIES_REGIONS, PERMANENT_ICE, region_style


class PermanentIceTests(unittest.TestCase):
    def test_maps_only_permanent_glaciers_and_snowfields(self):
        for tags, expected in [
            ({'natural': 'glacier'}, 'glacier'),
            ({'natural': 'snowfield'}, 'permanent_snow'),
            ({'natural': 'glacier', 'glacier:type': 'snowfield'}, 'permanent_snow'),
            ({'natural': 'glacier', 'glacier:type': 'rock'}, None),
            ({'natural': 'snowfield', 'seasonal': 'yes'}, None),
            ({'natural': 'glacier', 'intermittent': 'yes'}, None),
            ({'surface': 'snow'}, None),
        ]:
            with self.subTest(tags=tags):
                self.assertEqual(permanent_ice_class(tags), expected)

    def test_ice_styles_are_opt_in_and_leave_contours_visible(self):
        for region in CANADIAN_ROCKIES_REGIONS:
            layers = region_style(region)['layers']
            ids = [layer['id'] for layer in layers]
            for kind, (_, color, outline, _) in PERMANENT_ICE.items():
                with self.subTest(region=region, kind=kind):
                    layer = layers[ids.index(kind)]
                    self.assertLess(ids.index('bare-rock-stipple'), ids.index(kind))
                    self.assertLess(ids.index(kind), ids.index('contours'))
                    self.assertEqual(layer['source-layer'], 'landcover')
                    self.assertEqual(layer['filter'], ['==', ['get', 'class'], kind])
                    self.assertEqual(layer['paint']['fill-color'], color)
                    self.assertEqual(layer['paint']['fill-outline-color'], outline)
        for region in ('ireland', 'picos-de-europa'):
            self.assertFalse(set(PERMANENT_ICE) & {layer['id'] for layer in region_style(region)['layers']})

    def test_high_tatras_shows_snowfields_and_excludes_glaciers(self):
        self.assertEqual(permanent_ice_class({'natural': 'glacier'}, glaciers_as_snowfields=True),
                         'permanent_snow')
        self.assertIsNone(permanent_ice_class({'natural': 'glacier', 'glacier:type': 'rock'},
                                             glaciers_as_snowfields=True))
        self.assertIsNone(permanent_ice_class({'natural': 'glacier', 'seasonal': 'yes'},
                                             glaciers_as_snowfields=True))
        layers = {layer['id']: layer for layer in region_style('high-tatras')['layers']}
        self.assertNotIn('glacier', layers)
        self.assertEqual(layers['permanent_snow']['source-layer'], 'permanent_ice')
