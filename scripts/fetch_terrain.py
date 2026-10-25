#!/usr/bin/env python3
"""Acquire and lock the complete 1-degree elevation grid covering Ireland."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'data/elevation'
LOCK=ROOT/'terrain-sources.lock.json'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def fetch(item):
    lat,lon=item
    name=f'N{lat:02d}W{abs(lon):03d}.hgt.gz'
    url=f'https://elevation-tiles-prod.s3.amazonaws.com/skadi/N{lat:02d}/{name}'
    path=DEST/name
    if not path.exists():
        part=path.with_suffix('.gz.part')
        with urllib.request.urlopen(url,timeout=120) as response,part.open('wb') as output:
            import shutil
            shutil.copyfileobj(response,output)
            headers=dict(response.headers)
        # Gzip CRC and expected HGT grid size must both pass before accepting it.
        raw=gzip.decompress(part.read_bytes())
        if len(raw)!=3601*3601*2:raise ValueError(f'Unexpected elevation grid: {name}')
        part.rename(path)
        path.with_suffix('.headers.json').write_text(json.dumps(headers,indent=2)+'\n')
    else:
        if len(gzip.decompress(path.read_bytes()))!=3601*3601*2:raise ValueError(name)
    print(name+' verified',flush=True)
    return {'path':str(path.relative_to(ROOT)),'url':url,'sha256':sha(path),'bytes':path.stat().st_size}

if __name__=='__main__':
    DEST.mkdir(parents=True,exist_ok=True)
    if LOCK.exists():
        lock=json.loads(LOCK.read_text())
        for asset in lock['assets']:
            if sha(ROOT/asset['path'])!=asset['sha256']:raise ValueError('Source checksum changed: '+asset['path'])
        print('All recorded elevation source checksums match.')
    else:
        with ThreadPoolExecutor(max_workers=4) as pool:
            assets=list(pool.map(fetch,[(lat,lon) for lat in range(51,56) for lon in range(-11,-5)]))
        lock={'dataset':'Mapzen/Terrain Tiles skadi composite elevation, not pure SRTM','coverage':[-11,51,-5,56],'grid':'3601 by 3601 signed 16-bit heights per degree tile','accessed_utc':datetime.now(timezone.utc).isoformat(),'documentation':'https://github.com/tilezen/joerd/tree/master/docs','assets':assets}
        LOCK.write_text(json.dumps(lock,indent=2,sort_keys=True)+'\n')
        print('Full-island elevation source lock written.')
