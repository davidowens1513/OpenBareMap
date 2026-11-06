import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from publish_preview_ui import stage,CACHE_POLICY
class PreviewPublicationTests(unittest.TestCase):
 def test_only_small_ui_files_are_staged_for_every_public_prefix(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=stage(Path(tmp)/'ui');files=[p for p in out.rglob('*') if p.is_file()]
   self.assertEqual({p.name for p in files},{'index.html','preview.js','preview.css'})
   self.assertEqual(len([p for p in files if p.name=='index.html']),8)
   legacy=out/'OpenBareMap/preview-v2/england-wales/index.html';catalog=json.loads((ROOT/'config/preview-regions.json').read_text());latest=next(e['url'] for e in catalog if e['id']=='england-wales')
   self.assertIn('http-equiv="refresh"',legacy.read_text());self.assertIn(latest,legacy.read_text())
   self.assertIn('must-revalidate',CACHE_POLICY)
