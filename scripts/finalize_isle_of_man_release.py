#!/usr/bin/env python3
"""Promote the island extension and validate it with the other accepted maps."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
from openbaremap import ROOT,digest,write
from package_resources import copy_map_file
from build_distribution_instructions import build as instructions
TITLES={'ireland':'Ireland','england-wales':'England-Wales','scotland':'Scotland','sierra-nevada':'Sierra-Nevada'}
REV='2.0.1-isle-of-man-r1'
def record(p):return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)}
def main(build):
 report=json.loads((build/'release.json').read_text());assert report['region']=='england-wales' and report['garminPackageRevision']==REV
 source=build/'gmapsupp.img';assert digest(source)==report['output']['sha256']
 base=ROOT/'regions/england-wales/garmin';image=base/'dist/OpenBareMap-England-Wales.img';pending=image.with_suffix('.next');copy_map_file(source,pending);assert digest(pending)==report['output']['sha256'];pending.replace(image)
 for name in ['inspection.json','hiking-validation.txt']:shutil.copyfile(build/name,base/name)
 report['output']=record(image);write(base/'build-report.json',report)
 dest=ROOT/'garmin/releases'/REV;dest.mkdir(parents=True,exist_ok=True);records={}
 for r,title in TITLES.items():
  b=ROOT/'garmin' if r=='ireland' else ROOT/'regions'/r/'garmin';j=json.loads((b/'build-report.json').read_text());p=b/'dist'/('OpenBareMap-'+title+'.img');assert digest(p)==j['output']['sha256'];records[r]={'image':p,'build':j,'base':b}
 java=Path('/opt/homebrew/opt/openjdk@21/bin/java');jar=ROOT/'garmin/tools/mkgmap-r4924/mkgmap.jar';classes=ROOT/'work/isle-of-man/validation-classes';classes.mkdir(exist_ok=True)
 subprocess.run([str(java.with_name('javac')),'-cp',str(jar),'-d',str(classes),str(ROOT/'garmin/ValidateMapSet.java')],check=True)
 companions=[ROOT/'garmin/dist/OpenBareMap-My-Tracks.img']
 companions=[p for p in companions if p.exists()]
 with (dest/'map-set-validation.txt').open('w') as f:
  subprocess.run([str(java),'-Djava.awt.headless=true',*['-Dopenbaremap.tiles.'+str(x['build']['familyId'])+'='+str(x['build']['inspection']['tiles']) for x in records.values()],'-Xmx2g','-cp',str(classes)+':'+str(jar),'ValidateMapSet',*[str(x['image']) for x in records.values()],*map(str,companions)],stdout=f,check=True)
 instructions()
 manifest={'format':'openbaremap-garmin-release-v1','releaseDate':'2026-11-02','collectionRevision':REV,'nativeLevels':[24,23,22,20,18,16],'hikingLineResolution':24,'hikingLineWidthPixels':4,'whiteBacking':False,'buildingResolution':24,'fineContourResolution':23,'routing':False,'regions':{},'validation':record(dest/'map-set-validation.txt')}
 staging=ROOT/'work/isle-of-man/garmin-public';staging.mkdir(exist_ok=True)
 for r,x in records.items():
  b=x['base'];img=x['image'];revision=x['build']['garminPackageRevision'];url='https://downloads.appsbyonzy.dev/Garmin/'+img.name+'?v='+revision
  manifest['regions'][r]={**record(img),'garminPackageRevision':revision,'familyId':x['build']['familyId'],'tileCount':x['build']['inspection']['tiles'],'downloadURL':url,'instructionsURL':'https://downloads.appsbyonzy.dev/Garmin/'+('instructions.txt' if r=='ireland' else r+'-instructions.txt'),'buildReport':record(b/'build-report.json'),'sourceLockSHA256':digest(ROOT/('sources.lock.json' if r=='ireland' else 'regions/'+r+'/sources.lock.json'))}
  mp=ROOT/'distribution/app-bundles-v1/garmin'/r/'manifest.json';m=json.loads(mp.read_text());m.update(garminPackageRevision=revision,downloadURL=url);write(mp,m)
  sums=b/'dist/SHA256SUMS.txt';names=[line.split('  ',1)[1] for line in sums.read_text().splitlines()];sums.write_text(''.join(digest(b/'dist'/n)+'  '+n+'\n' for n in names))
  shutil.copyfile(b/'dist/INSTALL.txt',staging/('instructions.txt' if r=='ireland' else r+'-instructions.txt'));(staging/(r+'-SHA256SUMS.txt')).write_text(digest(img)+'  '+img.name+'\n');shutil.copytree(mp.parent,staging/r,dirs_exist_ok=True)
 copy_map_file(image,staging/image.name);write(dest/'manifest.json',manifest);shutil.copyfile(dest/'manifest.json',staging/'release-manifest.json')
 recorddir=ROOT/'releases/england-wales/2.0.1/build-records/garmin';recorddir.mkdir(parents=True,exist_ok=True)
 for name in ['release.json','build.json','inspection.json','hiking-validation.txt','tiles.args']:shutil.copyfile(build/name,recorddir/name)
 print('Current four-map Garmin collection verified and England/Wales promoted.',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);main(p.parse_args().build.resolve())
