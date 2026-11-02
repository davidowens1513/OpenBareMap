import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_isle_of_man_extension import merge_layer
from verify_isle_of_man import signatures
from optimize_storage import field
from build_cartography_2 import vint

def layer(keys,values,features):
 raw=field(15,0,2)+field(1,2,b'road')+field(5,0,4096)
 for identifier,tags in features:
  raw+=field(2,2,field(1,0,identifier)+field(2,2,b''.join(vint(x) for x in tags))+field(3,0,2)+field(4,2,b'\x09\x00\x00\x0a\x02\x02'))
 return raw+b''.join(field(3,2,k) for k in keys)+b''.join(field(4,2,field(1,2,v)) for v in values)
class IslandMergingTests(unittest.TestCase):
 def test_property_indexes_remap_without_changing_existing_features(self):
  old=layer([b'name',b'class'],[b'old name',b'path'],[(1,[0,0,1,1])])
  island=layer([b'class',b'name'],[b'track',b'new name'],[(2,[0,0,1,1])])
  merged,count=merge_layer(old,island)
  self.assertEqual(count,1)
  self.assertEqual(signatures(merged),signatures(old)+signatures(island))
 def test_shared_feature_is_not_added_again_with_different_tables(self):
  old=layer([b'name',b'class'],[b'old name',b'path'],[(1,[0,0,1,1])])
  same=layer([b'class',b'name'],[b'path',b'old name'],[(1,[0,0,1,1])])
  merged,count=merge_layer(old,same)
  self.assertEqual(count,0);self.assertEqual(signatures(merged),signatures(old))
 def test_rejects_mismatched_tile_extent(self):
  a=layer([],[],[]);b=a.replace(field(5,0,4096),field(5,0,8192))
  with self.assertRaises(AssertionError):merge_layer(a,b)
if __name__=='__main__':unittest.main()
