import json,hashlib,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];out=Path(__file__).resolve().parent
locks=['sources.lock.json','coast-sources.lock.json','terrain-sources.lock.json','garmin/inputs.lock.json','garmin/dem-padding.lock.json','garmin/toolchain.lock.json','regions/england-wales/sources.lock.json','regions/england-wales/terrain-sources.lock.json','regions/england-wales/garmin/inputs.lock.json','regions/england-wales/garmin/dem-padding.lock.json']
records={}
def walk(x,lock):
 if isinstance(x,dict):
  if 'path' in x and 'sha256' in x and x['path']:
   p=x['path'];records.setdefault(p,{'path':p,'expected':x['sha256'],'locks':[]})['locks'].append(lock)
  for v in x.values():walk(v,lock)
 elif isinstance(x,list):
  for v in x:walk(v,lock)
for lock in locks:walk(json.loads((ROOT/lock).read_text()),lock)
for p,expected in [('garmin/dist/OpenBareMap-Ireland.img','2e0e907e52b0bd535481b013c2487bb327e749fcf62ab61935ae2d94396b6c96'),('regions/england-wales/garmin/dist/OpenBareMap-England-Wales.img','c0792c5b885c4f44e3c2189c2cc2d7e9508b52f68067fdb6b5a23e94f3e59855'),('garmin/dist/OpenBareMap-My-Tracks.img','1c8d81a890151a1758ef7ae7212018906e61d851ea1b32da2cace0a5f3a0b5d8')]:records[p]={'path':p,'expected':expected,'locks':['build/install records']}
results=[]
for i,item in enumerate(records.values()):
 p=ROOT/item['path']
 try:
  with p.open('rb') as f:item['actual']=hashlib.file_digest(f,'sha256').hexdigest()
  item['bytes']=p.stat().st_size;item['status']='match' if item['actual']==item['expected'] else 'MISMATCH'
 except Exception as e:item['status']='UNREADABLE';item['error']=str(e)
 results.append(item)
 (out/'source-checks.json').write_text(json.dumps({'files':results,'complete':i==len(records)-1,'expectedFiles':len(records)},indent=2)+'\n')
 print(i+1,len(records),item['status'],item['path'],flush=True)
