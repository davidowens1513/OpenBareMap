import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from regions import profile,region_style,expected_basemap_layers,REGIONS
class FaroeTests(unittest.TestCase):
 def test_full_archipelago_and_distinct_identity(self):
  p=profile('faroe-islands');self.assertEqual(len(p['islandValidationAnchors']),18);self.assertTrue({'Mykines','Fugloy','Suðuroy','Lítla Dímun','Stóra Dímun'}<=p['islandValidationAnchors'].keys())
  w,s,e,n=p['bounds']
  for xy in p['islandValidationAnchors'].values():self.assertTrue(w<xy[0]<e and s<xy[1]<n)
  self.assertEqual(p['garminFamilyId'],4838);self.assertEqual(p['contourIntervalMetres'],20);self.assertEqual(p['gridCRS'],'EPSG:25829')
  self.assertEqual(len({profile(r).get('garminFamilyId',4831) for r in REGIONS}),len(REGIONS))
 def test_shared_paints_are_preserved(self):
  paints={l['id']:l.get('paint') for l in json.loads((ROOT/'style/openbaremap.json').read_text())['layers']}
  for layer in region_style('faroe-islands')['layers']:
   if layer['id'] in paints:self.assertEqual(layer.get('paint'),paints[layer['id']],layer['id'])
 def test_station_exemption_is_limited_to_verified_absence(self):
  self.assertNotIn('station',expected_basemap_layers('faroe-islands'));self.assertIn('station',expected_basemap_layers('dolomites'));self.assertIn('station',expected_basemap_layers('ireland'))
  record=json.loads((ROOT/'regions/faroe-islands/source-feature-review.json').read_text());self.assertEqual(sum(record['stationFeaturesInLockedSource'].values()),0)
 def test_regional_terrain_notice_is_available_for_single_and_combined_previews(self):
  from regions import terrain_html,terrain_file
  one=terrain_html(['faroe-islands']);combined=terrain_html(['ireland','faroe-islands'])
  self.assertIn('produced using Copernicus WorldDEM-30',one);self.assertIn('do not incur any liability',one);self.assertIn('produced using Copernicus WorldDEM-30',combined)
  self.assertEqual(terrain_file('ireland','terrain-attribution.html'),ROOT/'viewer/terrain-attribution.html')
  p=profile('faroe-islands');self.assertEqual(p['terrainProvider'],'copernicus-glo30')
 def test_terrain_review_matches_selected_source_lock(self):
  import hashlib
  r=json.loads((ROOT/'regions/faroe-islands/terrain-source-review.json').read_text());self.assertEqual(r['terrainLockSHA256'],hashlib.sha256((ROOT/'regions/faroe-islands/terrain-sources.lock.json').read_bytes()).hexdigest());self.assertEqual(len(r['islands']),18);self.assertTrue(850<=r['summit']['centreElevationMetres']<=900)
