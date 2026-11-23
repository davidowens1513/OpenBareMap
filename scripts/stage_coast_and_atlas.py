#!/usr/bin/env python3
"""Stage or publish Rota Vicentina, High Atlas & Toubkal and the Lycian Way."""

import argparse
from functools import partial
from pathlib import Path

from openbaremap import ROOT
from regions import COAST_AND_ATLAS_REGIONS
from stage_mountain_editions import publish, stage
from stage_worldwide_trekking import merge_worldwide_catalogue, render_homepage


OUTPUT = ROOT / 'work/coast-and-atlas-publication'
ARCHIVE = 'appsbyonzy-coast-and-atlas.zip'
GROUPS = (
    ('portugal', 'Portugal', 'rota-vicentina'),
    ('morocco', 'Morocco', 'high-atlas-toubkal'),
    ('turkiye', 'Türkiye', 'lycian-way'),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--website', type=Path, required=True)
    parser.add_argument('--worldwide-baseline', type=Path)
    parser.add_argument('--publish-assets', action='store_true')
    args = parser.parse_args()
    regions = COAST_AND_ATLAS_REGIONS
    homepage = partial(render_homepage, groups=GROUPS)
    if args.publish_assets:
        manifests = {f'../{region}-release/preview/manifest.json': f'{region}-manifest.json' for region in regions}
        publish(OUTPUT, args.website, regions=regions, render_homepage=homepage, preview_manifests=manifests)
    else:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        stage(OUTPUT, args.website, regions=regions, render=homepage, archive=ARCHIVE, version_garmin=True)
        if args.worldwide_baseline:
            merge_worldwide_catalogue(OUTPUT / 'worldwide-catalog-v1.json', args.worldwide_baseline, regions=regions)


if __name__ == '__main__':
    main()
