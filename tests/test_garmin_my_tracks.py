import importlib.util,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('my_tracks',ROOT/'garmin/my-tracks/build.py');tracks=importlib.util.module_from_spec(spec);spec.loader.exec_module(tracks)
class PersonalTrackTests(unittest.TestCase):
 def test_foreign_section_excludes_entire_track(self):
  self.assertTrue(tracks.in_ireland([[[-9,52],[-8,53]]]))
  self.assertFalse(tracks.in_ireland([[[-9,52],[-8,53]],[[2,48],[3,48]]]))
  self.assertFalse(tracks.in_ireland([]))
 def test_segment_gap_is_not_joined_and_only_first_point_is_start(self):
  with tempfile.TemporaryDirectory() as tmp:
   gpx=Path(tmp)/'test.gpx';gpx.write_text('<gpx xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg><trkpt lat="52" lon="-9"/><trkpt lat="52.1" lon="-9"/></trkseg><trkseg><trkpt lat="53" lon="-8"/><trkpt lat="53.1" lon="-8"/></trkseg></trk></gpx>')
   segments=tracks.read_segments(gpx);out=Path(tmp)/'out.osm';tracks.osm({'tracks':[{'id':'42','name':'A & B','segments':segments}]},out)
   root=ET.parse(out).getroot();ways=root.findall('way');self.assertEqual(len(ways),2)
   refs=[{n.attrib['ref'] for n in w.findall('nd')} for w in ways];self.assertFalse(refs[0]&refs[1])
   starts=[n for n in root.findall('node') if any(t.attrib['k']=='obm:track_start' for t in n.findall('tag'))]
   self.assertEqual(len(starts),1);self.assertEqual(starts[0].attrib['lat'],'52.0000000')

   self.assertFalse(root.findall('.//tag[@k="name"]'))
