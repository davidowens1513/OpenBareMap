#!/usr/bin/env python3
"""Stage or publish the nine-map November 2026 OpenBareMap release."""

from openbaremap import ROOT
from regions import NINE_MAP_RELEASE_REGIONS
from stage_map_collection import collection_cli


OUTPUT = ROOT / 'work/nine-map-publication'
COUNTRIES = {
    'north-cascades': 'USA',
    'white-mountains': 'USA',
    'san-juan-mountains': 'USA',
    'aoraki-mount-cook-westland': 'New Zealand',
    'upper-svaneti': 'Georgia',
    'jordan-trail-dana-petra-wadi-rum': 'Jordan',
    'cordillera-blanca': 'Peru',
    'cordillera-huayhuash': 'Peru',
    'cerro-castillo': 'Chile',
}
GROUPS = {
    'north-america': ('North America', (
        'north-cascades', 'white-mountains', 'san-juan-mountains',
    )),
    'oceania': ('Oceania', ('aoraki-mount-cook-westland',)),
    'eastern-europe': ('Eastern Europe', ('upper-svaneti',)),
    'asia': ('Asia', ('jordan-trail-dana-petra-wadi-rum',)),
    'south-america': ('South America', (
        'cordillera-blanca', 'cordillera-huayhuash', 'cerro-castillo',
    )),
}


if __name__ == '__main__':
    collection_cli(__doc__, OUTPUT, NINE_MAP_RELEASE_REGIONS, COUNTRIES, GROUPS)
