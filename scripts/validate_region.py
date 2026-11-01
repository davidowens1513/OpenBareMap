#!/usr/bin/env python3
"""Verify complete regional coverage, packages and preservation of Ireland."""
import argparse
from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3
from openbaremap import ROOT,digest,inspect_tiles,write
from regions import active_map,profile,region_path,region_style
from build_cartography_2 import layers
from audit import fields
from optimize_storage import packed,value

ANCHORS={
    'Isles of Scilly':[-6.311,49.914], 'Lands End':[-5.714,50.065],
    'Dartmoor':[-3.94,50.58], 'Dover':[1.313,51.127],
    'Lowestoft':[1.75,52.475], 'London':[-.128,51.507],
    'Cardiff':[-3.179,51.482], 'Pembrokeshire':[-5.267,51.881],
    'Anglesey':[-4.331,53.229], 'Eryri':[-4.076,53.068],
    'Bannau Brycheiniog':[-3.436,51.884], 'Peak District':[-1.837,53.35],
    'Lake District':[-3.211,54.455], 'Carlisle':[-2.938,54.893],
    'Berwick upon Tweed':[-2.004,55.77], 'Holy Island':[-1.802,55.67]
}

def xyz(lon,lat,zoom):
    n=2**zoom
    return int((lon+180)/360*n),int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)

