#!/usr/bin/env python3
"""Build the all-Ireland coast, contours and hillshade from locked inputs."""
import argparse
from contextlib import closing
import gzip
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from openbaremap import ROOT, digest, inspect_tiles, write

GDAL=Path('/Applications/QGIS.app/Contents/MacOS')
TOOLS=['ogr2ogr','gdalbuildvrt','gdalwarp','gdaldem','gdal_contour','gdal_translate','gdaladdo','gdalinfo']

def build(args):
    coast=json.loads((ROOT/'coast-sources.lock.json').read_text())
    terrain=json.loads((ROOT/'terrain-sources.lock.json').read_text())
    for item in [coast]+terrain['assets']:
        if digest(ROOT/item['path'])!=item['sha256']:raise ValueError('Input changed: '+item['path'])
    config=json.loads((ROOT/'config/topography.json').read_text())
    tools={name:str(GDAL/name) for name in TOOLS}
    tools['tilemaker']=shutil.which('tilemaker')
    identity={name:{'path':path,'sha256':digest(path)} for name,path in tools.items()}
    env=os.environ.copy()
    env['PROJ_DATA']=str(GDAL.parent/'Resources/qgis/proj')
    env['GDAL_DATA']=str(GDAL.parent/'Resources/qgis/gdal')
    identity['gdal_data']={str(p.relative_to(Path(env['GDAL_DATA']))):digest(p) for p in sorted(Path(env['GDAL_DATA']).rglob('*')) if p.is_file()}
    identity['proj_database']={'path':str(Path(env['PROJ_DATA'])/'proj.db'),'sha256':digest(Path(env['PROJ_DATA'])/'proj.db')}
    identity['gdal_version']=subprocess.check_output([tools['gdalinfo'],'--version'],text=True).strip()
    lock=ROOT/'topography-toolchain.lock.json'
    if lock.exists():
        if json.loads(lock.read_text())!=identity:raise ValueError('Topography tools changed')
    elif args.accept_toolchain:write(lock,identity)
    else:raise ValueError('Use --accept-toolchain once to record the local tools')
    dest=ROOT/'build'/args.name
    dest.mkdir(exist_ok=False)
    record={'status':'started','config':config,'toolchain':identity,'coast_source':coast,'terrain_source_lock_sha256':digest(ROOT/'terrain-sources.lock.json'),'builder_sha256':digest(Path(__file__)),'raster_builder_sha256':digest(Path(__file__).with_name('build_hillshade.py')),'packager_sha256':digest(Path(__file__).with_name('mbtiles.py')),'commands':[],'scope':'local runtime; shared-library and portable container pinning remain pending'}
    write(dest/'build.json',record)
    def run(tool,*argv):
        command=[tools[tool],*map(str,argv)]
        print(tool+' '+(' '.join(map(str,argv)))[:160],flush=True)
        record['commands'].append(command)
        write(dest/'build.json',record)
        with (dest/'build.log').open('a') as log:
            log.write('\n'+json.dumps(command)+'\n');log.flush()
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,env=env)
    try:
        coastfile=dest/'land.geojson'
        zip_path='/vsizip/'+str((ROOT/coast['path']).resolve())+'/land-polygons-split-4326/land_polygons.shp'
        run('ogr2ogr','-f','GeoJSON',coastfile,zip_path,'-spat',*config['coast_context_bounds'],'-clipsrc',*config['coast_context_bounds'],'-lco','COORDINATE_PRECISION=7')
        elevation=dest/'elevation';elevation.mkdir()
        grids=[]
        for asset in terrain['assets']:
            path=elevation/Path(asset['path']).name.removesuffix('.gz')
            with gzip.open(ROOT/asset['path'],'rb') as source,path.open('wb') as out:shutil.copyfileobj(source,out)
            grids.append(path)
        run('gdalbuildvrt',dest/'elevation.vrt',*grids)
        run('gdalwarp','-t_srs',config['projected_crs'],'-tr',config['ground_resolution_m'],config['ground_resolution_m'],'-r','bilinear','-dstnodata','-32768','-cutline',coastfile,'-co','COMPRESS=DEFLATE','-co','TILED=YES',dest/'elevation.vrt',dest/'elevation-itm.tif')
        run('gdal_contour','-i',config['contour_interval_m'],'-a','elevation','-snodata','-32768','-f','GPKG',dest/'elevation-itm.tif',dest/'contours.gpkg')
        run('ogr2ogr','-f','GeoJSON','-t_srs','EPSG:4326','-where','elevation > 0','-simplify',config['contour_simplification_m'],'-lco','COORDINATE_PRECISION=7',dest/'contours.geojson',dest/'contours.gpkg')
        from build_hillshade import raster_stage
        raster_stage(dest/'elevation-itm.tif',dest,config,tools,run)
        tileconfig={'layers':{'land':{'minzoom':4,'maxzoom':config['land_maxzoom'],'source':str(coastfile),'simplify_below':12,'simplify_level':0.00003,'simplify_ratio':2},'contour':{'minzoom':8,'maxzoom':config['vector_maxzoom'],'source':str(dest/'contours.geojson'),'source_columns':['elevation'],'simplify_below':13,'simplify_level':0.00002}},'settings':{'minzoom':4,'maxzoom':config['vector_maxzoom'],'basezoom':config['vector_maxzoom'],'bounding_box':config['coast_context_bounds'],'include_ids':False,'description':'OSM coastal land and Terrain Tiles elevation contours','compress':'gzip','name':'OpenBareMap coast and contours','version':'0.1.0'}}
        write(dest/'tilemaker.json',tileconfig)
        (dest/'process.lua').write_text('node_keys = {}\nway_keys = {}\nfunction node_function() end\nfunction way_function() end\n')
        run('tilemaker','--output',dest/'topography.mbtiles','--config',dest/'tilemaker.json','--process',dest/'process.lua','--threads','1')
        record['outputs']={}
        for name in ['topography.mbtiles','hillshade.mbtiles']:
            path=dest/name
            record['outputs'][name]={'sha256':digest(path),'bytes':path.stat().st_size,'validation':inspect_tiles(path)}
            with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
                record['outputs'][name]['metadata']=dict(db.execute('SELECT name,value FROM metadata'))
        record['status']='built and structurally validated; visual review pending'
        write(dest/'build.json',record)
        print(record['status'],flush=True)
    except Exception as error:
        record['status']='failed';record['error']=str(error);write(dest/'build.json',record)
        raise

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('name',choices=['topography-a','topography-b'])
    parser.add_argument('--accept-toolchain',action='store_true')
    try:build(parser.parse_args())
    except (OSError,ValueError,subprocess.SubprocessError) as error:sys.exit(str(error))
