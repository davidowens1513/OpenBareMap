"""Edition settings, keeping the established Ireland paths as the default."""
import json
from pathlib import Path
from openbaremap import ROOT

REGIONS = ('ireland', 'england-wales')

def profile(region='ireland'):
    if region not in REGIONS:
        raise ValueError('Unknown region: ' + region)
    return json.loads((ROOT/'regions'/region/'region.json').read_text())

def region_path(region, name):
    profile(region)
    return ROOT/name if region == 'ireland' else ROOT/'regions'/region/name

def active_map(region='ireland'):
    return json.loads(region_path(region, 'active-map.json').read_text())

def region_style(region='ireland'):
    style = json.loads((ROOT/'style/openbaremap.json').read_text())
    if region == 'ireland':
        return style
    p = profile(region)
    style['name'] = p['name'] + ' ' + p['mapVersion']
    style['center'] = p['destinations']['island'][:2]
    style['zoom'] = p['destinations']['island'][2]
    style['sources']['coast']['bounds'] = p['bounds']
    del style['sources']['townlands']
    grid = style['sources'].pop('irish-grid')
    style['sources'][p['gridSource']] = grid
    style['layers'] = [layer for layer in style['layers'] if layer.get('source') != 'townlands']
    def translate(value):
        if isinstance(value, list):
            return [translate(item) for item in value]
        if isinstance(value, dict):
            return {key: translate(item) for key,item in value.items()}
        return 'name_cy' if value == 'name_ga' else value
    style = translate(style)
    for layer in style['layers']:
        if layer.get('source') == 'irish-grid':
            layer['source'] = p['gridSource']
            layer['id'] = layer['id'].replace('irish-grid', p['gridSource'])
        # England/Wales constituent-country boundaries use OSM admin_level 4.
        if layer['id'] == 'administrative-boundaries':
            layer['filter'] = ['in', ['to-string', ['get','admin_level']], ['literal',['2','4']]]
    return style

def provenance_files(region='ireland'):
    return [region_path(region, name) for name in ('active-map.json','sources.lock.json','terrain-sources.lock.json')] + [ROOT/name for name in ('coast-sources.lock.json','legacy-assets.lock.json','viewer-assets.lock.json','assets/sprites.lock.json','config/transport-style.json')] + ([region_path(region,'grid-provenance.json'),region_path(region,'python-runtime.json')] if region!='ireland' else [])


def process_script(region='ireland'):
    profile(region)
    script=(ROOT/'config/process.lua').read_text()
    if region=='ireland':return script
    return script.replace('name:ga','name:cy').replace('name_ga','name_cy').replace('"tracktype", "access"','"tracktype", "designation", "bicycle", "horse", "sac_scale", "trail_visibility", "access"')
