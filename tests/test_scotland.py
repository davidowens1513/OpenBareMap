"""Coverage and language regressions for the independent Scotland edition."""
from pathlib import Path
import json,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from regions import ROOT,profile,region_style,process_script

class ScotlandTests(unittest.TestCase):
    def test_gaelic_labels_and_no_ireland_or_welsh_sources(self):
        style=region_style('scotland');text=json.dumps(style)
        self.assertIn('name_gd',text)
        self.assertNotIn('name_ga',text);self.assertNotIn('name_cy',text)
        self.assertNotIn('townlands',style['sources'])
        self.assertIn('british-grid',style['sources'])
        script=process_script('scotland')
        self.assertIn('name:gd',script);self.assertIn('name_gd',script)
        self.assertNotIn('name:cy',script)

    def test_entire_source_polygon_and_destinations_fit_selected_extent(self):
        from region_coverage import polygon_union
        p=profile('scotland');w,s,e,n=p['bounds'];tw,ts,te,tn=p['terrainBounds']
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'scotland.poly';polygon_union('scotland',target)
            coverage=json.loads(target.with_suffix('.json').read_text())
        x0,y0,x1,y1=coverage['bounds']
        self.assertLessEqual(w,x0);self.assertLessEqual(s,y0)
        self.assertGreaterEqual(e,x1);self.assertGreaterEqual(n,y1)
        self.assertLessEqual(tw,w);self.assertLessEqual(ts,s)
        self.assertGreaterEqual(te,e);self.assertGreaterEqual(tn,n)
        for location in ('rockall','st-kilda','shetland','unst','orkney','lewis'):
            self.assertIn(location,coverage['knownDestinationsCovered'])

    def test_grid_extends_north_of_shetland(self):
        from build_region_geometry import grid,features
        with tempfile.TemporaryDirectory() as directory:
            dest=Path(directory);counts=grid('scotland',dest)
            parallels=[f for f in features(dest/'grid_10km.geojson') if f['properties']['axis']=='N']
        north=max(parallels,key=lambda f:f['properties']['metres'])
        self.assertEqual(north['properties']['metres'],1300000)
        # Extended western grid bows south; test its northern edge at Shetland's longitude.
        above_unst=min(north['geometry']['coordinates'],key=lambda c:abs(c[0]+.84))
        self.assertGreater(above_unst[1],61)
        self.assertGreater(counts['grid_1km'],2300)
        self.assertLessEqual(profile('scotland')['gridExtent'][0],-300000)

    def test_reserved_identity_does_not_overlap_existing_editions(self):
        sys.path.insert(0,str(ROOT/'garmin'))
        from identities import validate_registry
        validate_registry()
        identity=json.loads((ROOT/'garmin/map-identities.json').read_text())['scotland']
        self.assertEqual(identity['familyId'],profile('scotland')['garminFamilyId'])
        self.assertEqual(identity['tileStartId'],profile('scotland')['garminTileStartId'])

if __name__=='__main__':unittest.main()
