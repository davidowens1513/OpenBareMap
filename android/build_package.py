#!/usr/bin/env python3
"""Package the current shared map resources for offline MapLibre Android use."""
from pathlib import Path
import argparse,hashlib,json,shutil,sqlite3,sys,zipfile,subprocess
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from package_resources import build_capped_coast

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def assemble(output):
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True);package=output/'OpenBareMap';package.mkdir();(package/'maps').mkdir()
    active=json.loads((ROOT/'active-map.json').read_text());files={};databases={}
    for name,item in active['datasets'].items():
        src=ROOT/item['path'];relative=f'maps/{name}.mbtiles'
        if sha(src)!=item['sha256']:raise ValueError('Selected map changed: '+name)
        dst=package/relative;shutil.copyfile(src,dst)
        if sha(dst)!=item['sha256']:raise ValueError('Copied map differs: '+name)
        files['irish-grid' if name=='grid' else name]=relative
        databases[name]={'path':relative,'sha256':sha(dst)}
    build_capped_coast(package/'maps/topography.mbtiles',package/'maps/coast.mbtiles');files['coast']='maps/coast.mbtiles';databases['coast']={'path':'maps/coast.mbtiles','sha256':sha(package/'maps/coast.mbtiles'),'derivedFrom':active['datasets']['topography']['sha256']}
    for src,target in [('viewer/fonts','fonts'),('viewer/sprites','sprites'),('app-legend','legend')]:shutil.copytree(ROOT/src,package/target)
    shutil.copyfile(ROOT/'viewer/townlands.geojson',package/'townlands.geojson')
    shutil.copyfile(ROOT/'viewer/terrain-attribution.html',package/'terrain-attribution.html')
    (package/'provenance').mkdir()
    for name in ['active-map.json','sources.lock.json','coast-sources.lock.json','terrain-sources.lock.json','legacy-assets.lock.json','viewer-assets.lock.json','assets/sprites.lock.json']:
        shutil.copyfile(ROOT/name,package/'provenance'/Path(name).name)
    for name in ['terrain-attribution.md','terrain-data-sources.md']:shutil.copyfile(ROOT/'data'/name,package/'provenance'/name)
    style=json.loads((ROOT/'style/openbaremap.json').read_text())
    for name,path in files.items():
        source=style['sources'][name];source.pop('tiles',None);source['url']='mbtiles://{package}/'+path
    style['sources']['townlands']['data']='{package}/townlands.geojson';style['glyphs']='{package}/fonts/{fontstack}/{range}.pbf';style['sprite']='{package}/sprites/outdoors'
    style['sources']['basemap']['attribution']='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
    style['sources']['hillshade']['attribution']='Terrain Tiles / Mapzen · Copernicus EU-DEM · USGS · NOAA'
    write(package/'style.json',style)
    write(package/'manifest.json',{'packageFormat':'openbaremap-android-resources-v1','mapVersion':'2.0.0','storageRevision':active.get('storageRevision','original'),'sourceCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'sourceStyleSHA256':sha(ROOT/'style/openbaremap.json'),'renderer':'MapLibre Native Android','sourceFiles':files,'databases':databases,'contourIntervalMetres':active.get('contourIntervalMetres',10),'osmSnapshot':'2026-10-24','inheritedAssets':'Pinned OpenBareMap 1.1 townland points, fixed grid, glyphs and original patterns; see provenance.','requiresRuntimePathResolution':True})
    (package/'ATTRIBUTION.txt').write_text('OpenBareMap\n\n© OpenStreetMap contributors. OSM-derived databases: ODbL 1.0.\nhttps://www.openstreetmap.org/copyright\nhttps://opendatacommons.org/licenses/odbl/1-0/\n\nElevation: Terrain Tiles / Mapzen composite, including Copernicus EU-DEM, USGS and NOAA. See terrain-attribution.html and provenance/terrain-data-sources.md. Not claimed to use pure SRTM.\n\nOpen Sans glyphs: Apache License 2.0, see fonts/LICENSE-APACHE-2.0.txt.\nCustom style and pattern assets: OpenBareMap.\nTownlands and Irish Grid inherited from OpenBareMap 1.1; see provenance.\n\nMake full attribution accessible in the host app.\n')
    resources=sorted(p for p in package.rglob('*') if p.is_file())
    (package/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.relative_to(package).as_posix()+'\n' for p in resources))
    validation={'files':len(resources)+1,'databases':{},'androidDeviceRenderingTested':False}
    for name,path in files.items():
        db=sqlite3.connect((package/path).as_uri()+'?mode=ro',uri=True);integrity=db.execute('PRAGMA integrity_check').fetchone()[0];assert integrity=='ok';validation['databases'][name]={'integrity':integrity,'zooms':list(db.execute('SELECT MIN(zoom_level),MAX(zoom_level) FROM tiles').fetchone())};db.close()
    archive=export_zip(output)
    validation['zip']={'name':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive)};write(output/'validation.json',validation);print(json.dumps(validation,indent=2))
def export_zip(output):
    package=output/'OpenBareMap'
    for line in (package/'SHA256SUMS.txt').read_text().splitlines():
        digest,name=line.split('  ',1)
        path=(package/name).resolve()
        if not path.is_relative_to(package.resolve()) or sha(path)!=digest:raise ValueError('Package checksum mismatch: '+name)
    archive=output/'OpenBareMap-Android.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as z:
        for p in sorted(package.rglob('*')):
            if p.is_file():
                entry=zipfile.ZipInfo(p.relative_to(package).as_posix(),date_time=(2026,10,26,0,0,0));entry.external_attr=0o100644<<16;z.writestr(entry,b'') if p.stat().st_size==0 else None
                if p.stat().st_size:
                    with p.open('rb') as src,z.open(entry,'w',force_zip64=p.stat().st_size>=2**31) as dst:shutil.copyfileobj(src,dst,1024*1024)
    return archive
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'android/package');p.add_argument('--zip-only',action='store_true',help='Export ZIP from the existing checksum-verified package');args=p.parse_args();print(export_zip(args.output.resolve())) if args.zip_only else assemble(args.output.resolve())