def land_coverage(path,anchors=None):
    """Check actual polygon coverage, including the two reported blue patches."""
    anchors=anchors or {'Moelwyn':[-3.995,52.965],'Llandeilo':[-3.991,51.886],
             'London':[-.128,51.507],'Cardiff':[-3.179,51.482],
             'Carlisle':[-2.938,54.893],'Dartmoor':[-3.94,50.58]}
    def contains(raw,px,py):
        extent=next((v for n,w,v in fields(raw) if n==5),4096)
        px*=extent;py*=extent
        for n,w,feature in fields(raw):
            if n!=2 or w!=2:continue
            geometry=next((packed(v) for n,w,v in fields(feature) if n==4 and w==2),[])
            i=x=y=0;rings=[];ring=[]
            while i<len(geometry):
                command=geometry[i];i+=1;op=command&7;count=command>>3
                if op==7:
                    if ring:rings.append(ring);ring=[]
                    continue
                if op not in (1,2):raise ValueError('Unexpected land geometry command')
                for _ in range(count):
                    dx,dy=geometry[i:i+2];i+=2
                    x+=(dx>>1)^-(dx&1);y+=(dy>>1)^-(dy&1)
                    if op==1 and ring:rings.append(ring);ring=[]
                    ring.append((x,y))
            if ring:rings.append(ring)
            inside=False
            for ring in rings:
                for a,b in zip(ring,ring[1:]+ring[:1]):
                    if (a[1]>py)!=(b[1]>py) and px<(b[0]-a[0])*(py-a[1])/(b[1]-a[1])+a[0]:inside=not inside
            if inside:return True
        return False
    result={}
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        for name,(lon,lat) in anchors.items():
            for z in range(8,13):
                fx=(lon+180)/360*2**z;fy=(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*2**z
                row=db.execute('SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?',(z,int(fx),2**z-1-int(fy))).fetchone()
                if not row or not any(contains(raw,fx%1,fy%1) for layer,raw in layers(row[0]) if layer=='land'):
                    raise ValueError(f'Missing land background at {name}, zoom {z}')
            result[name]={'coordinate':[lon,lat],'verifiedZooms':[8,9,10,11,12]}
    return result

def coverage(path):
    result={}
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        for name,(lon,lat) in ANCHORS.items():
            x,y=xyz(lon,lat,14);count=0
            for xx in range(x-1,x+2):
                for yy in range(y-1,y+2):
                    row=db.execute('SELECT tile_data FROM tiles WHERE zoom_level=14 AND tile_column=? AND tile_row=?',(xx,2**14-1-yy)).fetchone()
                    if row:
                        for layer,raw in layers(row[0]):count+=sum(n==2 and w==2 for n,w,_ in fields(raw))
            if not count:raise ValueError('No detailed features around '+name)
            result[name]={'coordinate':[lon,lat],'featuresInNeighbouringDetailedTiles':count}
    return result

def detail(path):
    counts={'contours':0,'boundaries':0}
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        for payload, in db.execute('SELECT tile_data FROM tiles'):
            for name,raw in layers(payload):
                if name not in ('contour','boundary'):continue
                fs=list(fields(raw));keys=[v.decode() for n,w,v in fs if n==3 and w==2];values=[value(v) for n,w,v in fs if n==4 and w==2]
                for n,w,feature in fs:
                    if n!=2 or w!=2:continue
                    tags=next((packed(v) for n,w,v in fields(feature) if n==2 and w==2),[])
                    props={keys[k]:values[v] for k,v in zip(tags[::2],tags[1::2])}
                    if name=='contour':
                        if float(props['elevation'])%20:raise ValueError('Unexpected contour interval')
                        counts['contours']+=1
                    else:
                        if str(props.get('admin_level','')) not in ('2','4','5','6'):raise ValueError('Unexpected local boundary')
                        counts['boundaries']+=1
    return counts

def package(root,platform):
    manifest=json.loads((root/'manifest.json').read_text());style=json.loads((root/'style.json').read_text())
    if manifest['region']!='england-wales':raise ValueError('Wrong package region')
    selected=active_map(manifest['region'])
    if manifest['storageRevision']!=selected['storageRevision']:raise ValueError('Stale package revision')
    databases=manifest['datasets'] if platform=='ios' else manifest['databases']
    for name,item in selected['datasets'].items():
        if databases[name]['sha256']!=item['sha256']:raise ValueError('Stale packaged dataset: '+name)
    if manifest['regionStyleSHA256']!=digest(region_path(manifest['region'],'style.json')):raise ValueError('Stale regional package style')
    if 'townlands' in style['sources'] or 'irish-grid' in style['sources']:raise ValueError('Ireland-specific source leaked')
    if 'british-grid' not in style['sources']:raise ValueError('Missing British National Grid')
    checked=0
    for line in (root/'SHA256SUMS.txt').read_text().splitlines():
        expected,name=line.split('  ',1);path=(root/name).resolve()
        if not path.is_relative_to(root.resolve()) or digest(path)!=expected:raise ValueError('Package checksum: '+name)
        checked+=1
    for name,relative in manifest['sourceFiles'].items():
        if not (root/relative).is_file() or name not in style['sources']:raise ValueError('Missing runtime source')
        source=style['sources'][name]
        if not source['url'].startswith('mbtiles://{'):raise ValueError('Nonlocal runtime source')
    return {'checkedFiles':checked,'sourceFiles':manifest['sourceFiles'],'nativeDeviceRenderingTested':False}

def welsh_glyphs():
    result={}
    for font in (ROOT/'viewer/fonts').iterdir():
        if not font.is_dir():continue
        glyphs=set()
        for n,w,stack in fields((font/'256-511.pbf').read_bytes()):
            if n==1 and w==2:
                for number,wire,glyph in fields(stack):
                    if number==3 and wire==2:
                        glyphs.update(v for k,t,v in fields(glyph) if k==1 and t==0)
        if not {372,373,374,375}.issubset(glyphs):raise ValueError('Missing Welsh glyphs: '+font.name)
        result[font.name]=True
    return result

def validate(region):
    p=profile(region);active=active_map(region);output={'region':region,'coverage':p['coverage'],'status':'automated checks passed; visual and hardware acceptance pending','datasets':{}}
    for name,item in active['datasets'].items():
        path=ROOT/item['path']
        if digest(path)!=item['sha256']:raise ValueError('Selected dataset changed: '+name)
        output['datasets'][name]=inspect_tiles(path)
    output['coverageAnchors']=coverage(ROOT/active['datasets']['basemap']['path'])
    output['landBackground']=land_coverage(ROOT/active['datasets']['topography']['path'])
    output['detail']={name:detail(ROOT/active['datasets'][name]['path']) for name in ('basemap','topography')}
    output['packages']={platform:package(ROOT/'regions'/region/platform/folder,platform) for platform,folder in [('ios','OpenBareMap.bundle'),('android','OpenBareMap')]}
    baseline=json.loads((ROOT/'regions/ireland/preservation-baseline.json').read_text())
    for relative,expected in baseline['files'].items():
        if digest(ROOT/relative)!=expected:raise ValueError('Ireland baseline changed: '+relative)
    output['irelandPreserved']=True
    output['welshGlyphs']=welsh_glyphs()
    geometry=json.loads((ROOT/'build'/(region+'-geometry')/'geometry-report.json').read_text())
    output['geometryProcessing']=geometry['counts']
    garmin=json.loads((ROOT/'regions'/region/'garmin/build-report.json').read_text())
    if garmin['familyId']!=p['garminFamilyId'] or garmin['routing']:raise ValueError('Wrong Garmin identity or routing')
    if digest(ROOT/garmin['output']['path'])!=garmin['output']['sha256']:raise ValueError('Garmin checksum changed')
    output['garmin']=garmin
    release=ROOT/'releases'/region/p['mapVersion'];release.mkdir(parents=True,exist_ok=True)
    write(release/'validation.json',output)
    package_records={}
    for platform,folder in [('ios','OpenBareMap.bundle'),('android','OpenBareMap')]:
        directory=ROOT/'regions'/region/platform;resource_root=directory/folder
        package_records[platform]={'path':str(directory.relative_to(ROOT)),'validationSHA256':digest(directory/'validation.json'),'manifestSHA256':digest(resource_root/'manifest.json'),'checksumsSHA256':digest(resource_root/'SHA256SUMS.txt')}
        if platform=='android':
            archive=directory/'OpenBareMap-Android.zip'
            package_records[platform]['archive']={'path':str(archive.relative_to(ROOT)),'bytes':archive.stat().st_size,'sha256':digest(archive)}
    write(release/'manifest.json',{'region':region,'mapVersion':p['mapVersion'],'coverage':p['coverage'],'datasets':active['datasets'],'osm':json.loads(region_path(region,'sources.lock.json').read_text())['osm'],'terrainLockSHA256':digest(region_path(region,'terrain-sources.lock.json')),'styleSHA256':digest(region_path(region,'style.json')),'pythonRuntime':json.loads(region_path(region,'python-runtime.json').read_text()),'garmin':garmin['output'],'packages':package_records,'validation':'validation.json','acceptance':'Automated checks only; see validation and visual-review records for actual reviewed scope.'})
    print('Full England/Wales build, packages and Ireland preservation verified.',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--region',choices=['england-wales'],required=True);args=parser.parse_args();validate(args.region)
