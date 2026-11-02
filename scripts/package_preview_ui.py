#!/usr/bin/env python3
"""Package shared preview pages and zoomable regional keys without rebuilding map archives."""
import argparse,html,shutil,json
from pathlib import Path
from regions import ROOT,profile

def package_ui(output,regions=None):
 output=Path(output);assets=output/'assets';(assets/'legends').mkdir(parents=True,exist_ok=True)
 for name in ['preview.js','preview.css','legend.js','legend.css']:shutil.copyfile(ROOT/'web-preview'/name,assets/name)
 for region in (regions or ['ireland','england-wales','scotland','sierra-nevada']):
  p=profile(region);directory=output/region;directory.mkdir(exist_ok=True)
  for name in ['index.html','legend.html']:
   text=(ROOT/'web-preview'/name).read_text().replace('{{REGION}}',html.escape(p['label'],quote=True)).replace('{{ID}}',region)
   (directory/name).write_text(text)
  (directory/'region.json').write_text(json.dumps(p,indent=2)+'\n')
  source=ROOT/'app-legend/openbaremap-legend@2x.png' if region=='ireland' else ROOT/'regions'/region/'legend/openbaremap-legend@2x.png'
  shutil.copyfile(source,assets/'legends'/(region+'@2x.png'))
 return output
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();print(package_ui(args.output.resolve()))
