#!/usr/bin/env python3
"""Recompile a new Garmin revision from verified, complete regional split sources."""
import argparse,gzip,hashlib,json,os,re,shutil,subprocess,sys,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'garmin'))
from build import java_path,tools,run

def sha(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--work',type=Path,required=True);parser.add_argument('--resume',action='store_true');parser.add_argument('--dem',type=Path,required=True);parser.add_argument('--fallback-splits',type=Path);args=parser.parse_args();work=args.work.resolve()
 if work.exists() and not args.resume:raise FileExistsError(work)
 if (work/'compiled').exists():raise FileExistsError(work/'compiled')
 work.mkdir(parents=True,exist_ok=True)
 region=ROOT/'regions/england-wales/garmin';config=json.loads((region/'config.json').read_text());p=json.loads((ROOT/'regions/england-wales/region.json').read_text())
 from identities import validate_registry,validate_config
 validate_registry();validate_config('england-wales',config)
 tools();sources=region/'work/split';template=(sources/'template.args').read_text();ids=re.findall(r'^mapname:\s*(\d+)',template,re.M)
 files=re.findall(r'^input-file:\s*(.+)',template,re.M)
 if len(ids)!=318 or len(files)!=len(ids) or len(set(ids))!=len(ids):raise ValueError('Incomplete split-source inventory')
 local=work/'pbf';local.mkdir(exist_ok=True);records=[];arguments=[]
 def copy_source(pair):
  index,(oldid,name)=pair;src=sources/name;dst=local/(oldid+'.osm.pbf')
  fallback=args.fallback_splits/(oldid+'.osm.pbf') if args.fallback_splits else None
  if fallback is not None and fallback.exists():src=fallback
  for attempt in range(4):
   try:
    if not dst.exists() or dst.stat().st_size!=src.stat().st_size:
     with src.open('rb') as inp,dst.open('wb') as out:shutil.copyfileobj(inp,out,1024*1024)
    expected=sha(src)
    if expected!=sha(dst):raise ValueError('Split-source copy changed')
    print('Verified source',index+1,len(ids),oldid,flush=True)
    return {'sourceTileId':int(oldid),'tileId':config['tileStartId']+index,'sha256':expected,'bytes':dst.stat().st_size}
   except OSError:
    dst.unlink(missing_ok=True)
    if attempt==3:raise
    time.sleep(1)
 with ThreadPoolExecutor(max_workers=32) as pool:records=list(pool.map(copy_source,enumerate(zip(ids,files))))
 for record in records:
  arguments.append(f"mapname: {record['tileId']}\ndescription: OpenBareMap England & Wales\ninput-file: {local/(str(record['sourceTileId'])+'.osm.pbf')}\n")
 argsfile=work/'tiles.args';argsfile.write_text('\n'.join(arguments))
 # DEM files must match the actual uncompressed locked grids, not just their size.
 dem_records=[]
 for lockpath in [ROOT/'regions/england-wales/terrain-sources.lock.json',region/'dem-padding.lock.json']:
  for item in json.loads(lockpath.read_text())['assets']:
   src=ROOT/item['path'];target=args.dem.resolve()/src.stem
   if sha(src)!=item['sha256']:raise ValueError('Elevation source changed')
   with gzip.open(src,'rb') as stream:expected=hashlib.file_digest(stream,'sha256').hexdigest()
   actual=sha(target)
   if actual!=expected:raise ValueError('Uncompressed elevation grid changed')
   dem_records.append({'name':target.name,'sha256':actual,'bytes':target.stat().st_size})
 write(work/'dem-checks.json',dem_records)
 style=work/'style';shutil.copytree(region/'style',style)
 opts=[]
 for item in config['compilerOptions']:
  for prefix,value in [('--style-file=',style),('--dem=',args.dem.resolve()),('--dem-poly=',region/'coverage.poly'),('--copyright-file=',region/'copyright.txt')]:
   if item.startswith(prefix):item=prefix+str(value);break
  opts.append(item)
 output=work/'compiled';output.mkdir();command=[java_path(),'-Xmx6g','-jar',str(ROOT/'garmin/tools/mkgmap-r4924/mkgmap.jar'),'--output-dir='+str(output),*opts,'-c',str(argsfile),str(style/'OBM4833.txt')]
 record={'revision':config['garminPackageRevision'],'status':'started','command':command,'sourceTiles':records,'inputsLockSHA256':sha(region/'inputs.lock.json'),'configSHA256':sha(region/'config.json'),'styleSHA256':{f.name:sha(f) for f in style.iterdir() if f.is_file()},'preservedMaps':{str(f.relative_to(ROOT)):sha(f) for f in [ROOT/'garmin/dist/OpenBareMap-Ireland.img',ROOT/'garmin/dist/OpenBareMap-My-Tracks.img'] if f.exists()}}
 write(work/'build.json',record);run(command,work/'compile.log')
 expected={str(x['tileId']) for x in records};actual={f.stem for f in output.glob('[0-9]*.img')}
 if expected!=actual:raise ValueError('Missing or unexpected compiled sections')
 image=output/'gmapsupp.img'
 if not 0<image.stat().st_size<4*1024**3:raise ValueError('Invalid image size')
 record.update(status='compiled; binary and geometry inspection required',outputSHA256=sha(image),outputBytes=image.stat().st_size)
 write(work/'build.json',record);print(json.dumps({k:record[k] for k in ['status','outputSHA256','outputBytes']},indent=2))
if __name__=='__main__':main()
