#!/usr/bin/env python3
"""Generate transport drawing passes from tracked templates and source layer levels."""
import copy
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def numeric_outputs(value, amount):
    if isinstance(value,(int,float)):return round(value+amount,3)
    if isinstance(value,list) and value[0]=='interpolate':
        result=copy.deepcopy(value)
        for i in range(4,len(result),2):result[i]=numeric_outputs(result[i],amount)
        return result
    raise ValueError('Unsupported width expression')

def generate(templates, levels):
    bridge=['!', ['in',['coalesce',['get','bridge'],'no'],['literal',['','no','false','0']]]]
    tunnel=['all',['!',bridge],['!', ['in',['coalesce',['get','tunnel'],'no'],['literal',['','no','false','0']]]]]
    ground=['all',['!',bridge],['!',tunnel]]
    effective=['to-number',['get','layer'],['case',bridge,1,tunnel,-1,0]]
    output=[]
    for level in sorted(set(levels)|{0}):
        for kind,condition in [('tunnel',tunnel),('ground',ground),('bridge',bridge)]:
            for original in templates:
                layer=copy.deepcopy(original)
                layer['id']=original['id'] if level==0 and kind=='ground' else f"{original['id']}--{kind}-{level}"
                layer['filter']=['all',original['filter'],condition,['==',effective,level]]
                layout=layer.setdefault('layout',{})
                layout['line-sort-key']=effective
                paint=layer['paint']
                if kind=='tunnel':
                    paint['line-opacity']=0.6
                    if 'casing' not in original['id'] and 'line-dasharray' not in paint:paint['line-dasharray']=[3,2]
                    if original['id']=='roads-minor':paint['line-dasharray']=[3,2]
                    if 'casing' in original['id']:continue
                if kind=='bridge' and original['id'] in ['paths','tracks','footways','bridleways','cycleways','steps']:
                    paint['line-width']=numeric_outputs(paint['line-width'],0.5)
                if kind=='tunnel' and original['id']=='roads-minor':paint['line-color']='#756e65'
                if kind=='bridge' and 'casing' in original['id']:
                    paint['line-color']='#615e56'
                    paint['line-width']=numeric_outputs(paint['line-width'],1.3)
                output.append(layer)
    return output

def main():
    config=json.loads((ROOT/'config/transport-style.json').read_text())
    path=ROOT/'style/openbaremap.json';style=json.loads(path.read_text())
    names={l['id'] for l in config['templates']}
    is_transport=lambda l:l['id'].split('--')[0] in names
    insertion=next(i for i,l in enumerate(style['layers']) if is_transport(l))
    before=[l for l in style['layers'][:insertion] if not is_transport(l)]
    after=[l for l in style['layers'][insertion:] if not is_transport(l)]
    style['layers']=before+generate(config['templates'],config['levels'])+after
    path.write_text(json.dumps(style,indent=2)+'\n')
if __name__=='__main__':main()
