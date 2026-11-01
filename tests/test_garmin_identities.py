import copy,importlib.util,json,sys,unittest,subprocess,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'garmin'))
from identities import validate_registry,validate_config,write_tile_args
class GarminIdentityTests(unittest.TestCase):
 def test_current_products_and_builders_have_disjoint_identities(self):
  registry=validate_registry()
  for name,path in [('ireland','garmin/config.json'),('england-wales','regions/england-wales/garmin/config.json')]:validate_config(name,json.loads((ROOT/path).read_text()))
  # Personal track input/report files stay private and are absent in public checkouts.
  report=ROOT/'garmin/my-tracks/build-report.json'
  if report.exists():
   tracks=json.loads(report.read_text())['command'];expected=registry['my-tracks']
   self.assertIn('--family-id='+str(expected['familyId']),tracks);self.assertIn('--mapname='+str(expected['tileStartId']),tracks)
  typ=(ROOT/'regions/england-wales/garmin/style/OBM4833.txt').read_text();self.assertIn('FID=4833\n',typ)
 def test_previous_england_wales_identity_is_rejected(self):
  registry=copy.deepcopy(validate_registry());registry['england-wales'].update(familyId=4832,tileStartId=48320001)
  with self.assertRaisesRegex(ValueError,'collision'):validate_registry(registry)
 def test_tile_collision_is_rejected_even_with_distinct_families(self):
  registry=copy.deepcopy(validate_registry());registry['england-wales']['tileStartId']=48320001
  with self.assertRaisesRegex(ValueError,'tile collision'):validate_registry(registry)
 def test_tiny_island_survives_low_zoom_in_compiled_map(self):
  from build import java_path
  java=java_path();javac=str(Path(java).with_name('javac'));jar=ROOT/'garmin/tools/mkgmap-r4924/mkgmap.jar'
  if not jar.exists() or not Path(javac).exists():self.skipTest('Garmin Java toolchain unavailable')
  with tempfile.TemporaryDirectory() as directory:
   work=Path(directory);style=work/'style';style.mkdir()
   for name in ['version','options','lines','points','relations']:
    (style/name).write_text({'version':'0\n','options':'levels = 0:24,1:22,2:20,3:18,4:16\n'}.get(name,''))
   (style/'polygons').write_text((ROOT/'regions/england-wales/garmin/style/polygons').read_text())
   osm=work/'island.osm';osm.write_text('<osm version="0.6"><node id="1" lat="52" lon="-4"/><node id="2" lat="52" lon="-3.99"/><node id="3" lat="52.01" lon="-3.99"/><node id="4" lat="52.01" lon="-4"/><way id="1"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/><tag k="natural" v="land"/></way></osm>')
   subprocess.run([javac,'-cp',str(jar),'-d',str(work),str(ROOT/'garmin/ProbeLand.java')],check=True,capture_output=True)
   def compile_and_probe(name):
    dest=work/name;dest.mkdir()
    result=subprocess.run([java,'-jar',str(jar),'--output-dir='+str(dest),'--style-file='+str(style),'--mapname=48330001','--levels=0:24,1:22,2:20,3:18,4:16',str(osm)],capture_output=True,text=True)
    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    return subprocess.run([java,'-Djava.awt.headless=true','-cp',str(work)+':'+str(jar),'ProbeLand',str(dest/'48330001.img'),'-3.995','52.005'],capture_output=True,text=True)
   result=compile_and_probe('fixed');self.assertEqual(result.returncode,0,result.stderr)
   (style/'polygons').write_text((style/'polygons').read_text().replace(' { set mkgmap:skipSizeFilter=true }',''))
   result=compile_and_probe('old');self.assertNotEqual(result.returncode,0,'Fixture must reproduce old low-zoom land loss')

 def test_cached_old_split_names_do_not_leak_into_compiled_map_ids(self):
  with tempfile.TemporaryDirectory() as directory:
   args=Path(directory)/'tiles.args';sources=[Path('/tmp/48320001.osm.pbf'),Path('/tmp/48320002.osm.pbf')]
   ids=write_tile_args(sources,args,'england-wales','England & Wales')
   self.assertEqual(ids,{'48330001','48330002'})
   text=args.read_text();self.assertIn('mapname: 48330001\n',text);self.assertIn('input-file: /tmp/48320001.osm.pbf\n',text);self.assertNotIn('mapname: 48320001',text)
