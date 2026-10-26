#!/usr/bin/env python3
"""Assemble and verify a versioned MapLibre Native iOS resource bundle."""
import argparse,hashlib,json,plistlib,shutil,sqlite3,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(path,obj):path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def assemble(destination):
    if destination.exists():raise FileExistsError(destination)
    destination.mkdir(parents=True)
    bundle=destination/'OpenBareMap.bundle';bundle.mkdir()
    (bundle/'maps').mkdir()
    active=json.loads((ROOT/'active-map.json').read_text());source_files={};records={}
    for name,item in active['datasets'].items():
        src=ROOT/item['path']
        if sha(src)!=item['sha256']:raise ValueError('Selected input changed: '+name)
        relative='maps/'+name+'.mbtiles';dst=bundle/relative;shutil.copyfile(src,dst)
        if sha(dst)!=item['sha256']:raise ValueError('Copied database changed: '+name)
        records[name]={'path':relative,'sha256':item['sha256']}
        source_files['irish-grid' if name=='grid' else name]=relative
    # A real capped source archive avoids relying on SDK-specific TileJSON overrides.
    top=bundle/'maps/topography.mbtiles';coast=bundle/'maps/coast.mbtiles'
    src=sqlite3.connect(top.as_uri()+'?mode=ro',uri=True);dst=sqlite3.connect(coast)
    metadata=dict(src.execute('SELECT name,value FROM metadata'));metadata['maxzoom']='12';metadata['name']='OpenBareMap capped coast source';metadata['description']='Unchanged topography tile payloads through zoom 12, packaged for coastline overzoom'
    schema=json.loads(metadata['json'])
    for layer in schema['vector_layers']:layer['maxzoom']=min(12,layer['maxzoom'])
    metadata['json']=json.dumps(schema,separators=(',',':'))
    dst.execute('CREATE TABLE metadata (name TEXT NOT NULL,value TEXT)')
    dst.execute('CREATE TABLE tiles (zoom_level INTEGER NOT NULL,tile_column INTEGER NOT NULL,tile_row INTEGER NOT NULL,tile_data BLOB NOT NULL,PRIMARY KEY(zoom_level,tile_column,tile_row))')
    dst.executemany('INSERT INTO metadata VALUES (?,?)',sorted(metadata.items()))
    dst.executemany('INSERT INTO tiles VALUES (?,?,?,?)',src.execute('SELECT zoom_level,tile_column,tile_row,tile_data FROM tiles WHERE zoom_level<=12 ORDER BY zoom_level,tile_column,tile_row'));dst.commit();dst.close();src.close()
    source_files['coast']='maps/coast.mbtiles';records['coast']={'path':'maps/coast.mbtiles','sha256':sha(coast),'derived_from':active['datasets']['topography']['sha256'],'maxzoom':12,'operation':'Copy unchanged coordinate-sorted tile payloads through zoom 12; update source metadata maxzoom.'}
    for source,target in [('viewer/fonts','fonts'),('viewer/sprites','sprites'),('app-legend','legend')]:shutil.copytree(ROOT/source,bundle/target)
    shutil.copyfile(ROOT/'viewer/townlands.geojson',bundle/'townlands.geojson')
    shutil.copyfile(ROOT/'viewer/terrain-attribution.html',bundle/'terrain-attribution.html')
    (bundle/'provenance').mkdir()
    for name in ['active-map.json','sources.lock.json','coast-sources.lock.json','terrain-sources.lock.json','legacy-assets.lock.json','viewer-assets.lock.json','assets/sprites.lock.json','config/transport-style.json']:
        shutil.copyfile(ROOT/name,bundle/'provenance'/Path(name).name)
    for name in ['terrain-attribution.md','terrain-data-sources.md']:
        shutil.copyfile(ROOT/'data'/name,bundle/'provenance'/name)
    style=json.loads((ROOT/'style/openbaremap.json').read_text())
    for name,path in source_files.items():
        source=style['sources'][name];source.pop('tiles',None);source['url']='mbtiles://{bundle}/'+path
    style['sources']['townlands']['data']='{bundle}/townlands.geojson'
    style['sources']['basemap']['attribution']='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
    style['sources']['hillshade']['attribution']='Terrain Tiles / Mapzen · Copernicus EU-DEM · USGS · NOAA'
    style['glyphs']='{bundle}/fonts/{fontstack}/{range}.pbf';style['sprite']='{bundle}/sprites/outdoors'
    write(bundle/'style.json',style)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    write(bundle/'manifest.json',{'packageFormat':'openbaremap-ios-resources-v1','mapVersion':'0.4.0','cartography':'OpenBareMap 1.1 with current adjustments and 10 m contours','sourceCommit':commit,'sourceStyleSHA256':sha(ROOT/'style/openbaremap.json'),'renderer':'MapLibre Native iOS','style':'style.json','requiresRuntimePathResolution':True,'loader':'OpenBareMapResources.swift (provided alongside bundle)','sourceFiles':source_files,'datasets':records,'contourIntervalMetres':10,'osmSnapshot':'2026-10-24','inheritedAssets':'Townlands, Irish Grid, font glyphs and original patterns are pinned 1.1 assets; see provenance/legacy-assets.lock.json','validation':'Resource integrity and loader tests; actual iOS device rendering remains to be verified.'})
    info={'CFBundleIdentifier':'org.openbaremap.resources','CFBundleName':'OpenBareMap','CFBundleDisplayName':'OpenBareMap','CFBundlePackageType':'BNDL','CFBundleShortVersionString':'0.4.0','CFBundleVersion':'1','CFBundleDevelopmentRegion':'en','CFBundleInfoDictionaryVersion':'6.0'}
    (bundle/'Info.plist').write_bytes(plistlib.dumps(info,sort_keys=True))
    (bundle/'ATTRIBUTION.txt').write_text('OpenBareMap\n\n© OpenStreetMap contributors. OSM-derived databases are distributed under ODbL 1.0.\nhttps://www.openstreetmap.org/copyright\nhttps://opendatacommons.org/licenses/odbl/1-0/\n\nElevation: Terrain Tiles / Mapzen composite data, including Copernicus EU-DEM, USGS and NOAA. See terrain-attribution.html and provenance/terrain-data-sources.md for full source notices. This rebuild is not claimed to use pure SRTM.\n\nOpen Sans glyphs: Apache License 2.0; see fonts/LICENSE-APACHE-2.0.txt.\nMap colours and custom pattern assets: OpenBareMap.\nTownland label points and fixed Irish Grid are inherited from OpenBareMap 1.1; source dates/generation recipes are not newly asserted.\n\nThe host app must make these attributions accessible to users.\n')
    shutil.copyfile(ROOT/'ios/OpenBareMapResources.swift',destination/'OpenBareMapResources.swift')
    shutil.copyfile(ROOT/'ios/INTEGRATION.txt',destination/'INTEGRATION.txt');shutil.copyfile(ROOT/'ios/INTEGRATION.txt',bundle/'INTEGRATION.txt')
    inventory=[]
    for p in sorted(bundle.rglob('*')):
        if p.is_file():inventory.append({'path':str(p.relative_to(bundle)),'bytes':p.stat().st_size,'sha256':sha(p)})
    write(bundle/'resource-inventory.json',{'files':inventory})
    all_files=sorted(p for p in bundle.rglob('*') if p.is_file())
    (bundle/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+str(p.relative_to(bundle))+'\n' for p in all_files))
    validation={'checksums':True,'databases':{},'styleSourceFiles':True,'fontRanges':True,'spriteReferences':True,'nativeDeviceRenderTested':False}
    for name,relative in source_files.items():
        db=sqlite3.connect((bundle/relative).as_uri()+'?mode=ro',uri=True)
        integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
        if integrity!='ok':raise ValueError(name+': '+integrity)
        bounds=db.execute('SELECT MIN(zoom_level),MAX(zoom_level),COUNT(*) FROM tiles').fetchone();db.close()
        validation['databases'][name]={'integrity':integrity,'minzoom':bounds[0],'maxzoom':bounds[1],'tiles':bounds[2]}
    for item in inventory:
        if sha(bundle/item['path'])!=item['sha256']:raise ValueError('Final checksum mismatch')
    atlas=json.loads((bundle/'sprites/outdoors.json').read_text())
    for layer in style['layers']:
        for font in layer.get('layout',{}).get('text-font',[]):
            if not (bundle/'fonts'/font/'0-255.pbf').is_file():raise ValueError('Missing font: '+font)
        for key in ['fill-pattern','line-pattern']:
            pattern=layer.get('paint',{}).get(key)
            if isinstance(pattern,str) and pattern not in atlas:raise ValueError('Missing pattern: '+pattern)
    validation['totalBytes']=sum(p.stat().st_size for p in bundle.rglob('*') if p.is_file());validation['fileCount']=sum(1 for p in bundle.rglob('*') if p.is_file());write(destination/'validation.json',validation)
    print(json.dumps({'bundle':str(bundle),'bytes':validation['totalBytes'],'files':validation['fileCount']},indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'ios/package');args=parser.parse_args();assemble(args.output.resolve())
