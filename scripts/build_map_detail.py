#!/usr/bin/env python3
"""Build the selected 20 m/county-border adaptation from pinned 10 m resources."""
from pathlib import Path
import json,sqlite3
import optimize_storage as opt
from build_cartography_2 import layers,encode
ROOT=Path(__file__).resolve().parents[1]

def keep(layer,zoom,properties):
    if layer=='boundary':return str(properties.get('admin_level','')) in ('2','5','6')
    if layer=='contour':
        elevation=properties.get('elevation')
        return elevation is None or float(elevation)%20==0
    return True

def build(source,destination,config):
    if destination.exists():raise FileExistsError(destination)
    src=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True);dst=sqlite3.connect(destination)
    dst.execute('CREATE TABLE metadata(name TEXT,value TEXT)')
    dst.execute('CREATE TABLE tiles(zoom_level INTEGER,tile_column INTEGER,tile_row INTEGER,tile_data BLOB)')
    dst.execute('CREATE UNIQUE INDEX tile_index ON tiles(zoom_level,tile_column,tile_row)')
    metadata=dict(src.execute('SELECT name,value FROM metadata'));metadata.update(openbaremap_storage_revision=config['storageRevision'],description='OpenBareMap 2.0; 20 m contours; national and county borders',openbaremap_contour_interval_metres='20')
    dst.executemany('INSERT INTO metadata VALUES(?,?)',metadata.items());removed=0
    old_eligible,old_visible=opt.eligible,opt.visible
    opt.eligible=lambda layer,zoom:layer in ('boundary','contour');opt.visible=keep
    try:
        for z,x,y,data in src.execute('SELECT zoom_level,tile_column,tile_row,tile_data FROM tiles ORDER BY zoom_level,tile_column,tile_row'):
            result=[];count=0
            for name,raw in layers(data):
                filtered,n=opt.filter_layer(raw,z);result.append((name,filtered));count+=n
            removed+=count;dst.execute('INSERT INTO tiles VALUES(?,?,?,?)',(z,x,y,encode(result) if count else data))
        dst.commit()
        if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLite integrity')
    finally:
        opt.eligible,opt.visible=old_eligible,old_visible;dst.close();src.close()
    return removed

def main():
    config=json.loads((ROOT/'config/map-detail-2.0.json').read_text());destination=ROOT/'build/detail-2.0';destination.mkdir(exist_ok=True)
    for name,item in config['inputs'].items():
        source=ROOT/item['path']
        if opt.sha(source)!=item['sha256']:raise ValueError('Changed source: '+name)
        out=destination/(name+'.mbtiles');removed=build(source,out,config)
        print(json.dumps({'dataset':name,'removedFeatureInstances':removed,'sha256':opt.sha(out)}),flush=True)
if __name__=='__main__':main()
