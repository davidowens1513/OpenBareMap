#!/usr/bin/env python3
"""Publish only small public preview UI files, with browser revalidation required."""
import argparse,json,subprocess
from pathlib import Path
from urllib.parse import urlsplit
from package_preview_ui import package_ui
from regions import ROOT
CACHE_POLICY='no-cache, max-age=0, must-revalidate'
def stage(output):
 output=Path(output);output.mkdir(exist_ok=False,parents=True)
 catalog=json.loads((ROOT/'config/preview-regions.json').read_text());groups={}
 for e in catalog:
  key=urlsplit(e['url']).path.lstrip('/');prefix=key.rsplit('/',2)[0];groups.setdefault(prefix,[]).append(e['id'])
 groups.setdefault('OpenBareMap/preview-v2',[]).append('england-wales')
 for prefix,regions in groups.items():
  folder=output/prefix;package_ui(folder,regions)
  for p in folder.rglob('*'):
   if p.is_file() and p.name not in ['index.html','preview.css','preview.js']:p.unlink()
 # The older England/Wales address always leads to the active release.
 legacy=output/'OpenBareMap/preview-v2/england-wales/index.html';latest=next(e['url'] for e in catalog if e['id']=='england-wales')
 if legacy.exists():
  import html
  text=legacy.read_text().replace('<head>','<head><meta http-equiv="refresh" content="0; url='+html.escape(latest,quote=True)+'">',1);legacy.write_text(text)
 return output
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--remote',default='r2:baregps-production-assets/');parser.add_argument('--stage-only',action='store_true');args=parser.parse_args();stage(args.output.resolve())
 if not args.stage_only:subprocess.run(['rclone','copy',str(args.output.resolve()),args.remote,'--ignore-times','--metadata','--metadata-set','cache-control='+CACHE_POLICY,'--s3-no-system-metadata=false','--s3-no-check-bucket','--transfers','4'],check=True)
