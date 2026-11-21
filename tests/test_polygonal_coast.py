import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from polygonal_coast import polygonal_coast


class PolygonalCoastTests(unittest.TestCase):
    def test_clipped_collection_preserves_polygon_holes_and_drops_lines(self):
        polygon = {'type': 'Polygon', 'coordinates': [
            [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]],
            [[1, 1], [1, 2], [2, 2], [2, 1], [1, 1]],
        ]}
        line = {'type': 'LineString', 'coordinates': [[0, 0], [0, 4]]}
        features = [{'type': 'Feature', 'properties': {'id': 1},
                     'geometry': {'type': 'GeometryCollection', 'geometries': [polygon, line]}},
                    {'type': 'Feature', 'properties': {}, 'geometry': line}]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'land.geojson'
            path.write_text(json.dumps({'type': 'FeatureCollection', 'features': features}))
            result = polygonal_coast(path)
            data = json.loads(path.read_text())
            self.assertEqual(len(data['features']), 1)
            self.assertEqual(data['features'][0]['geometry']['coordinates'], [polygon['coordinates']])
            self.assertEqual(data['features'][0]['properties'], {'id': 1})
            from build_region_geometry import features
            self.assertEqual(list(features(path)), data['features'])
            self.assertEqual(result['removedZeroAreaFeatures'], 1)
            self.assertEqual(result['extractedPolygonCollections'], 1)
            self.assertTrue((Path(temp) / 'land-unfiltered.geojson').exists())

    def test_pure_polygon_crop_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'land.geojson'
            original = '{"type":"FeatureCollection", "features":[{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,0]]]}}]}'
            path.write_text(original)
            result = polygonal_coast(path)
            self.assertEqual(path.read_text(), original)
            self.assertEqual(result['sourceSHA256'], result['outputSHA256'])

    def test_invalid_clipped_ring_can_be_repaired(self):
        from shapely.geometry import shape

        ring = [[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]]
        source = {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'properties': {},
                  'geometry': {'type': 'Polygon', 'coordinates': [ring]}}]}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'land.geojson'
            path.write_text(json.dumps(source))
            result = polygonal_coast(path, repair_invalid=True)
            repaired = shape(json.loads(path.read_text())['features'][0]['geometry'])
            self.assertTrue(repaired.is_valid)
            self.assertEqual(repaired.area, 2)
            self.assertEqual(result['repairedInvalidFeatures'], 1)
