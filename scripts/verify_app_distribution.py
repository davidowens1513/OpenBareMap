#!/usr/bin/env python3
"""Read back public integration kits and instructions against their local catalog."""
import argparse,hashlib,json,urllib.request,datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from openbaremap import ROOT,write

CATALOG=ROOT/'distribution/app-bundles-v1/catalog.json'
def read_hash(url):
    sha=hashlib.sha256();size=0;milestone=0
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=120) as response:
        if response.status!=200:raise ValueError('Public HTTP status: '+str(response.status))
        content_type=response.headers.get('Content-Type')
        while chunk:=response.read(1024*1024):
            sha.update(chunk);size+=len(chunk)
            if size//(512*1024*1024)>milestone:milestone=size//(512*1024*1024);print(url.split('/')[-1],size,'bytes read',flush=True)
    return size,sha.hexdigest(),content_type

def verify(region):
    catalog=json.loads(CATALOG.read_text());records={}
    for platform,item in catalog['regions'][region].items():
        size,sha,mime=read_hash(item['url'])
        if size!=item['bytes'] or sha!=item['sha256']:raise ValueError('Public bundle mismatch: '+region+'/'+platform)
        _,instruction_sha,instruction_mime=read_hash(item['instructionsURL'])
        if instruction_sha!=item['instructionsSHA256']:raise ValueError('Public instructions mismatch')
        records[platform]={'url':item['url'],'bytes':size,'sha256':sha,'contentType':mime,'fullPublicReadbackVerified':True,'instructionsURL':item['instructionsURL'],'instructionsSHA256':instruction_sha,'instructionsContentType':instruction_mime}
        print(region,platform,'fully verified',flush=True)
    g=json.loads((ROOT/'distribution/app-bundles-v1/garmin'/region/'manifest.json').read_text())
    _,sha,mime=read_hash(g['instructionsURL'])
    if sha!=g['instructionsSHA256']:raise ValueError('Public Garmin guide mismatch')
    result={'verifiedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'region':region,'bundles':records,'garminInstructions':{'url':g['instructionsURL'],'sha256':sha,'contentType':mime,'verified':True}}
    write(ROOT/'distribution/app-bundles-v1'/('publication-'+region+'.json'),result)
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--regions',nargs='+',choices=['ireland','england-wales','scotland','sierra-nevada'],default=['ireland','england-wales','scotland']);args=parser.parse_args()
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(verify,args.regions))
