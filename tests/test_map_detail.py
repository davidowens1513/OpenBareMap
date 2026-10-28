from pathlib import Path
import json,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_map_detail import keep
class MapDetailTests(unittest.TestCase):
    def test_counties_and_national_borders_remain(self):
        for level in ('2','5','6'):self.assertTrue(keep('boundary',14,{'admin_level':level}))
        for level in ('7','8','9','10',''):self.assertFalse(keep('boundary',14,{'admin_level':level}))
    def test_twenty_metre_contours_and_hundred_metre_indices(self):
        for elevation in (20,40,60,80,100,1000):self.assertTrue(keep('contour',14,{'elevation':elevation}))
        for elevation in (10,30,50,90,150):self.assertFalse(keep('contour',14,{'elevation':elevation}))
    def test_legends_and_style_agree_with_selection(self):
        root=Path(__file__).resolve().parents[1];style=json.loads((root/'style/openbaremap.json').read_text())
        ids={l['id'] for l in style['layers']};self.assertNotIn('local-boundaries',ids);self.assertNotIn('contour-50m-lines',ids);self.assertIn('county-boundaries',ids)
        self.assertEqual(style['metadata']['contour_interval_metres'],20)
        self.assertNotIn('Local border',(root/'viewer/index.html').read_text());self.assertIn('20 m contours',(root/'viewer/index.html').read_text())
