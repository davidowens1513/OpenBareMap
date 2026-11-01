#!/usr/bin/env python3
"""One-command complete regional build; accepted outputs are never overwritten."""
import argparse
import json
import subprocess
import sys
from openbaremap import ROOT,digest
from regions import region_path

def run(*args):subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,check=True)

def main(region):
    run('scripts/fetch_region.py','--region',region)
    top=ROOT/'build'/(region+'-topography')
    if not top.exists():run('scripts/build_topography.py',region+'-topography','--region',region)
    elif not json.loads((top/'build.json').read_text())['status'].startswith('built and structurally validated'):
        raise ValueError('Topography stage is incomplete; inspect its build record before resuming')
    for name,item in json.loads((top/'build.json').read_text())['outputs'].items():
        if digest(top/name)!=item['sha256']:raise ValueError('Topography checkpoint changed: '+name)
    run('scripts/build_region.py','--region',region)
    if not (ROOT/'regions'/region/'garmin/build-report.json').exists():run('scripts/build_region_garmin.py','--region',region)
    run('scripts/validate_region.py','--region',region)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--region',choices=['england-wales'],required=True);a=p.parse_args();main(a.region)
