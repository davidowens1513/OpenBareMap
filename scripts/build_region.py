#!/usr/bin/env python3
"""Build and package a complete edition without replacing Ireland's active map."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from openbaremap import ROOT, digest, inspect_tiles, write
from regions import profile, region_path, region_style
from build_cartography_2 import rebuild, layers, encode
from build_region_geometry import build as geometry_build
import optimize_storage as opt
from trim_contour_padding import trim_layer


def run(*args):
    print('Running: '+' '.join(map(str,args)),flush=True)
    subprocess.run(list(map(str,args)),cwd=ROOT,check=True)

def record_output(path):
    return {'path':str(path.relative_to(ROOT)),'sha256':digest(path),'bytes':path.stat().st_size,'validation':inspect_tiles(path)}

def select_detail(source,target,revision="2.0.0-england-wales-r1"):
    """Shared visibility rules, with constituent-country borders and bounded padding."""
    if target.exists():raise FileExistsError(target)
    from audit import audit
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as src, closing(sqlite3.connect(target)) as dst:
        dst.execute('CREATE TABLE metadata(name TEXT,value TEXT)')
        dst.execute('CREATE TABLE tiles(zoom_level INTEGER,tile_column INTEGER,tile_row INTEGER,tile_data BLOB,PRIMARY KEY(zoom_level,tile_column,tile_row))')
        metadata=dict(src.execute('SELECT name,value FROM metadata'));metadata.update(openbaremap_contour_interval_metres='20',openbaremap_storage_revision=revision)
        dst.executemany('INSERT INTO metadata VALUES (?,?)',metadata.items())
        old_eligible,old_visible=opt.eligible,opt.visible
        def visible(layer,zoom,props):
            if layer=='boundary':
                level=str(props.get('admin_level',''))
                return level in ('2','4') or zoom>=6 and level in ('5','6')
            return opt_original_visible(layer,zoom,props)
        opt_original_visible=old_visible
        opt.eligible=lambda layer,zoom:layer=='boundary' or old_eligible(layer,zoom)
        opt.visible=visible
        try:
            for z,x,y,payload in src.execute('SELECT zoom_level,tile_column,tile_row,tile_data FROM tiles ORDER BY zoom_level,tile_column,tile_row'):
                result=[];changed=False
                for name,raw in layers(payload):
                    filtered,removed=opt.filter_layer(raw,z)
                    if name=='contour':
                        filtered,stats=trim_layer(filtered);changed=changed or bool(stats['changedFeatures'])
                    changed=changed or bool(removed);result.append((name,filtered))
                dst.execute('INSERT INTO tiles VALUES (?,?,?,?)',(z,x,y,encode(result) if changed else payload))
            dst.commit()
        finally:opt.eligible,opt.visible=old_eligible,old_visible

def finish(region, reuse_geometry=False):
    p=profile(region);base=ROOT/'build'/(region+'-basemap');top=ROOT/'build'/(region+'-topography');geometry=ROOT/'build'/(region+'-geometry');final=ROOT/'build'/(region+'-release')
    if final.exists() and not reuse_geometry:raise FileExistsError(final)
    if not reuse_geometry:final.mkdir()
    report=json.loads((geometry/'geometry-report.json').read_text())
    for name,expected in report['outputs'].items():
        if digest(geometry/name)!=expected:raise ValueError('Geometry changed: '+name)
    config={'layers':{
        'landcover':{'minzoom':4,'maxzoom':14,'source':str(geometry/'landcover.geojson'),'source_columns':['class','wetland','natural','landuse','name','name_en','name_cy','name_gd','name_es','name_fr','official_name','short_name'],'simplify_below':14,'simplify_level':.000008,'simplify_ratio':2},
        'contour':{'minzoom':8,'maxzoom':14,'source':str(geometry/'contours.geojson'),'source_columns':['elevation'],'simplify_below':13,'simplify_level':.00001},
        'grid_1km':{'minzoom':12,'maxzoom':14,'source':str(geometry/'grid_1km.geojson'),'source_columns':['label','metres','axis']},
        'grid_10km':{'minzoom':10,'maxzoom':14,'source':str(geometry/'grid_10km.geojson'),'source_columns':['label','metres','axis']}},
        'settings':{'minzoom':4,'maxzoom':14,'basezoom':14,'bounding_box':p['bounds'],'include_ids':False,'compress':'gzip','name':p['name']+' geometry','description':p['coverage'],'version':p['mapVersion']}}
    if reuse_geometry:
        checkpoint=json.loads((final/'geometry-validation.json').read_text())
        if json.loads((final/'tilemaker.json').read_text())!=config or digest(final/'geometry.mbtiles')!=checkpoint['sha256'] or digest(final/'tilemaker.json')!=checkpoint['configSHA256']:
            raise ValueError('Geometry checkpoint changed')
    else:
        write(final/'tilemaker.json',config);(final/'process.lua').write_text('node_keys={}\nway_keys={}\nfunction node_function() end\nfunction way_function() end\n')
        tool=shutil.which('tilemaker')
        if digest(tool)!=json.loads((ROOT/'toolchain.lock.json').read_text())['tilemaker']['sha256']:raise ValueError('Tilemaker changed')
        with (final/'tilemaker.log').open('w') as log:
            subprocess.run([tool,'--output',str(final/'geometry.mbtiles'),'--config',str(final/'tilemaker.json'),'--process',str(final/'process.lua'),'--threads','1'],stdout=log,stderr=subprocess.STDOUT,check=True)
        from audit import audit
        write(final/'geometry-validation.json',{'sha256':digest(final/'geometry.mbtiles'),'configSHA256':digest(final/'tilemaker.json'),'validation':inspect_tiles(final/'geometry.mbtiles'),'audit':audit(final/'geometry.mbtiles',{'landcover','contour','grid_1km','grid_10km'})})
    replacements={}
    replacements['basemap']=rebuild(base/'basemap.mbtiles',final/'basemap-smoothed.mbtiles',final/'geometry.mbtiles','landcover')
    replacements['topography']=rebuild(top/'topography.mbtiles',final/'topography-smoothed.mbtiles',final/'geometry.mbtiles','contour')
    for name in ('basemap','topography'):
        select_detail(final/(name+'-smoothed.mbtiles'),final/(name+'.mbtiles'),p['mapVersion']+'-'+region+'-r1')
    # Extract only grid layers; unrelated contour and landcover do not enter this DB.
    with closing(sqlite3.connect((final/'geometry.mbtiles').as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(final/'grid.mbtiles')) as dst:
        dst.execute('CREATE TABLE metadata(name TEXT,value TEXT)');dst.execute('CREATE TABLE tiles(zoom_level INTEGER,tile_column INTEGER,tile_row INTEGER,tile_data BLOB,PRIMARY KEY(zoom_level,tile_column,tile_row))')
        metadata=dict(src.execute('SELECT name,value FROM metadata'));schema=json.loads(metadata['json']);schema['vector_layers']=[l for l in schema['vector_layers'] if l['id'].startswith('grid_')];metadata.update(name=p['gridName'],minzoom='10',maxzoom='14',json=json.dumps(schema))
        dst.executemany('INSERT INTO metadata VALUES (?,?)',metadata.items())
        for z,x,y,data in src.execute('SELECT zoom_level,tile_column,tile_row,tile_data FROM tiles WHERE zoom_level>=10'):
            selected=[(n,v) for n,v in layers(data) if n.startswith('grid_')]
            if selected:dst.execute('INSERT INTO tiles VALUES (?,?,?,?)',(z,x,y,encode(selected)))
        dst.commit()
    datasets={name:record_output(final/(name+'.mbtiles')) for name in ('basemap','topography','grid')}
    datasets['hillshade']=record_output(top/'hillshade.mbtiles')
    from audit import audit
    for name,expected in [('basemap',None),('topography',{'land','contour'}),('grid',{'grid_1km','grid_10km'})]:
        write(final/(name+'-audit.json'),audit(ROOT/datasets[name]['path'],expected))
    release_maps=ROOT/'releases'/region/p['mapVersion']/'maps'
    release_maps.mkdir(parents=True,exist_ok=True)
    for name,item in datasets.items():
        target=release_maps/(name+'.mbtiles')
        if target.exists():raise FileExistsError(target)
        shutil.copyfile(ROOT/item['path'],target)
        if digest(target)!=item['sha256']:raise ValueError('Release copy changed: '+name)
        item['path']=str(target.relative_to(ROOT))
    active={'format':'openbaremap-development-viewer-v1','region':region,'mapVersion':p['mapVersion'],'storageRevision':p['mapVersion']+'-'+region+'-r1','contourIntervalMetres':20,'localBorders':False,'styleRevision':p.get('styleRevision','shared'),'datasets':datasets,'coverage':p['coverage']}
    write(region_path(region,'active-map.json'),active)
    write(final/'build.json',{'status':'built and structurally validated; visual/device review pending','region':region,'geometryReport':report,'replacements':replacements,'outputs':datasets,'builderSHA256':digest(Path(__file__))})
    write(region_path(region,'style.json'),region_style(region))
    shutil.copyfile(geometry/'grid-provenance.json',region_path(region,'grid-provenance.json'))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--region',choices=['england-wales','scotland','sierra-nevada','pyrenees'],required=True);parser.add_argument('--resume-geometry',action='store_true');parser.add_argument('--stage',choices=['basemap','geometry','finish','packages','all'],default='all');args=parser.parse_args();region=args.region
    if args.stage in ('basemap','all'):
        dest=ROOT/'build'/(region+'-basemap')
        if not dest.exists():run(sys.executable,'scripts/openbaremap.py','build',region+'-basemap','--region',region)
        else:
            record=json.loads((dest/'build.json').read_text())
            if record['status']!='validated vector build' or digest(dest/'basemap.mbtiles')!=record['output_sha256']:raise ValueError('Existing basemap is incomplete or changed')
    if args.stage in ('geometry','all'):
        dest=ROOT/'build'/(region+'-geometry')
        if not dest.exists():geometry_build(region,ROOT/'build'/(region+'-topography'))
        elif not (dest/'geometry-report.json').exists():raise ValueError('Incomplete geometry stage')
    if args.stage in ('finish','all'):
        if not region_path(region,'active-map.json').exists():finish(region,args.resume_geometry)
        else:
            for item in json.loads(region_path(region,'active-map.json').read_text())['datasets'].values():
                if digest(ROOT/item['path'])!=item['sha256']:raise ValueError('Selected output changed')
    if args.stage in ('packages','all'):
        if not (ROOT/'regions'/region/'legend/legend-manifest.json').exists():run(sys.executable,'scripts/build_app_legend.py','--region',region)
        for platform,builder in [('ios','ios/build_bundle.py'),('android','android/build_package.py')]:
            output=ROOT/'regions'/region/platform
            if not output.exists():run(sys.executable,builder,'--region',region,'--output',output)
            elif not (output/'validation.json').exists():raise ValueError('Incomplete '+platform+' package')

if __name__=='__main__':main()
