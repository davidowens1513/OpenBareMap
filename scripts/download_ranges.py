#!/usr/bin/env python3
"""Resumable bounded parallel HTTP ranges, verified against upstream MD5."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import shutil
import time
import urllib.request

def fetch(url,path,workers=8):
    with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=60) as response:
        size=int(response.headers['Content-Length'])
    with urllib.request.urlopen(url+'.md5',timeout=60) as response:
        expected=response.read().decode().split()[0]
    path=Path(path);parts=path.with_name(path.name+'.ranges');parts.mkdir(parents=True,exist_ok=True)
    step=16*1024*1024
    def chunk(start):
        end=min(size,start+step)-1;part=parts/str(start)
        if part.exists() and part.stat().st_size==end-start+1:return part
        for attempt in range(4):
            try:
                req=urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}'})
                with urllib.request.urlopen(req,timeout=120) as src,part.open('wb') as out:
                    if src.status!=206 or src.headers.get('Content-Range')!=f'bytes {start}-{end}/{size}':
                        raise ValueError('Server did not honour exact range')
                    shutil.copyfileobj(src,out)
                if part.stat().st_size!=end-start+1:raise ValueError('Incomplete range')
                print(f'{path.name}: range {start}-{end} complete',flush=True);return part
            except Exception:
                if attempt==3:raise
                time.sleep(2)
    with ThreadPoolExecutor(max_workers=workers) as pool:files=list(pool.map(chunk,range(0,size,step)))
    result=path.with_name(path.name+'.assembled')
    with result.open('wb') as out:
        for part in files:
            with part.open('rb') as src:shutil.copyfileobj(src,out)
    with result.open('rb') as src:actual=hashlib.file_digest(src,'md5').hexdigest()
    if actual!=expected:raise ValueError('Upstream MD5 mismatch')
    result.replace(path)
    (path.with_name(path.name+'.md5')).write_text(expected+'  '+path.name+'\n')
    shutil.rmtree(parts)
    print(path.name+' fully downloaded and MD5 verified',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('url');p.add_argument('output',type=Path);p.add_argument('--workers',type=int,default=8);a=p.parse_args();fetch(a.url,a.output,a.workers)
