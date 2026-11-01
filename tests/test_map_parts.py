import hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from restore_map_parts import restore

class MapPartsTests(unittest.TestCase):
 def make(self,root):
  data=b'Complete map payload across independently downloaded parts.';parts=[]
  for i,block in enumerate([data[:13],data[13:31],data[31:]]):
   path=root/f'part{i}';path.write_bytes(block);parts.append({'path':path.name,'bytes':len(block),'sha256':hashlib.sha256(block).hexdigest()})
  manifest=root/'parts.json';manifest.write_text(json.dumps({'path':'restored/map.mbtiles','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'parts':parts}));return manifest,data
 def test_full_payload_and_safe_existing_destination(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);manifest,data=self.make(root);target=restore(manifest,root)
   self.assertEqual(target.read_bytes(),data);self.assertEqual(restore(manifest,root),target)
   target.write_bytes(b'other map')
   with self.assertRaisesRegex(ValueError,'refusing overwrite'):restore(manifest,root)
 def test_bad_part_is_rejected_before_creating_map(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);manifest,data=self.make(root);(root/'part1').write_bytes(b'wrong')
   with self.assertRaisesRegex(ValueError,'Missing or changed map part'):restore(manifest,root)
   self.assertFalse((root/'restored/map.mbtiles').exists())
 def test_path_escape_is_rejected(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);manifest,data=self.make(root);record=json.loads(manifest.read_text());record['path']='../outside.mbtiles';manifest.write_text(json.dumps(record))
   with self.assertRaisesRegex(ValueError,'escapes repository'):restore(manifest,root)
