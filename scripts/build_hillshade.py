#!/usr/bin/env python3
"""Independent raster stage consuming a recorded projected elevation checkpoint."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
from contextlib import closing
import subprocess
import sys
from openbaremap import ROOT,digest,inspect_tiles,write
from mbtiles import canonicalize


def raster_stage(elevation,dest,config,tools,run):
    run('gdaldem','hillshade',elevation,dest/'hillshade.tif','-multidirectional','-alt',config['hillshade_altitude'],'-scale','1','-co','COMPRESS=DEFLATE','-co','TILED=YES')
    colours=dest/'hillshade-colours.txt'
    # GDAL hillshade uses 0 for no-data and 1..255 for valid shade values.
    # A numeric zero entry is necessary as well as nv: duplicate zero/nv
    # lookup keys otherwise allow an opaque shadow colour to win.
    colours.write_text('0 0 0 0 0\n1 50 43 30 150\n128 50 43 30 65\n255 50 43 30 0\nnv 0 0 0 0\n')
    run('gdaldem','color-relief',dest/'hillshade.tif',colours,dest/'hillshade-rgba.tif','-alpha','-co','COMPRESS=DEFLATE','-co','TILED=YES')
    resolution=156543.03392804097/(2**config['hillshade_zoom'])
    run('gdalwarp','-t_srs','EPSG:3857','-tr',resolution,resolution,'-tap','-r','bilinear','-dstalpha','-co','COMPRESS=DEFLATE','-co','TILED=YES',dest/'hillshade-rgba.tif',dest/'hillshade-mercator.tif')
    run('gdal_translate','-of','MBTiles','-co','TILE_FORMAT=PNG','-co','ZOOM_LEVEL_STRATEGY=AUTO',dest/'hillshade-mercator.tif',dest/'hillshade-raw.mbtiles')
    run('gdaladdo','-r','average',dest/'hillshade-raw.mbtiles','2','4','8','16','32','64')
    canonicalize(dest/'hillshade-raw.mbtiles',dest/'hillshade.mbtiles')


def main(args):
    source=ROOT/'build'/args.source
    upstream=json.loads((source/'build.json').read_text())
    if not upstream['status'].startswith('built and structurally validated'):raise ValueError('Upstream build is not validated')
    elevation=source/'elevation-itm.tif'
    checkpoint={'path':str(elevation.relative_to(ROOT)),'sha256':digest(elevation),'upstream_build_record_sha256':digest(source/'build.json'),'source_config':upstream['config']}
    tools={name:item['path'] for name,item in upstream['toolchain'].items() if isinstance(item,dict) and 'path' in item and name!='proj_database'}
    for name,path in tools.items():
        if digest(path)!=upstream['toolchain'][name]['sha256']:raise ValueError('Tool changed: '+name)
    env=os.environ.copy();env['PROJ_DATA']=str(Path(upstream['toolchain']['proj_database']['path']).parent);env['GDAL_DATA']='/Applications/QGIS.app/Contents/Resources/qgis/gdal'
    for relative,sha in upstream['toolchain']['gdal_data'].items():
        if digest(Path(env['GDAL_DATA'])/relative)!=sha:raise ValueError('GDAL data changed')
    if digest(Path(env['PROJ_DATA'])/'proj.db')!=upstream['toolchain']['proj_database']['sha256']:raise ValueError('PROJ database changed')
    dest=ROOT/'build'/args.name;dest.mkdir(exist_ok=False)
    record={'status':'started','input':checkpoint,'raster_builder_sha256':digest(Path(__file__)),'packager_sha256':digest(Path(__file__).with_name('mbtiles.py')),'commands':[],'toolchain':upstream['toolchain'],'sqlite_version':sqlite3.sqlite_version}
    write(dest/'build.json',record)
    def run(tool,*argv):
        command=[tools[tool],*map(str,argv)];print(tool,flush=True);record['commands'].append(command);write(dest/'build.json',record)
        with (dest/'build.log').open('a') as log:
            log.write('\n'+json.dumps(command)+'\n');log.flush();subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=env,check=True)
    try:
        raster_stage(elevation,dest,upstream['config'],tools,run)
        path=dest/'hillshade.mbtiles';record['output']={'sha256':digest(path),'bytes':path.stat().st_size,'validation':inspect_tiles(path)}
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:record['output']['metadata']=dict(db.execute('SELECT name,value FROM metadata'))
        record['status']='built and structurally validated; visual review pending';write(dest/'build.json',record);print(record['status'],flush=True)
    except Exception as error:
        record['status']='failed';record['error']=str(error);write(dest/'build.json',record);raise

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',choices=['topography-a','topography-b']);parser.add_argument('name',choices=['hillshade-a','hillshade-b'])
    try:main(parser.parse_args())
    except (OSError,ValueError,subprocess.SubprocessError) as error:sys.exit(str(error))
