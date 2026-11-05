"""Edition settings, keeping the established Ireland paths as the default."""
import copy
import json
from pathlib import Path
from openbaremap import ROOT

REGIONS = ('ireland', 'england-wales', 'scotland', 'sierra-nevada', 'pyrenees', 'dolomites')

def profile(region='ireland'):
    if region not in REGIONS:
        raise ValueError('Unknown region: ' + region)
    return json.loads((ROOT/'regions'/region/'region.json').read_text())

def region_path(region, name):
    profile(region)
    return ROOT/name if region == 'ireland' else ROOT/'regions'/region/name

def active_map(region='ireland'):
    selected=json.loads(region_path(region, 'active-map.json').read_text())
    for item in selected['datasets'].values():
        target=ROOT/item['path'];manifest=target.with_name(target.name+'.parts.json')
        if not target.exists() and manifest.exists():
            from restore_map_parts import restore
            restore(manifest)
    return selected

def region_style(region='ireland'):
    style = json.loads((ROOT/'style/openbaremap.json').read_text())
    if region == 'ireland':
        return style
    p = profile(region)
    style['name'] = p['name'] + ' ' + p['mapVersion']
    style['center'] = p['destinations']['island'][:2]
    style['zoom'] = p['destinations']['island'][2]
    style['sources']['coast']['bounds'] = p.get('coastContextBounds',p['bounds'])
    del style['sources']['townlands']
    grid = style['sources'].pop('irish-grid')
    style['sources'][p['gridSource']] = grid
    style['layers'] = [layer for layer in style['layers'] if layer.get('source') != 'townlands']
    def translate(value):
        if isinstance(value, list):
            return [translate(item) for item in value]
        if isinstance(value, dict):
            return {key: translate(item) for key,item in value.items()}
        return 'name_'+p.get('nativeLanguage','cy') if value == 'name_ga' else value
    style = translate(style)
    for layer in style['layers']:
        if layer.get('source') == 'irish-grid':
            layer['source'] = p['gridSource']
            layer['id'] = layer['id'].replace('irish-grid', p['gridSource'])
        # England/Wales constituent-country boundaries use OSM admin_level 4.
        if layer['id'] == 'administrative-boundaries':
            layer['filter'] = ['in', ['to-string', ['get','admin_level']], ['literal',['2','4']]]
    if 'minorWaterwayMinzoom' in p:
        index=next(i for i,layer in enumerate(style['layers']) if layer['id']=='waterway')
        major=style['layers'][index];minor=copy.deepcopy(major)
        major['filter']=['in',['get','class'],['literal',['river','canal']]]
        minor.update(id='waterway-minor',minzoom=p['minorWaterwayMinzoom'],filter=['!',major['filter']])
        style['layers'].insert(index+1,minor)
    if p.get('coverageBoundary') or p.get('boundaryPreview'):
        for name in ('park-boundary','coverage','coverage-mask'):
            style['sources'][name]={'type':'geojson','data':json.loads(region_path(region,name+'.geojson').read_text()),'attribution':'Fuente: Organismo Autónomo Parques Nacionales · CC BY 4.0'}
        # Hide rectangular tile padding so the preview follows the actual buffer.
        style['layers'] += [
            {'id':'coverage-mask','type':'fill','source':'coverage-mask','paint':{'fill-color':'#f5f3ec','fill-antialias':False}},
            {'id':'park-boundary','type':'line','source':'park-boundary','paint':{'line-color':'#8c278b','line-width':2.5,'line-opacity':0.95}},
            {'id':'coverage-boundary','type':'line','source':'coverage','paint':{'line-color':'#444444','line-width':2,'line-dasharray':[4,3]}}]
    return style

def provenance_files(region='ireland'):
    return [region_path(region, name) for name in ('active-map.json','sources.lock.json','terrain-sources.lock.json')] + [ROOT/name for name in ('coast-sources.lock.json','legacy-assets.lock.json','viewer-assets.lock.json','assets/sprites.lock.json','config/transport-style.json')] + ([region_path(region,name) for name in ('boundary-source.json','park-boundary.geojson','coverage.geojson','coverage-mask.geojson')] if profile(region).get('coverageBoundary') else []) + ([region_path(region,'grid-provenance.json'),region_path(region,'python-runtime.json')] if region!='ireland' else [])


def process_script(region='ireland'):
    profile(region)
    script=(ROOT/'config/process.lua').read_text()
    if region=='ireland':return script
    language=profile(region).get('nativeLanguage','cy')
    return script.replace('name:ga','name:'+language).replace('name_ga','name_'+language).replace('"tracktype", "access"','"tracktype", "designation", "bicycle", "horse", "sac_scale", "trail_visibility", "access"')


def garmin_work(region='ireland'):
    profile(region)
    import hashlib,os,tempfile
    if region=='ireland' and not os.environ.get('OPENBAREMAP_BUILD_ROOT'):return ROOT/'garmin/work'
    cache=Path(os.environ.get('OPENBAREMAP_BUILD_ROOT',tempfile.gettempdir()))
    identity=hashlib.sha256(str(ROOT).encode()).hexdigest()[:12]
    return cache/'OpenBareMap-builds'/identity/region/'garmin'


def accepted_ireland_baseline():
    """Keep shared/mobile preservation pins while selecting the accepted native release."""
    baseline = json.loads((ROOT/'regions/ireland/preservation-baseline.json').read_text())
    config = json.loads((ROOT/'garmin/config.json').read_text())
    revision = config.get('garminPackageRevision')
    manifest = ROOT/'garmin/releases'/str(revision)/'manifest.json'
    # A new compiler configuration is not an accepted release until promoted.
    if not manifest.exists():
        report=ROOT/'garmin/build-report.json'
        if report.exists():
            accepted=json.loads(report.read_text()).get('garminPackageRevision')
            candidate=ROOT/'garmin/releases'/str(accepted)/'manifest.json'
            if candidate.exists():revision=accepted;manifest=candidate
    if manifest.exists():
        released = json.loads(manifest.read_text())
        if released['garminPackageRevision'] != revision:
            raise ValueError('Wrong accepted Garmin preservation revision')
        baseline['files']['garmin/dist/OpenBareMap-Ireland.img'] = released['regions']['ireland']['sha256']
        baseline['garminPackageRevision'] = revision
    return baseline
