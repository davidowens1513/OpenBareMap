import json,sys,tempfile,unittest
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from package_preview_ui import package_ui
from regions import REGIONS,profile,region_style
class Menu(HTMLParser):
 def __init__(self):super().__init__();self.in_region=False;self.options=[];self.nav=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='nav':self.nav=True
  if tag=='select':self.in_region=a.get('id')=='region'
  if tag=='option' and self.in_region:self.options.append(a)
 def handle_endtag(self,tag):
  if tag=='select':self.in_region=False
class PreviewRegionsTests(unittest.TestCase):
 def test_all_editions_have_full_menu_and_correct_current_region(self):
  catalog=json.loads((ROOT/'config/preview-regions.json').read_text())
  self.assertEqual({x['id'] for x in catalog},set(REGIONS))
  with tempfile.TemporaryDirectory() as directory:
   output=package_ui(directory)
   for region in REGIONS:
    parser=Menu();parser.feed((output/region/'index.html').read_text())
    self.assertFalse(parser.nav)
    self.assertEqual([x['value'] for x in parser.options],[x['url'] for x in catalog])
    self.assertEqual([x['value'] for x in parser.options if 'selected' in x],[x['url'] for x in catalog if x['id']==region])
 def test_single_region_export_retains_other_regions(self):
  with tempfile.TemporaryDirectory() as directory:
   out=package_ui(directory,['dolomites']);parser=Menu();parser.feed((out/'dolomites/index.html').read_text());self.assertEqual(len(parser.options),len(REGIONS))
   self.assertFalse((out/'ireland').exists())
 def test_dolomites_bounds_identity_and_shared_cartography(self):
  p=profile('dolomites');self.assertEqual(p['bounds'],[10.65,45.7,13.1,47.0]);self.assertEqual(p['garminFamilyId'],4837)
  self.assertEqual(set(p['sourceSlugs']),{'nord-est','nord-ovest','austria'})
  shared=json.loads((ROOT/'style/openbaremap.json').read_text());paints={x['id']:x.get('paint') for x in shared['layers']}
  for layer in region_style('dolomites')['layers']:
   if layer['id'] in paints:self.assertEqual(layer.get('paint'),paints[layer['id']],layer['id'])
  self.assertEqual(p['contourIntervalMetres'],20)
