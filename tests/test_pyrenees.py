"""Pyrenees crop, complete edge geometry and shared cartography checks."""
import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'work/python'),str(ROOT/'garmin')]
from regions import profile,region_style
from fetch_region import extract_complete
from shapely.geometry import Point,box
from identities import validate_registry

class PyreneesTests(unittest.TestCase):
    def test_crop_covers_bayonne_both_coasts_and_mountain_anchors(self):
        p=profile('pyrenees');extent=box(*p['bounds'])
        for name,xy in p['destinations'].items():self.assertTrue(extent.covers(Point(*xy[:2])),name)
        self.assertGreater(p['bounds'][3]-p['destinations']['bayonne'][1],.2)
        self.assertEqual(p['contourIntervalMetres'],20)
        self.assertEqual(p['maxzoom'],14)
        self.assertEqual(validate_registry()['pyrenees']['familyId'],4836)

    def test_transport_weights_colours_and_hillshade_match_accepted_style(self):
        shared=json.loads((ROOT/'style/openbaremap.json').read_text())
        regional=region_style('pyrenees');old={l['id']:l for l in shared['layers']}
        self.assertIn('utm-grid',regional['sources']);self.assertNotIn('townlands',regional['sources'])
        for layer in regional['layers']:
            if layer['id'] in old:self.assertEqual(layer.get('paint'),old[layer['id']].get('paint'),layer['id'])
            if 'source' in layer:self.assertIn(layer['source'],regional['sources'])

    def test_extract_keeps_complete_ways_and_nested_relations_at_edge(self):
        import osmium
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source.osm';target=Path(temp)/'extract.osm.pbf'
            source.write_text('''<osm version="0.6">
<node id="1" lat="42" lon="0" version="1"/>
<node id="2" lat="44" lon="0" version="1"/>
<node id="3" lat="45" lon="0" version="1"/>
<node id="4" lat="46" lon="0" version="1"/>
<node id="5" lat="50" lon="0" version="1"/>
<way id="10" version="1"><nd ref="1"/><nd ref="2"/><tag k="highway" v="path"/></way>
<way id="11" version="1"><nd ref="3"/><nd ref="4"/><tag k="highway" v="path"/></way>
<relation id="20" version="1"><member type="way" ref="10" role=""/><member type="way" ref="11" role=""/><tag k="type" v="route"/></relation>
<relation id="21" version="1"><member type="relation" ref="20" role=""/><tag k="type" v="superroute"/></relation>
</osm>''')
            extract_complete(source,target,[-1,41,1,43])
            objects={}
            for obj in osmium.FileProcessor(str(target)).with_locations():
                objects[(obj.type_str(),obj.id)]=dict(obj.tags)
                if obj.is_way():self.assertTrue(all(n.location.valid() for n in obj.nodes))
            self.assertEqual(set(objects),{('n',i) for i in (1,2,3,4)}|{('w',10),('w',11),('r',20),('r',21)})
            self.assertEqual(objects[('w',11)]['highway'],'path')
            extract_complete(source,target,[-1,41,1,43])
            with self.assertRaisesRegex(ValueError,'Changed extraction'):extract_complete(source,target,[-1,41,1,44])

    def test_native_split_rejects_first_extract_header_bounds(self):
        from garmin_split_coverage import validate_split
        import math
        p=profile('pyrenees');unit=(1<<24)/360
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'areas.list'
            def area(w,s,e,n):
                path.write_text(f"48360001: {math.floor(s*unit)},{math.floor(w*unit)} to {math.ceil(n*unit)},{math.ceil(e*unit)}\n")
            area(-.32753,42.53333,3.4,43.9)
            with self.assertRaisesRegex(ValueError,'excludes bayonne'):validate_split(path,p)
            area(*p['bounds'])
            result=validate_split(path,p)
            self.assertIn('bayonne',result['anchorsCovered']);self.assertIn('girona',result['anchorsCovered'])
