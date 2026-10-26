import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

def evaluate(expression, tags):
    if not isinstance(expression,list):return expression
    op,*args=expression
    if op=='literal':return args[0]
    if op=='get':return tags.get(args[0])
    if op=='coalesce':return next((v for a in args if (v:=evaluate(a,tags)) is not None),None)
    if op=='!':return not evaluate(args[0],tags)
    if op=='all':return all(evaluate(a,tags) for a in args)
    if op=='in':return evaluate(args[0],tags) in evaluate(args[1],tags)
    if op=='==':return evaluate(args[0],tags)==evaluate(args[1],tags)
    if op=='case':
        for i in range(0,len(args)-1,2):
            if evaluate(args[i],tags):return evaluate(args[i+1],tags)
        return evaluate(args[-1],tags)
    if op=='to-number':
        for a in args:
            try:
                v=evaluate(a,tags)
                if v is not None:return float(v)
            except (TypeError,ValueError):pass
        raise ValueError('No numeric fallback')
    raise ValueError(op)

class TransportStyleTests(unittest.TestCase):
    def setUp(self):
        self.layers=json.loads((ROOT/'style/openbaremap.json').read_text())['layers']

    def road_pass(self, tags):
        return [i for i,l in enumerate(self.layers) if l['id'].split('--')[0]=='roads-major' and evaluate(l['filter'],tags)]

    def test_crossings_and_links_use_exactly_one_ordered_pass(self):
        surface=self.road_pass({'class':'primary'})
        tunnel=self.road_pass({'class':'primary','tunnel':'yes'})
        bridge=self.road_pass({'class':'primary','bridge':'yes'})
        high=self.road_pass({'class':'primary','bridge':'yes','layer':'2'})
        for passes in [surface,tunnel,bridge,high]:self.assertEqual(len(passes),1)
        self.assertLess(tunnel[0],surface[0]);self.assertLess(surface[0],bridge[0]);self.assertLess(bridge[0],high[0])
        for cl in ['motorway_link','trunk_link','primary_link','secondary_link']:
            self.assertEqual(len(self.road_pass({'class':cl})),1)
        for level in ['-6','-1.5','0','5']:
            self.assertEqual(len(self.road_pass({'class':'primary','layer':level})),1)
        self.assertEqual(self.road_pass({'class':'primary','bridge':'no','tunnel':'no'}),surface)

    def test_paths_never_gain_solid_casings_and_tunnels_have_dashes(self):
        for layer in self.layers:
            if layer['id'].startswith('roads-casing'):
                self.assertFalse(evaluate(layer['filter'],{'class':'path','bridge':'yes'}))
                self.assertFalse(evaluate(layer['filter'],{'class':'track'}))
        tunnel=next(l for l in self.layers if l['id']=='roads-major--tunnel--1')
        self.assertEqual(tunnel['paint']['line-dasharray'],[3,2])
        self.assertLess(tunnel['paint']['line-opacity'],1)

    def test_text_outputs_never_fall_below_six_pixels(self):
        def outputs(value):
            if isinstance(value,(int,float)):return [value]
            if value[0]=='interpolate':return [n for i in range(4,len(value),2) for n in outputs(value[i])]
            if value[0]=='match':return [n for i in range(3,len(value)-1,2) for n in outputs(value[i])]+outputs(value[-1])
            raise ValueError(value)
        for layer in self.layers:
            size=layer.get('layout',{}).get('text-size')
            if size is not None:self.assertGreaterEqual(min(outputs(size)),6,layer['id'])
