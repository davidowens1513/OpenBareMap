#!/usr/bin/env python3
"""Retain close-up map content; remove only provably hidden overview features."""
import argparse, collections, gzip, hashlib, json, sqlite3, struct
from pathlib import Path
from audit import fields, varint
from build_cartography_2 import vint, layers, encode
ROOT = Path(__file__).resolve().parents[1]
REVISION = '2.0.0-storage-r1'
MAJOR = {'motorway','trunk','primary','secondary','motorway_link','trunk_link','primary_link','secondary_link'}

def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def field(n,w,v):
    return vint(n*8+w)+(vint(v) if w==0 else vint(len(v))+v if w==2 else v)

def packed(data):
    result=[];pos=0
    while pos<len(data):
        value,pos=varint(data,pos);result.append(value)
    return result

def value(raw):
    for n,w,v in fields(raw):
        if n==1:return v.decode('utf-8')
        if n in (4,5):return v
        if n==6:return (v>>1)^-(v&1)
        if n==7:return bool(v)
        if n==2:return struct.unpack('<f',v)[0]
        if n==3:return struct.unpack('<d',v)[0]
    return None

def visible(layer,zoom,properties):
    if layer=='transportation':
        return zoom>=11 or zoom>=7 and properties.get('class') in MAJOR
    if layer=='boundary':
        level=str(properties.get('admin_level',''))
        return level=='2' or zoom>=6 and level in ('5','6') or zoom>=10
    if layer=='contour':
        elevation=properties.get('elevation')
        return zoom>=11 or elevation is None or float(elevation)%100==0
    return True

def eligible(layer,zoom):
    return layer in ('transportation','contour') and zoom<11 or layer=='boundary' and zoom<10

def canonical(feature,keys,values):
    pieces=[]
    for n,w,v in fields(feature):
        if n==2 and w==2:
            tags=packed(v)
            for k,val in zip(tags[::2],tags[1::2]):
                pieces.append(field(1,2,keys[k]));pieces.append(field(2,2,values[val]))
        else:pieces.append(field(n,w,v))
    return b''.join(pieces)

def filter_layer(raw,zoom):
    fs=list(fields(raw));name=next(v.decode() for n,w,v in fs if n==1)
    if not eligible(name,zoom):return raw,0
    keys=[v for n,w,v in fs if n==3 and w==2];values=[v for n,w,v in fs if n==4 and w==2]
    decoded=[value(v) for v in values];kept=[];removed=0;usedkeys=set();usedvalues=set()
    for n,w,feature in fs:
        if n!=2 or w!=2:continue
        tags=next((packed(v) for n,w,v in fields(feature) if n==2 and w==2),[])
        properties={keys[k].decode():decoded[v] for k,v in zip(tags[::2],tags[1::2])}
        if not visible(name,zoom,properties):removed+=1;continue
        kept.append(feature);usedkeys.update(tags[::2]);usedvalues.update(tags[1::2])
    if not removed:return raw,0
    keyids=sorted(usedkeys);valids=sorted(usedvalues);km={v:i for i,v in enumerate(keyids)};vm={v:i for i,v in enumerate(valids)}
    newkeys=[keys[i] for i in keyids];newvalues=[values[i] for i in valids]
    rewritten=[]
    before=hashlib.sha256();after=hashlib.sha256()
    for feature in kept:
        parts=[]
        for n,w,v in fields(feature):
            if n==2 and w==2:
                tags=packed(v);mapped=[]
                for k,val in zip(tags[::2],tags[1::2]):mapped.extend((km[k],vm[val]))
                v=b''.join(vint(i) for i in mapped)
            parts.append(field(n,w,v))
        result=b''.join(parts);rewritten.append(field(2,2,result))
        before.update(canonical(feature,keys,values));after.update(canonical(result,newkeys,newvalues))
    if before.digest()!=after.digest():raise ValueError('Retained feature geometry or attributes changed')
    other=[field(n,w,v) for n,w,v in fs if n not in (2,3,4)]
    return b''.join(other+rewritten+[field(3,2,k) for k in newkeys]+[field(4,2,v) for v in newvalues]),removed

def validate_style(style):
    # Stop rather than silently apply these visibility rules to changed cartography.
    expected=json.loads((ROOT/'config/storage-2.0.json').read_text())['styleSHA256']
    if sha(style)!=expected:raise ValueError('Style changed; re-audit visibility rules')

def optimize(source,destination):
    if destination.exists():raise FileExistsError(destination)
    src=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True);dst=sqlite3.connect(destination)
    dst.execute('CREATE TABLE metadata(name TEXT,value TEXT)')
    dst.execute('CREATE TABLE tiles(zoom_level INTEGER,tile_column INTEGER,tile_row INTEGER,tile_data BLOB)')
    dst.execute('CREATE UNIQUE INDEX tile_index ON tiles(zoom_level,tile_column,tile_row)')
    metadata=dict(src.execute('SELECT name,value FROM metadata'));metadata['openbaremap_storage_revision']=REVISION
    dst.executemany('INSERT INTO metadata VALUES(?,?)',sorted(metadata.items()))
    removed=collections.Counter();changed=0;unchanged=0;tiles=0
    for z,x,y,data in src.execute('SELECT zoom_level,tile_column,tile_row,tile_data FROM tiles ORDER BY zoom_level,tile_column,tile_row'):
        if z<11:
            parts=[];count=0
            for name,raw in layers(data):
                filtered,n=filter_layer(raw,z);removed[name]+=n;count+=n;parts.append((name,filtered))
            if count:data=encode(parts);changed+=1
            else:unchanged+=1
        else:unchanged+=1
        dst.execute('INSERT INTO tiles VALUES(?,?,?,?)',(z,x,y,data));tiles+=1
    dst.commit()
    if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLite integrity')
    # All tile coordinates remain present, including empty tiles and close-up payloads.
    dst.close();src.close()
    return {'source':str(source.relative_to(ROOT)),'path':str(destination.relative_to(ROOT)),'beforeBytes':source.stat().st_size,'afterBytes':destination.stat().st_size,'sha256':sha(destination),'tiles':tiles,'changedOverviewTiles':changed,'unchangedTilePayloads':unchanged,'removedHiddenFeatureInstances':dict(removed),'allRetainedGeometryAndAttributesVerified':True,'allZoom11Through14TilePayloadsUnchanged':True}

def main():
    config=json.loads((ROOT/'config/storage-2.0.json').read_text());validate_style(ROOT/'style/openbaremap.json')
    destination=ROOT/'build/storage-2.0';destination.mkdir(exist_ok=True)
    results={}
    for name,item in config['inputs'].items():
        source=ROOT/item['path']
        if sha(source)!=item['sha256']:raise ValueError('Source checksum: '+name)
        results[name]=optimize(source,destination/(name+'.mbtiles'))
        print(json.dumps(results[name]),flush=True)
    report={'storageRevision':REVISION,'mapVersion':'2.0.0','styleSHA256':config['styleSHA256'],'geometryChanged':False,'outputs':results}
    (destination/'report.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
