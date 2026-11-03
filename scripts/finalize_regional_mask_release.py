#!/usr/bin/env python3
"""Validate and promote the four Garmin maps with bounded regional backgrounds."""
import json,shutil,subprocess
from pathlib import Path
from openbaremap import ROOT,digest,write
from package_resources import copy_map_file
from regions import garmin_work,profile,region_path
from build_distribution_instructions import build as instructions

REV='2.0.1-regional-mask-r1'
TITLES={'ireland':'Ireland','england-wales':'England-Wales','scotland':'Scotland','sierra-nevada':'Sierra-Nevada'}
def record(path):return {'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':digest(path)}
def main():
    dest=ROOT/'garmin/releases'/REV;dest.mkdir(parents=True,exist_ok=True)
    staging=Path('/private/tmp/OpenBareMap-regional-mask/Garmin');staging.mkdir(parents=True,exist_ok=True)
    java=Path('/opt/homebrew/opt/openjdk@21/bin/java');jar=ROOT/'garmin/tools/mkgmap-r4924/mkgmap.jar'
    classes=staging.parent/'validation-classes';classes.mkdir(exist_ok=True)
    subprocess.run([str(java.with_name('javac')),'-cp',str(jar),'-d',str(classes),str(ROOT/'garmin/ValidateMapSet.java'),str(ROOT/'garmin/CheckRegionalBackgrounds.java')],check=True)
    records={}
    for region,title in TITLES.items():
        base=ROOT/'garmin' if region=='ireland' else ROOT/'regions'/region/'garmin'
        build=garmin_work(region)/REV;report=json.loads((build/'release.json').read_text());source=build/'gmapsupp.img'
        assert report['region']==region and report['garminPackageRevision']==REV
        assert report['transparent'] and report['drawPriority']==25
        assert report['inspection']['subfileBytes'].get('DEM',0)>0,'Native elevation data missing'
        assert not report['inspection']['routing'],'Unexpected routing network'
        assert report['renderFootprintSHA256']==digest(base/'render-coverage.geojson')
        assert report['configSHA256']==digest(base/'config.json')
        assert report['styleSHA256']=={p.name:digest(p) for p in (base/'style').iterdir() if p.is_file()}
        assert digest(source)==report['output']['sha256']
        with (dest/(region+'-background-validation.txt')).open('w') as out:
            subprocess.run([str(java),'-Xmx2g','-cp',str(classes)+':'+str(jar),'CheckRegionalBackgrounds',region,str(source)],stdout=out,check=True)
        records[region]={'base':base,'build':build,'report':report,'source':source}
    companions=[p for p in [ROOT/'garmin/dist/OpenBareMap-My-Tracks.img'] if p.exists()]
    with (dest/'map-set-validation.txt').open('w') as out:
        subprocess.run([str(java),'-Djava.awt.headless=true',*['-Dopenbaremap.tiles.'+str(x['report']['familyId'])+'='+str(x['report']['inspection']['tiles']) for x in records.values()],'-Xmx2g','-cp',str(classes)+':'+str(jar),'ValidateMapSet',*[str(x['source']) for x in records.values()],*map(str,companions)],stdout=out,check=True)
    manifest={'format':'openbaremap-garmin-release-v1','releaseDate':'2026-11-03','garminPackageRevision':REV,'collectionRevision':REV,'nativeLevels':[24,23,22,20,18,16],'hikingLineResolution':24,'hikingLineWidthPixels':4,'lineColours':{'path':'#269e3f','track':'#654321','walkingRoute':'#d13d2c'},'whiteBacking':False,'buildingResolution':24,'fineContourResolution':23,'routing':False,'transparent':True,'drawPriority':25,'regionalBackgrounds':'Clipped to locked source footprints; no automatic rectangular filler','regions':{},'validation':record(dest/'map-set-validation.txt')}
    for region,x in records.items():
        base=x['base'];build=x['build'];report=x['report'];image=base/'dist'/('OpenBareMap-'+TITLES[region]+'.img')
        pending=image.with_suffix('.next')
        if not pending.exists():copy_map_file(x['source'],pending)
        assert digest(pending)==report['output']['sha256'];pending.replace(image)
        for name in ['inspection.json','hiking-validation.txt']:shutil.copyfile(build/name,base/name)
        report['output']=record(image);report['nativeElevation']=True;write(base/'build-report.json',report)
        archive=dest/region;archive.mkdir(exist_ok=True)
        for name in ['config.json','render-coverage.geojson','render-coverage.lock.json']:shutil.copyfile(base/name,archive/name)
        for name in ['release.json','build.json','inspection.json','hiking-validation.txt','tiles.args']:shutil.copyfile(build/name,archive/name)
        shutil.copyfile(garmin_work(region)/'prepared.json',archive/'prepared.json')
        url='https://downloads.appsbyonzy.dev/Garmin/'+image.name+'?v='+REV
        manifest['regions'][region]={**record(image),'mapVersion':profile(region)['mapVersion'],'garminPackageRevision':REV,'familyId':report['familyId'],'tileCount':report['inspection']['tiles'],'downloadURL':url,'instructionsURL':'https://downloads.appsbyonzy.dev/Garmin/'+('instructions.txt' if region=='ireland' else region+'-instructions.txt'),'buildReport':record(base/'build-report.json'),'sourceLockSHA256':digest(region_path(region,'sources.lock.json')),'terrainLockSHA256':digest(region_path(region,'terrain-sources.lock.json')),'renderFootprint':record(base/'render-coverage.geojson'),'renderFootprintLock':record(base/'render-coverage.lock.json'),'backgroundValidation':record(dest/(region+'-background-validation.txt'))}
    write(dest/'manifest.json',manifest)
    instructions()
    for region,x in records.items():
        base=x['base'];image=base/'dist'/('OpenBareMap-'+TITLES[region]+'.img');folder=image.parent
        sums=folder/'SHA256SUMS.txt';names=[line.split('  ',1)[1] for line in sums.read_text().splitlines()]
        sums.write_text(''.join(digest(folder/name)+'  '+name+'\n' for name in names))
        mp=ROOT/'distribution/app-bundles-v1/garmin'/region/'manifest.json';m=json.loads(mp.read_text());m.update(garminPackageRevision=REV,downloadURL=manifest['regions'][region]['downloadURL']);write(mp,m)
        target=staging/image.name
        if not target.exists():copy_map_file(image,target)
        assert digest(target)==digest(image),'Staging contains a different release'
        shutil.copyfile(folder/'INSTALL.txt',staging/('instructions.txt' if region=='ireland' else region+'-instructions.txt'))
        (staging/(region+'-SHA256SUMS.txt')).write_text(digest(image)+'  '+image.name+'\n')
        shutil.copytree(mp.parent,staging/region,dirs_exist_ok=True)
        if region!='ireland':
            release=ROOT/'releases'/region/profile(region)['mapVersion'];path=release/'manifest.json';m=json.loads(path.read_text());m.update(garmin=record(image),garminPackageRevision=REV);write(path,m)
            path=release/'validation.json';v=json.loads(path.read_text());v.update(garmin=x['report'],garminMapSetValidation=record(dest/'map-set-validation.txt'),irelandGarminPackageRevision=REV);write(path,v)
    path=ROOT/'releases/2.0.0/manifest.json';m=json.loads(path.read_text());g=m['platforms']['garmin'];g.update(map=record(ROOT/'garmin/dist/OpenBareMap-Ireland.img'),validation=record(ROOT/'garmin/build-report.json'),garminPackageRevision=REV)
    m['profiles']['garmin']=record(ROOT/'garmin/config.json');m['profiles']['garminStyle']={p.name:digest(p) for p in (ROOT/'garmin/style').iterdir() if p.is_file()}
    m['platformRevisions']['garmin']={'revision':REV,'scope':'Regional backgrounds confined to locked drawing footprints; six native levels, 4-pixel hiking lines at resolution24, buildings24, fine contours23','releaseManifest':record(dest/'manifest.json'),'routing':False}
    write(path,m);shutil.copyfile(dest/'manifest.json',staging/'release-manifest.json')
    print('All four regional Garmin maps validated, promoted and staged:',staging,flush=True)
if __name__=='__main__':main()
