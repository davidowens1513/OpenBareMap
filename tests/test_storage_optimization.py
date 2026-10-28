from pathlib import Path
import json, sys, unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from optimize_storage import field,filter_layer,canonical,MAJOR
from audit import fields

def layer(name,classes):
    keys=[b'class',b'name'];values=[];features=[]
    for i,class_ in enumerate(classes):
        values += [field(1,2,class_.encode()),field(1,2,('name-'+class_).encode())]
        feature=field(2,2,bytes([0,i*2,1,i*2+1]))+field(3,0,2)+field(4,2,b'\x09\x02\x02\x0a\x04\x04')
        features.append(field(2,2,feature))
    return field(1,2,name.encode())+b''.join(features)+b''.join(field(3,2,k) for k in keys)+b''.join(field(4,2,v) for v in values)+field(5,0,4096)+field(15,0,2)

def feature_content(raw):
    fs=list(fields(raw));keys=[v for n,w,v in fs if n==3];values=[v for n,w,v in fs if n==4]
    return [canonical(v,keys,values) for n,w,v in fs if n==2]

class StorageOptimizationTests(unittest.TestCase):
    def test_overview_removes_hidden_roads_but_preserves_visible_geometry_and_names(self):
        raw=layer('transportation',['motorway','path','primary'])
        actual,removed=filter_layer(raw,7)
        self.assertEqual(removed,1)
        original=feature_content(raw)
        self.assertEqual(feature_content(actual),[original[0],original[2]])
        self.assertEqual(filter_layer(raw,11),(raw,0))
        self.assertEqual(feature_content(filter_layer(raw,6)[0]),[])

    def test_unrelated_layers_are_byte_identical(self):
        raw=layer('water',['river'])
        self.assertEqual(filter_layer(raw,4),(raw,0))

    def test_road_rules_follow_current_style_visibility(self):
        root=Path(__file__).resolve().parents[1]
        style=json.loads((root/'style/openbaremap.json').read_text())
        def class_sets(expression):
            found=[]
            if isinstance(expression,list):
                if len(expression)==3 and expression[0]=='in' and expression[1]==['get','class'] and isinstance(expression[2],list) and expression[2][0]=='literal':found.append(set(expression[2][1]))
                for child in expression:found.extend(class_sets(child))
            return found
        for item in style['layers']:
            if item.get('source-layer')=='transportation' and item.get('minzoom',0)<11:
                self.assertGreaterEqual(item['minzoom'],7)
                self.assertTrue(any(values<=MAJOR for values in class_sets(item['filter'])),item['id'])
        boundary={item['id']:item for item in style['layers'] if item.get('source-layer')=='boundary'}
        self.assertNotIn('local-boundaries',boundary)
        self.assertEqual(boundary['county-boundaries']['minzoom'],6)
        for item in style['layers']:
            if item.get('source-layer')=='contour' and item.get('minzoom',0)<11:
                self.assertEqual(item['filter'],['==',['%',['get','elevation'],100],0])
