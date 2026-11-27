#!/usr/bin/env python3
"""Package shared preview pages and zoomable regional keys without rebuilding map archives."""
import argparse,html,shutil,json
from pathlib import Path
from regions import ROOT,profile

def grouped_options(catalog,selected,groups=None):
 catalog_ids=[item['id'] for item in catalog]
 if len(catalog_ids)!=len(set(catalog_ids)):
  raise ValueError('Preview catalogue region IDs must be unique')
 entries={item['id']:item for item in catalog}
 if groups is None:
  groups=json.loads((ROOT/'config/preview-region-groups.json').read_text())
 ordered=[region for group in groups for region in group['regions']]
 if len(ordered)!=len(set(ordered)):
  raise ValueError('Preview groups must contain every catalogued region exactly once')
 if len(ordered)!=len(catalog_ids) or set(ordered)!=set(catalog_ids):
  raise ValueError('Preview groups must contain every catalogued region exactly once')
 result=[]
 for group in groups:
  result.append('<optgroup label="'+html.escape(group['label'],quote=True)+'">')
  for region in group['regions']:
   entry=entries[region]
   result.append('<option value="'+html.escape(entry['url'],quote=True)+'"'+(' selected' if region==selected else '')+'>'+html.escape(entry['label'])+'</option>')
  result.append('</optgroup>')
 return ''.join(result)

def package_ui(output,regions=None):
 output=Path(output);assets=output/'assets';(assets/'legends').mkdir(parents=True,exist_ok=True)
 catalog=json.loads((ROOT/'config/preview-regions.json').read_text())
 selected=regions or [item['id'] for item in catalog]
 published={item['id'] for item in catalog}
 catalog += [{'id':region,'label':profile(region)['label'],'url':'../'+region+'/index.html'}
             for region in selected if region not in published]
 for name in ['preview.js','preview.css','legend.js','legend.css']:shutil.copyfile(ROOT/'web-preview'/name,assets/name)
 for region in selected:
  p=profile(region);directory=output/region;directory.mkdir(exist_ok=True)
  for name in ['index.html','legend.html']:
   text=(ROOT/'web-preview'/name).read_text().replace('{{REGION}}',html.escape(p['label'],quote=True)).replace('{{ID}}',region)
   options=grouped_options(catalog,region)
   text=text.replace('{{REGION_OPTIONS}}',options)
   (directory/name).write_text(text)
  (directory/'region.json').write_text(json.dumps(p,indent=2)+'\n')
  source=ROOT/'app-legend/openbaremap-legend@2x.png' if region=='ireland' else ROOT/'regions'/region/'legend/openbaremap-legend@2x.png'
  shutil.copyfile(source,assets/'legends'/(region+'@2x.png'))
 return output
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();print(package_ui(args.output.resolve()))
