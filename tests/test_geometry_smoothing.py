import importlib.util,math,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('smoothing',ROOT/'scripts/smooth_geometry.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class GeometrySmoothingTests(unittest.TestCase):
 def test_open_contour_keeps_endpoints_and_bounds_corner_cut(self):
  points=[[-9,52],[-9,52.001],[-8.999,52.001]];result=m.smooth_line(points,4)
  self.assertEqual(result[0],points[0]);self.assertEqual(result[-1],points[-1]);self.assertEqual(len(result),4)
  for p in result[1:-1]:
   d=math.hypot((p[0]-points[1][0])*m.METRES_PER_DEGREE*math.cos(math.radians(52.001)),(p[1]-points[1][1])*m.METRES_PER_DEGREE)
   self.assertLessEqual(d,4.02)
 def test_polygon_remains_closed_and_holes_are_retained(self):
  ring=[[-9,52],[-8.99,52],[-8.99,52.01],[-9,52.01],[-9,52]];hole=[[-8.998,52.002],[-8.998,52.004],[-8.996,52.004],[-8.996,52.002],[-8.998,52.002]]
  result=m.smooth_polygon_geometry({'type':'Polygon','coordinates':[ring,hole]},6)
  self.assertEqual(len(result['coordinates']),2)
  for r in result['coordinates']:self.assertEqual(r[0],r[-1]);self.assertEqual(len(r),9)
 def test_straight_and_short_contours_are_unchanged(self):
  for points in [[[-9,52],[-9,52.001],[-9,52.002]],[[-9,52],[-8,52]]]:self.assertEqual(m.smooth_line(points,4),points)
