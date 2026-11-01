from pathlib import Path
import hashlib
import json
import sys
import shutil
import subprocess
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from regions import ROOT,profile,region_path,region_style,active_map,process_script

class RegionalEditionTests(unittest.TestCase):
    def test_ireland_paths_and_cartography_remain_default(self):
        self.assertEqual(region_path('ireland','active-map.json'),ROOT/'active-map.json')
        self.assertEqual(region_style(),json.loads((ROOT/'style/openbaremap.json').read_text()))
        self.assertEqual(active_map(),json.loads((ROOT/'active-map.json').read_text()))
        baseline=json.loads((ROOT/'regions/ireland/preservation-baseline.json').read_text())
        for relative,expected in baseline['files'].items():
            with (ROOT/relative).open('rb') as stream:
                self.assertEqual(hashlib.file_digest(stream,'sha256').hexdigest(),expected,relative)

    def test_england_wales_style_has_only_resolvable_regional_sources(self):
        style=region_style('england-wales');ids=[l['id'] for l in style['layers']]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertNotIn('townlands',style['sources']);self.assertNotIn('irish-grid',style['sources'])
        self.assertIn('british-grid',style['sources'])
        for layer in style['layers']:
            if 'source' in layer:self.assertIn(layer['source'],style['sources'])
        self.assertNotIn('name_ga',json.dumps(style))
        self.assertIn('name_cy',json.dumps(style))
        self.assertEqual(style['sources']['coast']['bounds'],profile('england-wales')['bounds'])

    def test_full_extent_and_independent_garmin_identity(self):
        p=profile('england-wales')
        self.assertEqual(p['sourceSlugs'],['england','wales'])
        self.assertEqual(p['terrainBounds'],[-7,49,3,56])
        self.assertNotEqual(p['garminFamilyId'],json.loads((ROOT/'garmin/config.json').read_text())['familyId'])
        self.assertEqual(p['contourIntervalMetres'],20)
        self.assertEqual(p['gridCRS'],'EPSG:27700')
        with self.assertRaises(ValueError):region_path('../ireland','active-map.json')

    def test_welsh_processing_preserves_access_fields_and_shared_classification(self):
        lua=shutil.which('lua')
        if not lua:self.skipTest('Lua runtime unavailable')
        cases=(ROOT/'tests/fixtures/process_cases.lua').read_text().replace('name:ga','name:cy').replace('name_ga','name_cy')
        cases += '\nrun("way",{highway="path",designation="public_footpath",horse="no",bicycle="yes",foot="designated",sac_scale="hiking",trail_visibility="good"},false)\nlocal p=find("transportation").attributes;assert(p.designation=="public_footpath" and p.horse=="no" and p.bicycle=="yes" and p.foot=="designated" and p.sac_scale=="hiking" and p.trail_visibility=="good")\n'
        with tempfile.TemporaryDirectory() as directory:
            script=Path(directory)/'process.lua';fixture=Path(directory)/'cases.lua'
            script.write_text(process_script('england-wales'));fixture.write_text(cases)
            result=subprocess.run([lua,str(fixture),str(script)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
