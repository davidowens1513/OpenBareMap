#!/usr/bin/env python3
"""Validate the complete native map set and assemble its public release metadata."""
from pathlib import Path
import json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'garmin')]
from openbaremap import digest,write
from regions import garmin_work,region_path
from build import java_path
from build_distribution_instructions import build as instructions
TITLES={'ireland':'Ireland','england-wales':'England-Wales','scotland':'Scotland','sierra-nevada':'Sierra-Nevada'}
REV='2.0.0-hiking-r1'
def record(path):return {'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':digest(path)}
def main():
 dest=ROOT/'garmin/releases'/REV;dest.mkdir(parents=True,exist_ok=True)
 records={r:json.loads((garmin_work(r)/'hiking-r1/release.json').read_text()) for r in TITLES}
 images=[Path(x['output']['path']) for x in records.values()]
 for region,image in zip(TITLES,images):assert digest(image)==records[region]['output']['sha256']
 jar=ROOT/'garmin/tools/mkgmap-r4924/mkgmap.jar';java=Path(java_path());classes=ROOT/'work/hiking-release-validation';classes.mkdir(exist_ok=True);subprocess.run([str(java.with_name('javac')),'-cp',str(jar),'-d',str(classes),str(ROOT/'garmin/ValidateMapSet.java')],check=True)
 companions=[ROOT/'garmin/dist/OpenBareMap-My-Tracks.img'];companions=[p for p in companions if p.exists()]
 with (dest/'map-set-validation.txt').open('w') as out:subprocess.run([str(java),'-Djava.awt.headless=true',*['-Dopenbaremap.tiles.'+str(x['familyId'])+'='+str(x['inspection']['tiles']) for x in records.values()],'-Xmx2g','-cp',str(classes)+':'+str(jar),'ValidateMapSet',*map(str,images+companions)],stdout=out,check=True)
 manifest={'format':'openbaremap-garmin-release-v1','mapVersion':'2.0.0','releaseDate':'2026-11-02','garminPackageRevision':REV,'nativeLevels':[24,23,22,20,18,16],'hikingLineResolution':24,'hikingLineWidthPixels':4,'lineColours':{'path':'#269e3f','track':'#654321','walkingRoute':'#d13d2c'},'whiteBacking':False,'buildingResolution':24,'fineContourResolution':23,'routing':False,'regions':{},'validation':record(dest/'map-set-validation.txt')}
 for region,source in zip(TITLES,images):
  base=ROOT/'garmin' if region=='ireland' else ROOT/'regions'/region/'garmin';image=base/'dist'/('OpenBareMap-'+TITLES[region]+'.img');tmp=image.with_suffix('.img.next');shutil.copyfile(source,tmp);assert digest(tmp)==records[region]['output']['sha256'];tmp.replace(image)
  for name in ['inspection.json','hiking-validation.txt']:
   shutil.copyfile(garmin_work(region)/'hiking-r1'/name,base/name)
  build=records[region];build.update(routing=False,contourIntervalMetres=20);build['output']=record(image);write(base/'build-report.json',build)
  shutil.copyfile(base/'config.json',dest/(region+'-config.json'));shutil.copyfile(base/'hiking-validation.txt',dest/(region+'-hiking-validation.txt'))
  filename=image.name;manifest['regions'][region]={**record(image),'familyId':build['familyId'],'tileCount':build['inspection']['tiles'],'downloadURL':'https://downloads.appsbyonzy.dev/Garmin/'+filename+'?v='+REV,'instructionsURL':'https://downloads.appsbyonzy.dev/Garmin/'+('instructions.txt' if region=='ireland' else region+'-instructions.txt'),'sourceLockSHA256':digest(region_path(region,'sources.lock.json')),'terrainLockSHA256':digest(region_path(region,'terrain-sources.lock.json')),'garminInputsLockSHA256':digest(base/'inputs.lock.json'),'demPaddingLockSHA256':digest(base/'dem-padding.lock.json'),'buildReport':record(base/'build-report.json')}
  if region!='ireland':
   mp=ROOT/'releases'/region/'2.0.0/manifest.json';data=json.loads(mp.read_text());data['garmin']=record(image);data['garminPackageRevision']=REV;write(mp,data)
   vp=mp.with_name('validation.json');validation=json.loads(vp.read_text());validation['garmin']=build;validation['garminMapSetValidation']=record(dest/'map-set-validation.txt');validation['irelandGarminPackageRevision']=REV;write(vp,validation)
 instructions()
 for region in TITLES:
  base=ROOT/'garmin' if region=='ireland' else ROOT/'regions'/region/'garmin';folder=base/'dist';sums=folder/'SHA256SUMS.txt'
  names=[x.split('  ',1)[1] for x in sums.read_text().splitlines()] if sums.exists() else ['OpenBareMap-'+TITLES[region]+'.img','INSTALL.txt','ATTRIBUTION.txt']
  sums.write_text(''.join(digest(folder/n)+'  '+n+'\n' for n in names))
  mp=ROOT/'distribution/app-bundles-v1/garmin'/region/'manifest.json';data=json.loads(mp.read_text());data['garminPackageRevision']=REV;data['downloadURL']=manifest['regions'][region]['downloadURL'];write(mp,data)
 write(dest/'manifest.json',manifest)
 # Refresh current Garmin records in Ireland's aggregate manifest; historical entries remain historical.
 mp=ROOT/'releases/2.0.0/manifest.json';data=json.loads(mp.read_text());g=data['platforms']['garmin'];g['map']=record(ROOT/'garmin/dist/OpenBareMap-Ireland.img');g['validation']=record(ROOT/'garmin/build-report.json');g['garminPackageRevision']=REV
 data['profiles']['garmin']=record(ROOT/'garmin/config.json');data['profiles']['garminStyle']={p.name:digest(p) for p in (ROOT/'garmin/style').iterdir() if p.is_file()};data['legends']['garmin']=record(ROOT/'garmin/dist/Montana-750i-Legend.png')
 for entry in data.get('sourceRecords',[]):
  if entry.get('path') in ['garmin/generate_typ.py','garmin/cartography.json']:entry.update(record(ROOT/entry['path']))
 data['platformRevisions']['garmin']={'revision':REV,'scope':'Equal 4-pixel paths, tracks and walking routes at shared resolution 24; buildings at 24 and fine contours retained at 23; six native levels','releaseManifest':record(dest/'manifest.json'),'routing':False}
 data['validation']['garminHikingProfile']={'structuralInspectionPassed':True,'hikingVisibilityCheckedInEveryCompiledSection':True,'completeMapSetChecked':True,'hardwareVisualReview':'Depends on Garmin settings; device file verification recorded separately'};write(mp,data)
 staging=ROOT/'work/garmin-public-release';staging.mkdir(exist_ok=False)
 for region,title in TITLES.items():
  base=ROOT/'garmin' if region=='ireland' else ROOT/'regions'/region/'garmin';folder=base/'dist';name='OpenBareMap-'+title+'.img';os.link(folder/name,staging/name)
  shutil.copyfile(folder/'INSTALL.txt',staging/('instructions.txt' if region=='ireland' else region+'-instructions.txt'));(staging/(region+'-SHA256SUMS.txt')).write_text(digest(folder/name)+'  '+name+'\n')
  target=staging/region;target.mkdir()
  source=ROOT/'distribution/app-bundles-v1/garmin'/region
  for file in source.iterdir():
   if file.is_file():shutil.copyfile(file,target/file.name)
 shutil.copyfile(dest/'manifest.json',staging/'release-manifest.json');shutil.copyfile(ROOT/'garmin/dist/Montana-750i-Legend.png',staging/'ireland/legend.png')
 print('COMPLETE GARMIN RELEASE VALIDATED AND ASSEMBLED',flush=True)
if __name__=='__main__':main()
