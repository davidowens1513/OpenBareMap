import hashlib,sys,tempfile,unittest
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from package_preview_ui import package_ui
class Elements(HTMLParser):
 def __init__(self):super().__init__();self.elements=[]
 def handle_starttag(self,tag,attrs):self.elements.append((tag,dict(attrs)))
class PreviewKeyTests(unittest.TestCase):
 def test_each_preview_opens_its_own_full_size_regional_key(self):
  with tempfile.TemporaryDirectory() as directory:
   output=package_ui(Path(directory))
   for region in ['ireland','england-wales','scotland']:
    page=Elements();page.feed((output/region/'index.html').read_text())
    links=[a for tag,a in page.elements if tag=='a' and a.get('href')=='./legend.html']
    self.assertEqual(len(links),2)
    self.assertTrue(all(a.get('target')=='_blank' and a.get('rel')=='noopener' for a in links))
    self.assertFalse(any(tag=='li' for tag,a in page.elements),'Abbreviated key must not remain alongside the regional legend')
    viewer=Elements();viewer.feed((output/region/'legend.html').read_text())
    image=next(a for tag,a in viewer.elements if tag=='img')
    path=(output/region/image['src']).resolve();self.assertTrue(path.is_file())
    source=ROOT/'app-legend/openbaremap-legend@2x.png' if region=='ireland' else ROOT/'regions'/region/'legend/openbaremap-legend@2x.png'
    self.assertEqual(hashlib.sha256(path.read_bytes()).digest(),hashlib.sha256(source.read_bytes()).digest())
    self.assertTrue({'zoom-in','zoom-out','fit-page','actual-size'} <= {a.get('id') for tag,a in viewer.elements if tag=='button'})
    self.assertIn('pinch to zoom',(output/region/'legend.html').read_text())
 def test_packaging_ui_preserves_existing_map_archive(self):
  with tempfile.TemporaryDirectory() as directory:
   output=Path(directory);archive=output/'data/ireland/basemap.pmtiles';archive.parent.mkdir(parents=True);archive.write_bytes(b'unchanged accepted map data')
   package_ui(output)
   self.assertEqual(archive.read_bytes(),b'unchanged accepted map data')
