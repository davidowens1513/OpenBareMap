#!/usr/bin/env python3
"""Extend coastal background without changing any contour layer payloads."""
from pathlib import Path
from contextlib import closing
import argparse,json,os,shutil,sqlite3,subprocess
from openbaremap import ROOT,digest,write,inspect_tiles
from regions import profile,region_path,region_style,active_map
from build_cartography_2 import rebuild,layers
from mbtiles import canonicalize

def build(region,revision=3):
    p=profile(region);bounds=p['coastContextBounds'];suffix='' if revision==3 else '-r'+str(revision);dest=ROOT/'build'/(region+'-coast-context'+suffix);dest.mkdir(exist_ok=False)
    active=active_map(region);old=active['datasets']['topography'];coast=json.loads((ROOT/'coast-sources.lock.json').read_text())
    if digest(ROOT/coast['path'])!=coast['sha256'] or digest(ROOT/old['path'])!=old['sha256']:raise ValueError('Source changed')
    tools=json.loads((ROOT/'topography-toolchain.lock.json').read_text())
    env=os.environ.copy();env['PROJ_DATA']=str(Path(tools['proj_database']['path']).parent);env['GDAL_DATA']='/Applications/QGIS.app/Contents/Resources/qgis/gdal'
    ogr=tools['ogr2ogr']['path'];tilemaker=tools['tilemaker']['path']
    for name in ('ogr2ogr','tilemaker'):
        if digest(tools[name]['path'])!=tools[name]['sha256']:raise ValueError('Tool changed')
    source='/vsizip/'+str(ROOT/coast['path'])+'/land-polygons-split-4326/land_polygons.shp'
    subprocess.run([ogr,'-f','GeoJSON',str(dest/'land.geojson'),source,'-spat',*map(str,bounds),'-clipsrc',*map(str,bounds),'-lco','COORDINATE_PRECISION=7'],env=env,check=True)
    config={'layers':{'land':{'minzoom':4,'maxzoom':12,'source':str(dest/'land.geojson'),'simplify_below':12,'simplify_level':.00003,'simplify_ratio':2}},'settings':{'minzoom':4,'maxzoom':14,'basezoom':14,'bounding_box':bounds,'include_ids':False,'compress':'gzip','name':p['name']+' coastal context','description':'Coastal background beyond edition coverage; source OSM land polygons','version':p['mapVersion']}}
    write(dest/'tilemaker.json',config);(dest/'process.lua').write_text('node_keys={}\nway_keys={}\nfunction node_function() end\nfunction way_function() end\n')
    with (dest/'tilemaker.log').open('w') as log:subprocess.run([tilemaker,'--output',str(dest/'coast.mbtiles'),'--config',str(dest/'tilemaker.json'),'--process',str(dest/'process.lua'),'--threads','1'],stdout=log,stderr=subprocess.STDOUT,check=True)
    # Tilemaker needs the normal base precision even when this layer stops at 12.
    # Its higher zoom placeholders contain no land and must not enter the export.
    with closing(sqlite3.connect(dest/'coast.mbtiles')) as db:
        for payload, in db.execute('SELECT tile_data FROM tiles WHERE zoom_level>12'):
            if list(layers(payload)):raise ValueError('Unexpected coastal features above zoom 12')
        db.execute('DELETE FROM tiles WHERE zoom_level>12')
        db.execute("UPDATE metadata SET value='12' WHERE name='maxzoom'")
        db.commit();db.execute('VACUUM')
    replacement=rebuild(ROOT/old['path'],dest/'combined.mbtiles',dest/'coast.mbtiles','land')
    with closing(sqlite3.connect(dest/'combined.mbtiles')) as db:
        for name,value in [('bounds',','.join(map(str,bounds))),('openbaremap_storage_revision',p['mapVersion']+'-'+region+'-r'+str(revision))]:
            db.execute('DELETE FROM metadata WHERE name=?',(name,));db.execute('INSERT INTO metadata VALUES (?,?)',(name,value))
        db.commit()
    output=ROOT/'releases'/region/p['mapVersion']/'maps'/('topography-context'+suffix+'.mbtiles');canonicalize(dest/'combined.mbtiles',output)
    record={'path':str(output.relative_to(ROOT)),'sha256':digest(output),'bytes':output.stat().st_size,'validation':inspect_tiles(output)}
    release=output.parent.parent
    write(release/('initial-active-map.json' if revision==3 else 'context'+suffix+'-input-active-map.json'),active)
    active['datasets']['topography']=record;active['storageRevision']=p['mapVersion']+'-'+region+'-r'+str(revision)
    write(region_path(region,'active-map.json'),active);write(region_path(region,'style.json'),region_style(region))
    write(release/('coast-context'+suffix+'-report.json'),{'source':coast,'contextBounds':bounds,'oldTopography':old,'replacement':replacement,'output':record,'builderSHA256':digest(Path(__file__)),'note':'Contour payloads preserved exactly while extending land background outside edition coverage.'})
    print('Coastal context extended; contour layer payloads preserved.',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--region',choices=['england-wales','scotland','sierra-nevada','pyrenees','dolomites','faroe-islands'],required=True);parser.add_argument('--revision',type=int,choices=[3,4],default=3);args=parser.parse_args();build(args.region,args.revision)
