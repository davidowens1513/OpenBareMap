#!/usr/bin/env python3
"""Acquire official OSM land polygons; never silently replace a locked snapshot."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import urllib.request
import zipfile
from openbaremap import ROOT,digest,write

URL='https://osmdata.openstreetmap.de/download/land-polygons-split-4326.zip'
LOCK=ROOT/'coast-sources.lock.json'

if __name__=='__main__':
    existing=json.loads(LOCK.read_text()) if LOCK.exists() else None
    path=ROOT/(existing['path'] if existing else 'data/land-polygons-split-4326.zip')
    if not path.exists():
        part=path.with_suffix('.zip.part')
        path.parent.mkdir(parents=True,exist_ok=True)
        with urllib.request.urlopen(URL,timeout=120) as response,part.open('wb') as out:
            headers=dict(response.headers)
            shutil.copyfileobj(response,out)
        with zipfile.ZipFile(part) as archive:
            bad=archive.testzip()
            if bad:raise ValueError('Coast archive CRC failed: '+bad)
        if existing and digest(part)!=existing['sha256']:
            raise ValueError('The remote archive changed. Recover the recorded snapshot; no source lock or accepted archive was replaced.')
        part.rename(path)
        write(path.with_suffix('.headers.json'),headers)
        if not existing:
            write(LOCK,{'url':URL,'path':str(path.relative_to(ROOT)),'sha256':digest(path),'bytes':path.stat().st_size,'accessed_utc':datetime.now(timezone.utc).isoformat(),'source_snapshot':'Publication header: '+headers.get('Last-Modified','unknown')+'; not a guaranteed OSM snapshot timestamp','license':'ODbL 1.0; OpenStreetMap contributors'})
    if not LOCK.exists():raise ValueError('Unregistered existing archive; review provenance before creating a lock')
    if digest(path)!=json.loads(LOCK.read_text())['sha256']:raise ValueError('Coast source checksum mismatch')
    print('Recorded coast source checksum verified.')
