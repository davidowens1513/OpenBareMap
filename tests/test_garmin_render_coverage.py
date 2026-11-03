import sys,unittest,json
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'scripts'),str(Path(__file__).resolve().parents[1]/'work/python')]
from shapely.geometry import box,Polygon,Point,shape,mapping
from shapely.ops import unary_union
from garmin_render_coverage import CoverageClipper,load
class RegionalRenderCoverageTests(unittest.TestCase):
 def test_inside_polygon_keeps_original_coordinates(self):
  g={'type':'Polygon','coordinates':[[[1,1],[2,1],[2,2],[1,2],[1,1]]]};c=CoverageClipper(box(0,0,3,3));self.assertEqual(list(c.polygons(g,'land')),[g['coordinates']])
 def test_overlapping_background_is_clipped_and_outside_excluded(self):
  mask=box(0,0,2,2);c=CoverageClipper(mask);pieces=list(c.polygons(mapping(box(-1,-1,3,3)),'sea'));result=unary_union([Polygon(p[0],p[1:]) for p in pieces]);self.assertTrue(result.equals(mask));self.assertEqual(list(c.polygons(mapping(box(4,4,5,5)),'land')),[])
 def test_holes_and_separate_islands_remain_transparent(self):
  mask=Polygon([(0,0),(5,0),(5,5),(0,5)],holes=[[(1,1),(2,1),(2,2),(1,2)]]).union(box(7,7,8,8));c=CoverageClipper(mask);result=unary_union([Polygon(p[0],p[1:]) for p in c.polygons(mapping(box(-1,-1,9,9)),'sea')]);self.assertTrue(result.equals(mask));self.assertFalse(result.covers(Point(1.5,1.5)));self.assertTrue(result.covers(Point(7.5,7.5)))
 def test_native_england_wales_padding_must_not_paint_dublin(self):
  mask,record=load('england-wales');self.assertFalse(mask.covers(Point(-6.2603,53.3493)));c=CoverageClipper(mask);g=box(-6.7,49.8,2.1,55.9);result=unary_union([Polygon(p[0],p[1:]) for p in c.polygons(mapping(g),'sea')]);self.assertFalse(result.covers(Point(-6.2603,53.3493)));self.assertTrue(result.covers(Point(-4.48,54.15)))
 def test_all_recorded_destination_anchors_retained(self):
  for r in ['ireland','england-wales','scotland','sierra-nevada']:
   mask,record=load(r)
   for n,xy in record['knownDestinationsCovered'].items():self.assertTrue(mask.covers(Point(*xy)),(r,n))
 def test_irish_background_excludes_kintyre(self):
  mask,_=load('ireland');self.assertFalse(mask.covers(Point(-5.606,55.426)))
 def test_scottish_background_excludes_belfast(self):
  mask,_=load('scotland');self.assertFalse(mask.covers(Point(-5.93,54.60)))
 def test_sierra_background_matches_exact_park_buffer(self):
  mask,_=load('sierra-nevada');root=Path(__file__).resolve().parents[1];expected=shape(json.loads((root/'regions/sierra-nevada/coverage.geojson').read_text())['features'][0]['geometry']);self.assertTrue(mask.equals(expected))
if __name__=='__main__':unittest.main()
