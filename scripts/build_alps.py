#!/usr/bin/env python3
"""Acquire, build and validate the four new Alpine editions as one batch."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from shapely.geometry import Point

from garmin_render_coverage import read_poly
from openbaremap import ROOT
from prepare_norway_shared_terrain import main as prepare_shared_terrain
from regions import ALPS_REGIONS, profile, region_path


def run(script, *args):
    subprocess.run([sys.executable, script, *args], cwd=ROOT, check=True)


def build():
    snapshot = set()
    for region in ALPS_REGIONS:
        run('scripts/fetch_region.py', '--region', region, '--stage', 'osm')
        source = json.loads(region_path(region, 'sources.lock.json').read_text())
        snapshot.add((source['inputs'][0]['sha256'], source['osm']['replicationTimestamp']))
        outline = read_poly(ROOT / source['polygons'][0]['path'])
        for name, (lon, lat, _) in profile(region)['destinations'].items():
            if not outline.covers(Point(lon, lat)):
                raise ValueError(f'{region} source outline excludes {name}')
    if len(snapshot) != 1:
        raise ValueError('The Alpine editions must use the same OSM snapshot.')

    for stage in ('terrain', 'padding'):
        for region in ALPS_REGIONS:
            run('scripts/fetch_region.py', '--region', region, '--stage', stage)

    prepare_shared_terrain(ALPS_REGIONS, 'alps')

    for region in ALPS_REGIONS:
        run('scripts/run_full_region.py', '--region', region)

    catalog = ROOT / 'work/alps-app-bundles-v1/catalog.json'
    if not catalog.is_file():
        run('scripts/build_app_distribution.py', '--output', str(catalog.parent),
            '--catalog', str(catalog), '--regions', *ALPS_REGIONS)

    origin = 'http://127.0.0.1:8768'
    preview = ROOT / 'work/alps-web-2.0.0'
    if not (preview / 'manifest.json').is_file():
        cached_preview = ROOT / 'work/faroe-islands-web-2.0.0'
        cached_args = ('--cached-preview', str(cached_preview)) if cached_preview.exists() else ()
        run('scripts/build_web_previews.py', '--output', str(preview),
            '--origin', origin, '--regions', *ALPS_REGIONS, *cached_args)
    print(f'All four new Alps editions built. Serve {preview.relative_to(ROOT)} at {origin}.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        build()
    except ValueError as error:
        sys.exit(str(error))
    except subprocess.CalledProcessError as error:
        sys.exit(f'Alps build stopped in {Path(error.cmd[1]).name}. See the error above.')
