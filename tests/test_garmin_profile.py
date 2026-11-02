import importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class GarminProfileTests(unittest.TestCase):
    def test_display_only_and_contour_progression(self):
        profile=json.loads((ROOT/'garmin/config.json').read_text())
        self.assertFalse(profile['routing'])
        self.assertFalse(any(x.startswith('--route') for x in profile['compilerOptions']))
        rules=(ROOT/'garmin/style/lines').read_text()
        self.assertIn('contour=elevation & obm:interval=100',rules)
        self.assertIn('[0x10008 resolution 20-21 continue]',rules)
        self.assertIn('[0x22 resolution 22]',rules)
        self.assertNotIn('obm:interval=50',rules)
        self.assertEqual(profile['contourIntervalMetres'],20)
        self.assertNotIn('boundary=administrative [0x1d',rules)
        self.assertIn('[0x20 resolution 23]',rules)
        self.assertIn('<finalize>',(ROOT/'garmin/style/points').read_text())
    def test_typ_generation_is_deterministic_and_all_polygons_have_draw_order(self):
        spec=importlib.util.spec_from_file_location('garmin_typ',ROOT/'garmin/generate_typ.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            module.ROOT=Path(tmp);(module.ROOT/'style').mkdir();module.main();first=(module.ROOT/'style/OBM4831.txt').read_bytes();module.main()
            self.assertEqual(first,(module.ROOT/'style/OBM4831.txt').read_bytes())
            text=first.decode()
            for code,name,color,order,pattern in module.polygons:self.assertIn(f'Type=0x{code:x},{order}',text)
            self.assertIn('String=Summit',text);self.assertIn('String=Parking',text)
            self.assertIn('CodePage=1252',text)

    def test_all_editions_share_the_hiking_profile(self):
        import re
        roots=[ROOT/'garmin']+[ROOT/'regions'/r/'garmin' for r in ['england-wales','scotland','sierra-nevada']]
        for base in roots:
            config=json.loads((base/'config.json').read_text())
            self.assertEqual(config['nativeLevels'],[24,23,22,20,18,16])
            self.assertEqual(config['hikingLineResolution'],24)
            self.assertEqual(config['hikingLineWidthPixels'],4)
            rules=(base/'style/lines').read_text()
            for code in ['0a','16','10001','1000b']:
                self.assertIn('[0x'+code+' resolution 24]',rules)
            self.assertNotIn('[0x1000b resolution 24 continue]',rules)
            text=(base/'style'/('OBM'+str(config['familyId'])+'.txt')).read_text()
            for code in ['a','16','10001','1000b']:
                block=re.search(r'\[_line\]\nType=0x'+code+r'\n(.*?)\[end\]',text,re.S)[1]
                self.assertIn('Xpm="32 4 2 1"',block)
                self.assertIn('c none',block)
                self.assertNotIn('#fffdf5',block)
            self.assertIn('a c #269e3f',text)
