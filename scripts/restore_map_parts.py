#!/usr/bin/env python3
"""Restore a selected map byte-for-byte from independently verified LFS parts."""
import argparse,hashlib,json,os
from pathlib import Path
from openbaremap import ROOT

def sha(path):
 with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def restore(manifest,root=ROOT):
 root=Path(root).resolve();record=json.loads(Path(manifest).read_text());target=(root/record['path']).resolve()
 if not target.is_relative_to(root):raise ValueError('Map destination escapes repository')
 if target.exists():
  if target.stat().st_size!=record['bytes'] or sha(target)!=record['sha256']:raise ValueError('Existing map differs; refusing overwrite')
  return target
 parts=[]
 for item in record['parts']:
  part=(root/item['path']).resolve()
  if not part.is_relative_to(root) or not part.is_file() or part.stat().st_size!=item['bytes'] or sha(part)!=item['sha256']:
   raise ValueError('Missing or changed map part; run git lfs pull: '+item['path'])
  parts.append(part)
 target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_name(target.name+'.restoring');h=hashlib.sha256();size=0
 try:
  with temporary.open('xb') as out:
   for part in parts:
    with part.open('rb') as inp:
     for block in iter(lambda:inp.read(1024*1024),b''):out.write(block);h.update(block);size+=len(block)
   out.flush();os.fsync(out.fileno())
  if size!=record['bytes'] or h.hexdigest()!=record['sha256']:raise ValueError('Restored map checksum mismatch')
  os.link(temporary,target);temporary.unlink()
 except BaseException:
  if temporary.exists():temporary.unlink()
  raise
 return target

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path,default=ROOT/'releases/england-wales/2.0.0/maps/basemap.mbtiles.parts.json');args=parser.parse_args();print(restore(args.manifest))
