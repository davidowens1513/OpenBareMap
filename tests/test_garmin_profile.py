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
        self.assertIn('[0x22 resolution 20]',rules)
        self.assertIn('[0x21 resolution 22]',rules)
        self.assertIn('[0x20 resolution 24]',rules)
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
