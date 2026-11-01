#!/usr/bin/env python3
"""Remove explicitly selected obsolete/generated outputs, protecting locked inputs and active maps."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,zipfile,time
ROOT=Path(__file__).resolve().parents[1];RECORDS=ROOT/'maintenance';RECORDS.mkdir(exist_ok=True)
RELATIVE=['regions/england-wales/garmin/work','work/separate-exports','work/web-previews','work/superseded-england-wales-maps','work/full-map-reassembly-check','work/grid-clone-check.mbtiles','work/swift-ios-module-cache','work/swift-module-cache','work/swift-region-module-cache','work/test-ios-loader-2.0','work/test-regional-ios-loader','work/stale-index-lock-20261101-113159','work/stale-index-lock-20261101-121044','build/england-wales-release','build/england-wales-coast-context','android/app/build','android/loader/build']
TEMP=['openbaremap-device-install','openbaremap-ew-coast-fix','openbaremap-ew-garmin-final','openbaremap-ew-garmin-r2','openbaremap-ew-r2-install','openbaremap-publish','openbaremap-publish.git','openbaremap-publish-rewrite.log','openbaremap-public-r2-verification.img','openbaremap-live-site-r2.html','openbaremap-ew-usb-devices.json','openbaremap-ew-current-devices.log','openbaremap-IMG_7455.png','openbaremap-IMG_7456.png','openbaremap-IMG_7457.png','openbaremap-montana-sample.txt','openbaremap-mtp-detect.log','openbaremap-mtp-errors.log','openbaremap-mtp-folders.log','openbaremap-mtp-maps.log','openbaremap-sample-status.log','openbaremap_mtp','openbaremap_mtp.c','CoastAudit.class','Inventory.class','ProbeLand.class','ValidateMapSet.class','InspectMap.class']
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def walk_records(x,protected):
 if isinstance(x,dict):
  if isinstance(x.get('path'),str):
   p=Path(x['path'])
   if not p.is_absolute():protected.add((ROOT/p).resolve())
  for v in x.values():walk_records(v,protected)
 elif isinstance(x,list):
  for v in x:walk_records(v,protected)
def describe(p):
 size=0;allocated=0;count=0
 files=[p] if p.is_file() or p.is_symlink() else p.rglob('*')
 for f in files:
  if f.is_file() or f.is_symlink():
   s=f.lstat();size+=s.st_size;allocated+=s.st_blocks*512;count+=1
 return {'path':str(p),'logicalBytes':size,'allocatedBytes':allocated,'files':count}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
 publication=json.loads((ROOT/'releases/england-wales/2.0.0/garmin-publication/publication.json').read_text())
 if not publication['liveWebsiteLinkVerified']:raise ValueError('Public verification missing')
 protected=set();locks=list(ROOT.glob('*.lock.json'))+list((ROOT/'garmin').glob('*.lock.json'))+list((ROOT/'regions').glob('*/*.lock.json'))+list((ROOT/'regions').glob('*/garmin/*.lock.json'))
 for p in locks:walk_records(json.loads(p.read_text()),protected)
 active={}
 for p in [ROOT/'active-map.json',ROOT/'regions/england-wales/active-map.json']:
  for item in json.loads(p.read_text())['datasets'].values():active[(ROOT/item['path']).resolve()]=item['sha256']
 for name,path in [('ireland','garmin/dist/OpenBareMap-Ireland.img'),('england-wales','regions/england-wales/garmin/dist/OpenBareMap-England-Wales.img'),('my-tracks','garmin/dist/OpenBareMap-My-Tracks.img')]:
  if name=='my-tracks' and not (ROOT/path).exists():continue
  report=ROOT/('garmin/my-tracks/build-report.json' if name=='my-tracks' else 'garmin/build-report.json' if name=='ireland' else 'regions/england-wales/garmin/build-report.json');r=json.loads(report.read_text()) if report.exists() else {'outputSHA256':sha(ROOT/path)}
  active[(ROOT/path).resolve()]=r['outputSHA256'] if name=='my-tracks' else r['output'].get('sha256',r['output'].get('outputSHA256'))
 protected.update(active)
 targets=[ROOT/p for p in RELATIVE]+[Path('/private/tmp')/p for p in TEMP];targets=[p for p in targets if p.exists() or p.is_symlink()]
 for target in targets:
  resolved=target.resolve()
  if resolved in [ROOT,Path('/private/tmp')]:raise ValueError('Unsafe root target')
  if any(p==resolved or p.is_relative_to(resolved) for p in protected):raise ValueError('Target contains a locked input/active file: '+str(target))
 plan={'date':'2026-11-01','purpose':'Remove obsolete builds, generated duplicate exports and temporary transfer/publishing files after verified repair publication. Preserve active release files, source data, toolchains, source code and Git history.','targets':[describe(p) for p in targets],'protectedActiveFiles':{str(k):v for k,v in active.items()},'freeBytesBefore':shutil.disk_usage(ROOT).free,'status':'planned'}
 record=RECORDS/'cleanup-2026-11-01.json'
 if args.apply and record.exists():
  previous=json.loads(record.read_text());plan['freeBytesBefore']=previous.get('freeBytesBefore',plan['freeBytesBefore'])
 record.write_text(json.dumps(plan,indent=2)+'\n')
 if not args.apply:
  print(json.dumps({'targets':len(targets),'logicalBytes':sum(x['logicalBytes'] for x in plan['targets']),'allocatedBytes':sum(x['allocatedBytes'] for x in plan['targets'])}));return
 # Verify current selected maps before deleting anything.
 for p,expected in active.items():
  if sha(p)!=expected:raise ValueError('Active release checksum mismatch: '+str(p))
 print('Active map checksums verified; archiving compact metadata.',flush=True)
 archive=RECORDS/'removed-build-metadata-2026-11-01.zip'
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for parent in [ROOT/'work/separate-exports',ROOT/'regions/england-wales/garmin/work',ROOT/'work/web-previews',ROOT/'build/england-wales-release',ROOT/'build/england-wales-coast-context']:
   if not parent.exists():continue
   for p in parent.rglob('*'):
    if p.is_file() and p.suffix in ['.json','.txt','.swift','.log','.lua'] and p.stat().st_size<2*1024*1024 and not p.stat().st_flags&0x40000000:z.write(p,p.relative_to(ROOT))
  install=Path('/private/tmp/openbaremap-ew-r2-install')
  if install.exists():
   for p in install.glob('*.json'):z.write(p,'installation-receipts/'+p.name)
 for target in targets:
  print('Removing',target,flush=True)
  if target.is_symlink() or target.is_file():target.unlink()
  else:shutil.rmtree(target)
 # These hashes also catch accidental deletion or mutation of the current release.
 for p,expected in active.items():
  if sha(p)!=expected:raise ValueError('Active release changed during cleanup: '+str(p))
 plan.update(status='completed',metadataArchive=str(archive.relative_to(ROOT)),freeBytesAfter=shutil.disk_usage(ROOT).free)
 plan['measuredFreeBytesIncrease']=plan['freeBytesAfter']-plan['freeBytesBefore'];record.write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps({'status':'completed','targetsRemoved':len(targets),'measuredFreeBytesIncrease':plan['measuredFreeBytesIncrease']},indent=2))
if __name__=='__main__':main()
