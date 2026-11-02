#!/usr/bin/env python3
"""Compile and inspect the shared native Garmin hiking profile from locked sources."""
import argparse,gzip,json,os,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'garmin'),str(ROOT/'work/python')]
from openbaremap import digest,write
from regions import profile,region_path,garmin_work
from build import java_path,tools,run
from identities import write_tile_args,validate_config
REVISION='2.0.0-hiking-r1'
def main(region):
 global REVISION
 p=profile(region);base=ROOT/'garmin' if region=='ireland' else ROOT/'regions'/region/'garmin';config=json.loads((base/'config.json').read_text());validate_config(region,config);REVISION=config['garminPackageRevision']
 work=garmin_work(region);coverage_polygon=base/('ireland.poly' if region=='ireland' else 'coverage.poly');out=work/('hiking-r1' if REVISION=='2.0.0-hiking-r1' else REVISION);out.mkdir(parents=True,exist_ok=True);tools()
 if (out/'release.json').exists():
  report=json.loads((out/'release.json').read_text());assert digest(out/'gmapsupp.img')==report['output']['sha256'];assert digest(base/'config.json')==report['configSHA256'];assert report['styleSHA256']=={f.name:digest(f) for f in (base/'style').iterdir() if f.is_file()};print('Verified completed build:',region,flush=True);return
 # Source locks must always match the complete local inputs.
 for lock in [region_path(region,'sources.lock.json'),region_path(region,'terrain-sources.lock.json'),base/'dem-padding.lock.json',base/'inputs.lock.json']:
  data=json.loads(lock.read_text())
  items=([data['osm']] if 'osm' in data else [])+data.get('assets',[])+data.get('inputs',[])
  for item in items:
   if item.get('path') and item.get('sha256'):assert digest(ROOT/item['path'])==item['sha256'],item['path']
 reuse=ROOT/'garmin/work/ireland-hiking-visibility-v10'
 if region=='ireland' and reuse.exists() and not (out/'gmapsupp.img').exists():
  old=json.loads((reuse/'build.json').read_text());assert digest(reuse/'gmapsupp.img')==old['output']['sha256']
  for name in ['lines','points','polygons','options','relations']:assert (base/'style'/name).read_bytes()==(ROOT/'garmin/hiking-visibility-v10/style'/name).read_bytes(),name
  records={}
  for source in sorted(reuse.glob('[0-9]*.img')):
   target=out/source.name
   if not target.exists():shutil.copyfile(source,target)
   assert digest(target)==digest(source);records[source.name]=digest(source)
  assert len(records)==91
  write(out/'reused-geometry.json',{'source':'Ireland v10 verified device build','sourceMapSHA256':old['output']['sha256'],'sections':records})
  command=[java_path(),'-Xmx2g','-jar',str(ROOT/'garmin/tools/mkgmap-r4924/mkgmap.jar'),'--gmapsupp','--code-page=1252','--family-id=4831','--product-id=1','--family-name=OpenBareMap Ireland','--description=OpenBareMap Ireland '+REVISION,'--series-name=OpenBareMap Garmin '+REVISION,'--output-dir='+str(out),*map(str,sorted(out.glob('[0-9]*.img'))),str(base/'style/OBM4831.txt')]
  run(command,out/'compile.log')
 elif not (out/'gmapsupp.img').exists():
  if not (work/'prepared.json').exists():run([sys.executable,str(ROOT/'garmin/prepare_inputs.py'),'--region',region],out/'prepare.log')
  assert digest(work/'overlays.osm.gz')==json.loads((work/'prepared.json').read_text())['overlay_sha256']
  if not (work/'merge-record.json').exists():run([sys.executable,str(ROOT/'garmin/merge_inputs.py'),'--region',region],out/'merge.log')
  merged=json.loads((work/'merge-record.json').read_text());assert digest(work/'combined.osm.pbf')==merged['combinedSHA256'];assert merged['osmSHA256']==json.loads(region_path(region,'sources.lock.json').read_text())['osm']['sha256']
  if not (work/'split/template.args').exists():
   split=work/'split';split.mkdir(exist_ok=True)
   run([java_path(),'-Xmx6g','-jar',str(ROOT/'garmin/tools/splitter-r654/splitter.jar'),'--mapid='+str(config['tileStartId']),'--description='+p['name'],'--max-nodes=1000000','--max-threads=2','--keep-complete=true','--output=pbf','--polygon-file='+str(coverage_polygon),'--output-dir='+str(split),str(work/'combined.osm.pbf')],out/'split.log')
  sources=sorted((work/'split').glob('[0-9]*.osm.pbf'));assert sources
  expected=write_tile_args(sources,out/'tiles.args',region,p['name'])
  hgt=work/'hgt';hgt.mkdir(exist_ok=True)
  for lock in [region_path(region,'terrain-sources.lock.json'),base/'dem-padding.lock.json']:
   for item in json.loads(lock.read_text())['assets']:
    source=ROOT/item['path'];target=hgt/source.stem
    if not target.exists():
     with gzip.open(source,'rb') as inp,target.open('wb') as dst:shutil.copyfileobj(inp,dst)
    with gzip.open(source,'rb') as inp:
     import hashlib
     assert hashlib.file_digest(inp,'sha256').hexdigest()==digest(target),target
  opts=[x for x in config['compilerOptions'] if not x.startswith(('--style-file=','--dem=','--dem-poly=','--copyright-file=','--description=','--series-name='))]
  opts+=['--style-file='+str(base/'style'),'--dem='+str(hgt),'--dem-poly='+str(coverage_polygon),'--copyright-file='+str(base/'copyright.txt'),'--description='+p['name']+' '+REVISION,'--series-name=OpenBareMap Garmin '+REVISION]
  command=[java_path(),'-Xmx6g','-jar',str(ROOT/'garmin/tools/mkgmap-r4924/mkgmap.jar'),'--output-dir='+str(out),*opts,'-c',str(out/'tiles.args'),str(base/'style'/('OBM'+str(config['familyId'])+'.txt'))]
  write(out/'build.json',{'status':'started','region':region,'command':command,'configSHA256':digest(base/'config.json'),'styleSHA256':{f.name:digest(f) for f in (base/'style').iterdir() if f.is_file()},'sections':{str(f):digest(f) for f in sources}})
  run(command,out/'compile.log');assert expected=={f.stem for f in out.glob('[0-9]*.img')}
 image=out/'gmapsupp.img';assert image.exists() and 0<image.stat().st_size<4*1024**3
 if (out/'tiles.args').exists():
  expected=set(re.findall(r'^mapname:\s*(\d+)',(out/'tiles.args').read_text(),re.M));assert expected=={f.stem for f in out.glob('[0-9]*.img')}
 elif region=='ireland':assert len(list(out.glob('[0-9]*.img')))==91
 jar=ROOT/'garmin/tools/mkgmap-r4924/mkgmap.jar';java=Path(java_path())
 subprocess.run([str(java.with_name('javac')),'-cp',str(jar),'-d',str(out),str(ROOT/'garmin/InspectMap.java'),str(ROOT/'garmin/CheckHikingRelease.java')],check=True)
 names=['Dublin','Belfast','Carrauntoohil'] if region=='ireland' else p.get('inspectionNames',['London','Cardiff','Newcastle upon Tyne','Plymouth','Carlisle'])
 with (out/'inspection.json').open('w') as f:subprocess.run([str(java),'-Xmx2g','-cp',str(out)+':'+str(jar),'InspectMap',str(out),*names],stdout=f,check=True)
 with (out/'hiking-validation.txt').open('w') as f:subprocess.run([str(java),'-Xmx2g','-cp',str(out)+':'+str(jar),'CheckHikingRelease',str(out)],stdout=f,check=True)
 write(out/'release.json',{'region':region,'garminPackageRevision':REVISION,'familyId':config['familyId'],'routing':False,'contourIntervalMetres':20,'output':{'path':str(image),'bytes':image.stat().st_size,'sha256':digest(image)},'configSHA256':digest(base/'config.json'),'styleSHA256':{f.name:digest(f) for f in (base/'style').iterdir() if f.is_file()},'inspection':json.loads((out/'inspection.json').read_text()),'status':'compiled and structurally verified; device rendering depends on Garmin settings'})
 print('GARMIN HIKING RELEASE VERIFIED:',region,flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--region',required=True,choices=['ireland','england-wales','scotland','sierra-nevada']);main(parser.parse_args().region)
