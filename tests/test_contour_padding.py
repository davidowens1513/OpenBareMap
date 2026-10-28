import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from trim_contour_padding import intersects,decode,encode_paths,trim_layer
from optimize_storage import field
from audit import fields
class ContourPaddingTests(unittest.TestCase):
 def test_crossing_segment(self):
  self.assertTrue(intersects((-9000,2000),(9000,2000),-1024,5120))
  self.assertFalse(intersects((-9000,6000),(9000,6000),-1024,5120))
 def test_split_retains_original_coordinates_and_attributes(self):
  paths=[([(-9000,0),(0,0),(6000,0),(7000,0),(4096,4096)],False)]
  geometry=encode_paths(paths)
  attributes=field(1,0,123)+field(2,2,b'\x00\x00')+field(3,0,2)
  raw=field(1,2,b'contour')+field(2,2,attributes+field(4,2,geometry))+field(5,0,4096)
  result,stats=trim_layer(raw)
  feature=next(v for n,w,v in fields(result) if n==2)
  geom=next(v for n,w,v in fields(feature) if n==4)
  self.assertEqual(decode(geom),[[[(-9000,0),(0,0),(6000,0)],False],[[(7000,0),(4096,4096)],False]])
  self.assertEqual(b''.join(field(n,w,v) for n,w,v in fields(feature) if n!=4),attributes)
  self.assertEqual(stats['removedOutsideSegments'],1)
 def test_inside_unchanged(self):
  raw=field(2,2,field(3,0,2)+field(4,2,encode_paths([([(0,0),(4096,4096)],False)])))
  result,stats=trim_layer(raw)
  self.assertEqual(result,raw);self.assertEqual(stats['removedOutsideSegments'],0)
 def test_wholly_outside_removed(self):
  raw=field(2,2,field(3,0,2)+field(4,2,encode_paths([([(9000,9000),(10000,10000)],False)])))
  result,stats=trim_layer(raw)
  self.assertEqual(result,b'');self.assertEqual(stats['removedWhollyOutsideFeatures'],1)
 def test_closed_unsupported_retained(self):
  raw=field(2,2,field(3,0,2)+field(4,2,encode_paths([([(0,0),(1,1),(2,0)],True)])))
  self.assertEqual(trim_layer(raw)[0],raw)
if __name__=='__main__':unittest.main()
