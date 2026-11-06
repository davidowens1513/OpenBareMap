#!/usr/bin/env python3
"""Acquire full regional sources and immutable locks, then merge border duplicates."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import urllib.request
from openbaremap import ROOT, digest, write
from regions import profile, region_path

sys.path.insert(0, str(ROOT/'work/python'))

def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        part = path.with_name(path.name+'.part')
        with urllib.request.urlopen(url, timeout=120) as src, part.open('wb') as out:
            shutil.copyfileobj(src, out)
        part.rename(path)
    return {'path': str(path.relative_to(ROOT)), 'url': url, 'bytes': path.stat().st_size, 'sha256': digest(path)}

def verify(lock):
    for item in lock:
        if digest(ROOT/item['path']) != item['sha256']:
            raise ValueError('Locked source changed: '+item['path'])

def extract_complete(source, target, bounds):
    """Select in-bounds nodes, parent ways/relations and their complete references."""
    import osmium
    checkpoint=target.with_suffix('.extract.json')
    identity={'sourceSHA256':digest(source),'bounds':bounds,'relationDepth':10}
    if checkpoint.exists():
        record=json.loads(checkpoint.read_text())
        if any(record.get(k)!=v for k,v in identity.items()) or digest(target)!=record['sha256']:
            raise ValueError('Changed extraction checkpoint: '+str(target))
        return
    if target.exists():raise FileExistsError('Unregistered extraction: '+str(target))
    west,south,east,north=bounds;ids=osmium.IdTracker()
    class Nodes(osmium.SimpleHandler):
        def node(self,n):
            if n.location.valid() and west<=n.location.lon<=east and south<=n.location.lat<=north:
                ids.add_node(n.id)
    Nodes().apply_file(str(source))
    ids.complete_forward_references(str(source),relation_depth=10)
    ids.complete_backward_references(str(source),relation_depth=10)
    with osmium.io.Reader(str(source)) as reader:header=reader.header()
    with osmium.SimpleWriter(str(target),header=header) as writer:
        for obj in osmium.FileProcessor(str(source)).with_filter(ids.id_filter()):writer.add(obj)
    write(checkpoint,{**identity,'sha256':digest(target),'bytes':target.stat().st_size,
        'operation':'In-bounds nodes plus referencing ways and relations; complete backward references, nested relation depth 10'})
    print(target.name+' complete-feature extract verified',flush=True)


def fetch_osm(region):
    import osmium
    p=profile(region);lockpath=region_path(region,'sources.lock.json')
    if lockpath.exists():
        existing=json.loads(lockpath.read_text());verify(existing['inputs']+[existing['osm']]);return
    directory=ROOT/'data/regions'/region;stamp=p['sourceDate'].replace('-','')[2:]
    base=p.get('sourceBaseURL','https://download.geofabrik.de/europe/united-kingdom/')
    def acquire(slug):
        name=f'{slug}-{stamp}.osm.pbf';source_base=p.get('sourceBaseOverrides',{}).get(slug,base);url=source_base+name
        path=directory/name
        if not path.exists():
            from download_ranges import fetch
            fetch(url,path,workers=4 if p.get('clipSource') else 8)
        with urllib.request.urlopen(url+'.md5',timeout=60) as response:expected=response.read().decode().split()[0]
        with path.open('rb') as stream:actual=hashlib.file_digest(stream,'md5').hexdigest()
        if actual!=expected:raise ValueError('Source MD5 does not match upstream: '+name)
        item=download(url,path)
        with osmium.io.Reader(str(ROOT/item['path'])) as reader:
            item['replicationTimestamp']=reader.header().get('osmosis_replication_timestamp')
        return item
    with ThreadPoolExecutor(max_workers=3 if p.get('clipSource') else 1) as pool:
        inputs=list(pool.map(acquire,p['sourceSlugs']))
    timestamps={item['replicationTimestamp'] for item in inputs}
    if len(timestamps)!=1 or not next(iter(timestamps)):
        raise ValueError('Regional inputs must share a nonempty OSM snapshot timestamp')
    polygons=[download(p.get('sourceBaseOverrides',{}).get(slug,base)+slug+'.poly',directory/(slug+'.poly')) for slug in p['sourceSlugs']]
    merge_inputs=inputs
    if p.get('clipSource'):
        merge_inputs=[]
        for item in inputs:
            clipped=directory/(Path(item['path']).stem+'.clipped.osm.pbf')
            extract_complete(ROOT/item['path'],clipped,p['bounds'])
            merge_inputs.append({**item,'path':str(clipped.relative_to(ROOT))})
    if len(inputs)==1:
        merged={**merge_inputs[0],'snapshot_date':p['sourceDate'],'operation':'Complete-feature bbox extraction with nested relation references' if p.get('clipSource') else 'Complete upstream extract; no merge or spatial filtering'}
        if p.get('clipSource'):merged.update(sha256=digest(ROOT/merged['path']),bytes=(ROOT/merged['path']).stat().st_size)
    else:
        # Additional extracts are buffered; the largest primary extract streams from disk.
        output=directory/(p.get('sourceOutputStem',region)+'-'+stamp+'.osm.pbf')
        if output.exists():raise FileExistsError('Unregistered merged input: '+str(output))
        merger=osmium.MergeInputReader()
        for item in merge_inputs[1:]:merger.add_file(str(ROOT/item['path']))
        with osmium.io.Reader(str(ROOT/merge_inputs[0]['path'])) as reader:
            header=reader.header();header.set('osmosis_replication_timestamp',next(iter(timestamps)))
            writer=osmium.io.Writer(str(output),header)
            try:merger.apply_to_reader(reader,writer)
            finally:writer.close()
        merged={'path':str(output.relative_to(ROOT)),'sha256':digest(output),'bytes':output.stat().st_size,'snapshot_date':p['sourceDate'],'replicationTimestamp':next(iter(timestamps)),'operation':('Complete-feature bbox extraction with nested relation references, then libosmium sorted merge; duplicate OSM objects resolved by version' if p.get('clipSource') else 'libosmium sorted merge; duplicate OSM objects resolved by version'),'url':None}
    write(lockpath,{'osm':merged,'inputs':inputs,'polygons':polygons,'accessed_utc':datetime.now(timezone.utc).isoformat()})
    print('Full '+p['label']+' OSM source locked.',flush=True)

def fetch_terrain(region):
    if profile(region).get('terrainProvider')=='copernicus-glo30':
        from fetch_copernicus import fetch
        return fetch(region)
    p=profile(region);lockpath=region_path(region,'terrain-sources.lock.json')
    if lockpath.exists():verify(json.loads(lockpath.read_text())['assets']);return
    west,south,east,north=p['terrainBounds']
    directory=ROOT/'data/regions'/region/'elevation'
    def fetch(cell):
        lat,lon=cell;ns='N' if lat>=0 else 'S';ew='E' if lon>=0 else 'W'
        name=f'{ns}{abs(lat):02d}{ew}{abs(lon):03d}.hgt.gz'
        item=download(f'https://elevation-tiles-prod.s3.amazonaws.com/skadi/{ns}{abs(lat):02d}/{name}',directory/name)
        if len(gzip.decompress((ROOT/item['path']).read_bytes()))!=3601*3601*2:
            raise ValueError('Invalid elevation cell: '+name)
        print(name+' verified',flush=True);return item
    with ThreadPoolExecutor(max_workers=4) as pool:
        assets=list(pool.map(fetch,[(lat,lon) for lat in range(south,north) for lon in range(west,east)]))
    write(lockpath,{'dataset':'Mapzen/Terrain Tiles skadi composite elevation, not pure SRTM','coverage':p['terrainBounds'],'grid':'3601 by 3601 signed 16-bit heights per degree tile','accessed_utc':datetime.now(timezone.utc).isoformat(),'documentation':'https://github.com/tilezen/joerd/tree/master/docs','assets':assets})

def fetch_dem_padding(region):
    if profile(region).get('terrainProvider')=='copernicus-glo30':
        from fetch_copernicus import fetch
        return fetch(region,padding=True)
    p=profile(region);lockpath=ROOT/'regions'/region/'garmin/dem-padding.lock.json'
    if lockpath.exists():verify(json.loads(lockpath.read_text())['assets']);return
    existing={Path(item['path']).name for item in json.loads(region_path(region,'terrain-sources.lock.json').read_text())['assets']}
    west,south,east,north=p['terrainBounds'];directory=ROOT/'data/regions'/region/'elevation'
    cells=[(lat,lon) for lat in range(south-1,north+1) for lon in range(west-1,east+1)]
    def fetch(cell):
        lat,lon=cell;name=f'N{lat:02d}{"W" if lon<0 else "E"}{abs(lon):03d}.hgt.gz'
        if name in existing:return None
        item=download(f'https://elevation-tiles-prod.s3.amazonaws.com/skadi/N{lat:02d}/{name}',directory/name)
        if len(gzip.decompress((ROOT/item['path']).read_bytes()))!=3601*3601*2:raise ValueError('Invalid padding HGT: '+name)
        return item
    with ThreadPoolExecutor(max_workers=4) as pool:assets=[item for item in pool.map(fetch,cells) if item]
    lockpath.parent.mkdir(parents=True,exist_ok=True)
    write(lockpath,{'dataset':'Mapzen/Terrain Tiles skadi composite elevation','purpose':'Garmin DEM interpolation padding beyond the complete regional source extent','coverage':[west-1,south-1,east+1,north+1],'assets':assets,'accessed_utc':datetime.now(timezone.utc).isoformat()})
    print('Garmin DEM padding locked:',len(assets),'additional cells',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--region',choices=['england-wales','scotland','sierra-nevada','pyrenees','dolomites','faroe-islands'],required=True);parser.add_argument('--stage',choices=['osm','terrain','padding','all'],default='all');args=parser.parse_args()
    if args.stage=='padding':fetch_dem_padding(args.region)
    if args.stage in ('terrain','all'):fetch_terrain(args.region)
    if args.stage in ('osm','all'):fetch_osm(args.region)
