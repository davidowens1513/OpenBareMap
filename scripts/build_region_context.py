#!/usr/bin/env python3
"""Extend coastal background without changing any contour layer payloads."""
from pathlib import Path
from contextlib import closing
import argparse,json,os,shutil,sqlite3,subprocess
from openbaremap import ROOT,digest,write,inspect_tiles
from regions import profile,region_path,region_style,active_map
from build_cartography_2 import rebuild
from mbtiles import canonicalize

def build(region):
    p=profile(region);bounds=p['coastContextBounds'];dest=ROOT/'build'/(region+'-coast-context');dest.mkdir(exist_ok=False)
    active=active_map(region);old=active['datasets']['topography'];coast=json.loads((ROOT/'coast-sources.lock.json').read_text())
    if digest(ROOT/coast['path'])!=coast['sha256'] or digest(ROOT/old['path'])!=old['sha256']:raise ValueError('Source changed')
    tools=json.loads((ROOT/'topography-toolchain.lock.json').read_text())
    env=os.environ.copy();env['PROJ_DATA']=str(Path(tools['proj_database']['path']).parent);env['GDAL_DATA']='/Applications/QGIS.app/Contents/Resources/qgis/gdal'
    ogr=tools['ogr2ogr']['path'];tilemaker=tools['tilemaker']['path']
    for name in ('ogr2ogr','tilemaker'):
        if digest(tools[name]['path'])!=tools[name]['sha256']:raise ValueError('Tool changed')
    source='/vsizip/'+str(ROOT/coast['path'])+'/land-polygons-split-4326/land_polygons.shp'
    subprocess.run([ogr,'-f','GeoJSON',str(dest/'land.geojson'),source,'-spat',*map(str,bounds),'-clipsrc',*map(str,bounds),'-lco','COORDINATE_PRECISION=7'],env=env,check=True)
    config={'layers':{'land':{'minzoom':4,'maxzoom':12,'source':str(dest/'land.geojson'),'simplify_below':12,'simplify_level':.00003,'simplify_ratio':2}},'settings':{'minzoom':4,'maxzoom':12,'basezoom':12,'bounding_box':bounds,'include_ids':False,'compress':'gzip','name':p['name']+' coastal context','description':'Coastal background beyond edition coverage; source OSM land polygons','version':p['mapVersion']}}
    write(dest/'tilemaker.json',config);(dest/'process.lua').write_text('node_keys={}\nway_keys={}\nfunction node_function() end\nfunction way_function() end\n')
    with (dest/'tilemaker.log').open('w') as log:subprocess.run([tilemaker,'--output',str(dest/'coast.mbtiles'),'--config',str(dest/'tilemaker.json'),'--process',str(dest/'process.lua'),'--threads','1'],stdout=log,stderr=subprocess.STDOUT,check=True)
    replacement=rebuild(ROOT/old['path'],dest/'combined.mbtiles',dest/'coast.mbtiles','land')
    with closing(sqlite3.connect(dest/'combined.mbtiles')) as db:
        for name,value in [('bounds',','.join(map(str,bounds))),('openbaremap_storage_revision','2.0.0-england-wales-r2')]:
            db.execute('DELETE FROM metadata WHERE name=?',(name,));db.execute('INSERT INTO metadata VALUES (?,?)',(name,value))
        db.commit()
    output=ROOT/'releases'/region/p['mapVersion']/'maps/topography-context.mbtiles';canonicalize(dest/'combined.mbtiles',output)
    record={'path':str(output.relative_to(ROOT)),'sha256':digest(output),'bytes':output.stat().st_size,'validation':inspect_tiles(output)}
    release=output.parent.parent
    write(release/'initial-active-map.json',active)
    active['datasets']['topography']=record;active['storageRevision']='2.0.0-england-wales-r2'
    write(region_path(region,'active-map.json'),active);write(region_path(region,'style.json'),region_style(region))
    write(release/'coast-context-report.json',{'source':coast,'contextBounds':bounds,'oldTopography':old,'replacement':replacement,'output':record,'builderSHA256':digest(Path(__file__)),'note':'Contour payloads preserved exactly while extending land background outside edition coverage.'})
    print('Coastal context extended; contour layer payloads preserved.',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--region',choices=['england-wales'],required=True);args=parser.parse_args();build(args.region)
