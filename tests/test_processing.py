from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]

class ProcessingTests(unittest.TestCase):
    def test_osm_feature_classification_and_elevation_rules(self):
        lua=shutil.which('lua')
        if lua is None:self.skipTest('Lua is required to run the processing fixtures')
        result=subprocess.run([lua,str(ROOT/'tests/fixtures/process_cases.lua'),str(ROOT/'config/process.lua')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
