"""Coverage and portability checks for the park and its full 25 km surroundings."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'work/python')]
from regions import profile,region_style
from shapely.geometry import shape,Point,Polygon
from shapely.ops import transform
from pyproj import Transformer

class SierraNevadaTests(unittest.TestCase):
    def geometry(self,name):
        return shape(json.loads((ROOT/'regions/sierra-nevada'/(name+'.geojson')).read_text())['features'][0]['geometry'])

    def test_official_boundary_source_is_pinned(self):
        source=json.loads((ROOT/'regions/sierra-nevada/boundary-source.json').read_text())
        actual=hashlib.sha256((ROOT/'data/regions/sierra-nevada/boundary/Limites_PPNN.kml').read_bytes()).hexdigest()
        self.assertEqual(source['boundaryKMLSHA256'],actual)
        self.assertEqual(source['bufferMetres'],25000)
        self.assertEqual(source['bufferCRS'],'EPSG:25830')

    def test_buffer_covers_whole_park_with_25km_edge_distance(self):
        t=Transformer.from_crs(4326,25830,always_xy=True).transform
        park=transform(t,self.geometry('park-boundary'));coverage=transform(t,self.geometry('coverage'))
        self.assertTrue(park.is_valid and coverage.is_valid and coverage.covers(park))
        self.assertTrue(850<park.area/1e6<870)
        for point in coverage.exterior.coords:
            self.assertAlmostEqual(Point(point).distance(park),25000,delta=3)

    def test_native_and_web_styles_keep_boundary_geometry_offline(self):
        style=region_style('sierra-nevada')
        self.assertIn('utm-grid',style['sources'])
        self.assertNotIn('british-grid',style['sources'])
        self.assertNotIn('name_ga',json.dumps(style))
        for name in ['park-boundary','coverage','coverage-mask']:
            source=style['sources'][name]
            self.assertIsInstance(source['data'],dict)
            self.assertTrue(source['data']['features'])
        self.assertEqual(style['layers'][-3]['id'],'coverage-mask')
        self.assertEqual(style['layers'][-2]['id'],'park-boundary')
        self.assertEqual(style['layers'][-1]['id'],'coverage-boundary')

    def test_map_extent_includes_all_requested_coverage(self):
        from shapely.geometry import box
        p=profile('sierra-nevada')
        self.assertTrue(box(*p['bounds']).covers(self.geometry('coverage')))
        self.assertEqual(p['mapVersion'],'2.0.0')
        self.assertEqual(p['nativeLanguage'],'es')

    def test_garmin_selection_envelope_covers_requested_footprint(self):
        path=ROOT/'regions/sierra-nevada/garmin/coverage.poly'
        if not path.exists():self.skipTest('Build Garmin selection first')
        rows=path.read_text().splitlines()[2:-2]
        polygon=Polygon([tuple(map(float,row.split())) for row in rows])
        self.assertTrue(polygon.is_valid)
        self.assertTrue(polygon.buffer(1e-7).covers(self.geometry('coverage')))
        ids=json.loads((ROOT/'garmin/map-identities.json').read_text())
        self.assertEqual(ids['sierra-nevada']['familyId'],4835)
        self.assertEqual(len({i['familyId'] for i in ids.values()}),len(ids))

    def test_readme_links_match_integration_catalog(self):
        catalog=json.loads((ROOT/'distribution/app-bundles-v1/catalog.json').read_text())
        readme=(ROOT/'README.md').read_text()
        for item in catalog['regions']['sierra-nevada'].values():
            self.assertIn(item['url'],readme)
            self.assertIn(item['instructionsURL'],readme)
