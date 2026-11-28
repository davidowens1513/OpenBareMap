#!/usr/bin/env python3
"""Stage or publish the eight-map November 2026 OpenBareMap release."""

from openbaremap import ROOT
from regions import EIGHT_MAP_RELEASE_REGIONS
from stage_map_collection import collection_cli


OUTPUT = ROOT / 'work/eight-map-publication'
COUNTRIES = {
    'gran-sasso': 'Italy',
    'northern-drakensberg': 'South Africa & Lesotho',
    'cape-peninsula': 'South Africa',
    'mount-rainier': 'USA',
    'vancouver-island-west-coast-trail': 'Canada',
    'garibaldi-whistler': 'Canada',
    'cotopaxi-quilotoa': 'Ecuador',
    'aconcagua': 'Argentina & Chile',
}
GROUPS = {
    'western-europe': ('Western Europe', ('gran-sasso',)),
    'africa': ('Africa', ('northern-drakensberg', 'cape-peninsula')),
    'north-america': ('North America', (
        'mount-rainier', 'vancouver-island-west-coast-trail', 'garibaldi-whistler',
    )),
    'south-america': ('South America', ('cotopaxi-quilotoa', 'aconcagua')),
}


if __name__ == '__main__':
    collection_cli(__doc__, OUTPUT, EIGHT_MAP_RELEASE_REGIONS, COUNTRIES, GROUPS)
