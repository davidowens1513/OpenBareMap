#!/usr/bin/env python3
"""Assemble and verify a versioned MapLibre Native iOS resource bundle."""
import argparse,hashlib,json,plistlib,shutil,sqlite3,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT/"scripts"))
from package_resources import build_capped_coast, copy_map_file
from regions import profile, active_map, region_style, provenance_files, region_path
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(path,obj):path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def assemble(destination, region='ireland'):
    edition=profile(region)
    if destination.exists():raise FileExistsError(destination)
    destination.mkdir(parents=True)
    bundle=destination/'OpenBareMap.bundle';bundle.mkdir()
    (bundle/'maps').mkdir()
    active=active_map(region);source_files={};records={}
    for name,item in active['datasets'].items():
        src=ROOT/item['path']
        if sha(src)!=item['sha256']:raise ValueError('Selected input changed: '+name)
        relative='maps/'+name+'.mbtiles';dst=bundle/relative;copy_map_file(src,dst)
        if sha(dst)!=item['sha256']:raise ValueError('Copied database changed: '+name)
        records[name]={'path':relative,'sha256':item['sha256']}
        source_files[edition['gridSource'] if name=='grid' else name]=relative
    # A real capped source archive avoids relying on SDK-specific TileJSON overrides.
    top=bundle/'maps/topography.mbtiles';coast=bundle/'maps/coast.mbtiles'
    build_capped_coast(top, coast)
    source_files['coast']='maps/coast.mbtiles';records['coast']={'path':'maps/coast.mbtiles','sha256':sha(coast),'derived_from':active['datasets']['topography']['sha256'],'maxzoom':12,'operation':'Preserve land-layer MVT bytes only through zoom 12; omit other layers.'}
    for source,target in [('viewer/fonts','fonts'),('viewer/sprites','sprites'),('app-legend' if region=='ireland' else 'regions/'+region+'/legend','legend')]:shutil.copytree(ROOT/source,bundle/target)
    if edition['townlands']:shutil.copyfile(ROOT/'viewer/townlands.geojson',bundle/'townlands.geojson')
    shutil.copyfile(ROOT/'viewer/terrain-attribution.html',bundle/'terrain-attribution.html')
    (bundle/'provenance').mkdir()
    for source in provenance_files(region):
        shutil.copyfile(source,bundle/'provenance'/source.name)
    shutil.copyfile(ROOT/'regions'/region/'region.json',bundle/'provenance/region.json')
    for name in ['terrain-attribution.md','terrain-data-sources.md']:
        shutil.copyfile(ROOT/'data'/name,bundle/'provenance'/name)
    style=region_style(region)
    for name,path in source_files.items():
        source=style['sources'][name];source.pop('tiles',None);source['url']='mbtiles://{bundle}/'+path
    if edition['townlands']:style['sources']['townlands']['data']='{bundle}/townlands.geojson'
    style['sources']['basemap']['attribution']='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
    style['sources']['hillshade']['attribution']='Terrain Tiles / Mapzen · Copernicus EU-DEM · USGS · NOAA'
    style['glyphs']='{bundle}/fonts/{fontstack}/{range}.pbf';style['sprite']='{bundle}/sprites/outdoors'
    write(bundle/'style.json',style)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    write(bundle/'manifest.json',{'packageFormat':'openbaremap-ios-resources-v1','mapVersion':active.get('mapVersion','2.0.0'),'region':region,'displayName':edition['label'],'bounds':edition['bounds'],'coverage':edition.get('coverage',edition['label']),'storageRevision':active.get('storageRevision','original'),'styleRevision':active.get('styleRevision','shared'),'regionStyleSHA256':sha(region_path(region,'style.json')) if region!='ireland' else sha(ROOT/'style/openbaremap.json'),'cartography':'OpenBareMap 2.0; '+str(active.get('contourIntervalMetres',10))+' m contours','sourceCommit':commit,'packagerSHA256':sha(Path(__file__)),'sourceRevisionNote':'Base repository commit; resource/style checksums and storageRevision identify this package.','sourceStyleSHA256':sha(ROOT/'style/openbaremap.json'),'renderer':'MapLibre Native iOS','style':'style.json','requiresRuntimePathResolution':True,'loader':'OpenBareMapResources.swift (provided alongside bundle)','loaderSHA256':sha(ROOT/'ios/OpenBareMapResources.swift'),'sourceFiles':source_files,'datasets':records,'contourIntervalMetres':active.get('contourIntervalMetres',10),'osmSnapshot':json.loads(region_path(region,'sources.lock.json').read_text())['osm']['snapshot_date'],'inheritedAssets':('Townlands, Irish Grid, font glyphs and original patterns are pinned 1.1 assets.' if edition['townlands'] else f"Font glyphs and original patterns are pinned 1.1 assets; {edition['gridName']} is generated from {edition['gridCRS']}."),'validation':'Resource integrity and loader tests; actual iOS device rendering remains to be verified.'})
    info={'CFBundleIdentifier':'org.openbaremap.resources' if region=='ireland' else 'org.openbaremap.resources.'+region,'CFBundleName':'OpenBareMap','CFBundleDisplayName':'OpenBareMap','CFBundlePackageType':'BNDL','CFBundleShortVersionString':active.get('mapVersion','2.0.0'),'CFBundleVersion':'1','CFBundleDevelopmentRegion':'en','CFBundleInfoDictionaryVersion':'6.0'}
    (bundle/'Info.plist').write_bytes(plistlib.dumps(info,sort_keys=True))
    (bundle/'ATTRIBUTION.txt').write_text('OpenBareMap\n\n© OpenStreetMap contributors. OSM-derived databases are distributed under ODbL 1.0.\nhttps://www.openstreetmap.org/copyright\nhttps://opendatacommons.org/licenses/odbl/1-0/\n\nElevation: Terrain Tiles / Mapzen composite data, including Copernicus EU-DEM, USGS and NOAA. See terrain-attribution.html and provenance/terrain-data-sources.md for full source notices. This rebuild is not claimed to use pure SRTM.\n\nOpen Sans glyphs: Apache License 2.0; see fonts/LICENSE-APACHE-2.0.txt.\nMap colours and custom pattern assets: OpenBareMap.\nTownland label points and fixed Irish Grid are inherited from OpenBareMap 1.1; source dates/generation recipes are not newly asserted.\n\nThe host app must make these attributions accessible to users.\n')
    if not edition['townlands']:
        notice=bundle/'ATTRIBUTION.txt'
        notice.write_text(notice.read_text().replace('Townland label points and fixed Irish Grid are inherited from OpenBareMap 1.1; source dates/generation recipes are not newly asserted.', f"{edition['gridName']} generated using {edition['gridCRS']}; font glyphs and original patterns inherited from OpenBareMap 1.1.").replace('Townlands and Irish Grid inherited from OpenBareMap 1.1; see provenance.', f"{edition['gridName']} generated using {edition['gridCRS']}; see provenance."))
    if edition.get('coverageBoundary'):
        notice=bundle/'ATTRIBUTION.txt'
        notice.write_text(notice.read_text()+'\nNational park boundary: Fuente: Organismo Autónomo Parques Nacionales (MITECO/OAPN), CC BY 4.0. Boundary source and calculated 25 km buffer: see provenance/boundary-source.json.\n')
    shutil.copyfile(ROOT/'ios/OpenBareMapResources.swift',destination/'OpenBareMapResources.swift')
    shutil.copyfile(ROOT/'ios/INTEGRATION.txt',destination/'INTEGRATION.txt');shutil.copyfile(ROOT/'ios/INTEGRATION.txt',bundle/'INTEGRATION.txt')
    if region != 'ireland':
        for file in [destination/'INTEGRATION.txt',bundle/'INTEGRATION.txt']:
            file.write_text(file.read_text().replace('Start around longitude -8.15, latitude 53.4, zoom 7. The map is designed for full-island coverage.', f"Use the region bounds in manifest.json, or longitude {edition['destinations']['island'][0]}, latitude {edition['destinations']['island'][1]}, zoom {edition['destinations']['island'][2]}, for {edition['name']}."))
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
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);parser.add_argument('--region',choices=['ireland','england-wales','scotland','sierra-nevada','pyrenees'],default='ireland');args=parser.parse_args();assemble((args.output or (ROOT/'ios/package' if args.region=='ireland' else ROOT/'regions'/args.region/'ios')).resolve(),args.region)
