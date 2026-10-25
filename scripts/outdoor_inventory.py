#!/usr/bin/env python3
"""Inventory outdoor features from actual highest-zoom MVT data, not metadata alone."""
from collections import Counter
from contextlib import closing
import gzip
import json
import math
from pathlib import Path
import sqlite3
import struct
import sys
from audit import fields,varint

LAYERS={'mountain','hiking_poi','hiking_route','natural_line'}

def value(data):
    for number,wire,item in fields(data):
        if number==1:return item.decode('utf-8')
        if number==2:return struct.unpack('<f',item)[0]
        if number==3:return struct.unpack('<d',item)[0]
        if number in (4,5):return item
        if number==6:return (item>>1)^-(item&1)
        if number==7:return bool(item)
    return None

def first_point(data,extent,z,x,tms_y):
    command,offset=varint(data,0)
    if command&7!=1:raise ValueError('Expected initial MoveTo')
    dx,offset=varint(data,offset);dy,offset=varint(data,offset)
    px=(dx>>1)^-(dx&1);py=(dy>>1)^-(dy&1)
    gx=(x+px/extent)/(2**z)
    gy=((2**z-1-tms_y)+py/extent)/(2**z)
    return [round(gx*360-180,6),round(math.degrees(math.atan(math.sinh(math.pi*(1-2*gy)))),6)]

def inventory(path):
    features={name:{} for name in LAYERS}
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)) as db:
        zoom=db.execute('SELECT MAX(zoom_level) FROM tiles').fetchone()[0]
        for x,y,payload in db.execute('SELECT tile_column,tile_row,tile_data FROM tiles WHERE zoom_level=? ORDER BY tile_column,tile_row',(zoom,)):
            if payload[:2]==b'\x1f\x8b':payload=gzip.decompress(payload)
            for number,wire,layer in fields(payload):
                if number!=3 or wire!=2:continue
                entries=list(fields(layer));name=next(item.decode() for n,w,item in entries if n==1)
                if name not in LAYERS:continue
                keys=[item.decode() for n,w,item in entries if n==3]
                values=[value(item) for n,w,item in entries if n==4]
                extent=next((item for n,w,item in entries if n==5),4096)
                for n,w,feature in entries:
                    if n!=2:continue
                    entries2=list(fields(feature));identifier=next((item for n,w,item in entries2 if n==1),None)
                    if identifier is None:raise ValueError('Outdoor feature lacks ID: '+name)
                    if identifier in features[name]:continue
                    packed=next((item for n,w,item in entries2 if n==2),b'');indices=[];offset=0
                    while offset<len(packed):
                        item,offset=varint(packed,offset);indices.append(item)
                    attrs={keys[indices[i]]:values[indices[i+1]] for i in range(0,len(indices),2)}
                    geometry=next(item for n,w,item in entries2 if n==4)
                    attrs['first_coordinate']=first_point(geometry,extent,zoom,x,y)
                    attrs['id']=identifier;features[name][identifier]=attrs
    counts={name:dict(sorted(Counter(f['class'] for f in items.values()).items())) for name,items in sorted(features.items())}
    peaks=sorted((f for f in features['mountain'].values() if f['class']=='peak' and 'ele_m' in f),key=lambda f:-f['ele_m'])[:20]
    routes=sorted((f for f in features['hiking_route'].values() if any(word in (f.get('name_en','')+' '+f.get('name','')).lower() for word in ['wicklow','kerry way','dingle way','ulster way'])),key=lambda f:f.get('name_en',f.get('name','')))[:20]
    if not all(features.values()):raise ValueError('Missing outdoor layer features')
    if not {'peak','saddle'}.issubset(counts['mountain']):raise ValueError('Missing peak or saddle features')
    return {'zoom':zoom,'distinct_emitted_feature_ids_by_class':counts,'highest_recorded_summits':peaks,'route_examples':routes,'note':'Counts deduplicate MVT feature IDs at the highest zoom; they are not an independent source completeness audit. first_coordinate is the first decoded geometry coordinate, not a route centre.'}

if __name__=='__main__':print(json.dumps(inventory(sys.argv[1]),indent=2,ensure_ascii=False))
