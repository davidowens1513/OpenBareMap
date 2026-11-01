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
    selection=region_path(region,'active-map.json')
    native_report=ROOT/'regions'/region/'garmin/build-report.json'
    # A finished release can be checked without rehydrating archived raw inputs.
    # Any stage that still needs to build must first verify its locked sources.
    if not selection.exists() or not native_report.exists():
        run('scripts/fetch_region.py','--region',region)
    if not selection.exists():
        top=ROOT/'build'/(region+'-topography')
        if not top.exists():run('scripts/build_topography.py',region+'-topography','--region',region)
        elif not json.loads((top/'build.json').read_text())['status'].startswith('built and structurally validated'):
            raise ValueError('Topography stage is incomplete; inspect its build record before resuming')
        for name,item in json.loads((top/'build.json').read_text())['outputs'].items():
            if digest(top/name)!=item['sha256']:raise ValueError('Topography checkpoint changed: '+name)
        for stage in ('basemap','geometry','finish'):run('scripts/build_region.py','--region',region,'--stage',stage)
    # Accepted datasets remain usable after redundant intermediates are cleaned.
    active=json.loads(selection.read_text())
    for name,item in active['datasets'].items():
        if digest(ROOT/item['path'])!=item['sha256']:raise ValueError('Selected dataset changed: '+name)
    if active['storageRevision']=='2.0.0-england-wales-r1':
        run('scripts/build_region_context.py','--region',region)
    elif active['storageRevision']!='2.0.0-england-wales-r3':
        raise ValueError('Coastal background needs repair before packaging')
    run('scripts/build_region.py','--region',region,'--stage','packages')
    if not native_report.exists():run('scripts/build_region_garmin.py','--region',region)
    run('scripts/validate_region.py','--region',region)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--region',choices=['england-wales'],required=True);a=p.parse_args();main(a.region)
