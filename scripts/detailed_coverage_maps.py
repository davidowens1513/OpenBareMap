#!/usr/bin/env python3
"""Generate contextual coverage SVGs for the November 2026 nine-map release."""

from html import escape
import json
import math

from shapely.geometry import shape

from openbaremap import ROOT
from regions import profile


SPECS = {
    'north-cascades': {
        'labels': [('marblemount', 10, -10), ('cascade-pass', 10, 34), ('sahale-arm', 10, -22)],
        'roads': [[(-121.55, 48.52), (-121.244, 48.527), (-121.10, 48.57), (-120.75, 48.59)], [(-121.244, 48.527), (-121.17, 48.50), (-121.075, 48.475)]],
        'rivers': [[(-121.55, 48.50), (-121.30, 48.52), (-121.12, 48.50), (-120.82, 48.57)]],
        'road_labels': [('SR 20', -121.38, 48.535), ('Cascade River Road', -121.19, 48.485)], 'scale': 10,
    },
    'white-mountains': {
        'labels': [('mount-washington', 10, -14), ('pinkham-notch', 10, 28), ('crawford-notch', -175, 24), ('franconia-notch', -170, -10), ('lincoln', 10, 24)],
        'roads': [[(-71.95, 44.08), (-71.68, 44.17), (-71.67, 44.30)], [(-71.72, 44.45), (-71.35, 44.39), (-71.05, 44.39)], [(-71.65, 44.18), (-71.414, 44.219), (-71.253, 44.257), (-71.05, 44.20)]],
        'rivers': [[(-71.70, 44.43), (-71.55, 44.28), (-71.43, 44.10), (-71.34, 43.85)]],
        'road_labels': [('I-93', -71.70, 44.12), ('US 302', -71.45, 44.22), ('US 2', -71.27, 44.40)], 'scale': 20,
    },
    'san-juan-mountains': {
        'labels': [('ouray', 10, -10), ('silverton', 10, 25), ('telluride', -115, -10), ('red-mountain-pass', 10, -10), ('ice-lakes-basin', -175, 24)],
        'roads': [[(-107.67, 38.15), (-107.672, 38.023), (-107.711, 37.898), (-107.665, 37.812), (-107.59, 37.65)], [(-108.15, 37.94), (-107.812, 37.937), (-107.72, 37.90)]],
        'rivers': [[(-107.71, 38.12), (-107.67, 38.02), (-107.67, 37.81), (-107.60, 37.65)]],
        'waters': [[(-107.80, 37.83), (-107.77, 37.84), (-107.74, 37.82), (-107.77, 37.79)]],
        'road_labels': [('US 550', -107.69, 37.94), ('CO 145', -107.98, 37.89)], 'scale': 20,
    },
    'aoraki-mount-cook-westland': {
        'labels': [('franz-josef', 10, -10), ('fox-glacier', -120, 25), ('aoraki-village', -225, 25), ('hooker-valley', -180, -12), ('tasman-glacier', 10, -10)],
        'land': [[(169.75, -43.80), (170.45, -43.80), (170.45, -43.20), (170.13, -43.20), (170.08, -43.30), (170.01, -43.43), (169.95, -43.57), (169.88, -43.70), (169.75, -43.76)]],
        'roads': [[(170.08, -43.20), (170.181, -43.387), (170.017, -43.465), (169.91, -43.80)], [(170.45, -43.80), (170.31, -43.72), (170.097, -43.735)]],
        'rivers': [[(170.18, -43.58), (170.24, -43.70), (170.38, -43.80)]],
        'waters': [[(170.28, -43.64), (170.45, -43.70), (170.45, -43.80), (170.35, -43.80), (170.25, -43.69)]],
        'road_labels': [('SH 6', 169.96, -43.55), ('SH 80', 170.29, -43.72)], 'scale': 10,
    },
    'upper-svaneti': {
        'labels': [('mestia', -75, -12), ('chalaadi-glacier', -210, -12), ('adishi', 10, -16), ('ushguli', 10, 25), ('shkhara-glacier', 10, 28)],
        'roads': [[(42.20, 43.04), (42.727, 43.045), (42.853, 43.039), (42.99, 42.998), (43.017, 42.916), (43.35, 42.86)]],
        'rivers': [[(42.20, 43.07), (42.727, 43.02), (42.90, 42.98), (43.017, 42.91), (43.25, 42.82)]],
        'road_labels': [('Zugdidi–Mestia road', 42.45, 43.06)], 'scale': 30,
    },
    'jordan-trail-dana-petra-wadi-rum': {
        'labels': [('dana', 10, -12), ('feynan', -100, 25), ('little-petra', -150, -12), ('petra', 10, 25), ('al-humeima', 10, -12), ('wadi-rum', 10, 25)],
        'land_fill': '#eee3cd',
        'roads': [[(35.65, 30.85), (35.611, 30.675), (35.52, 30.45), (35.478, 30.322), (35.344, 29.955), (35.42, 29.576), (35.45, 29.40)], [(35.82, 30.85), (35.82, 29.40)]],
        'waters': [[(35.10, 30.85), (35.27, 30.85), (35.24, 30.63), (35.10, 30.45)]],
        'road_labels': [('King’s Highway', 35.57, 30.48), ('Desert Highway', 35.69, 30.08)], 'scale': 20,
        'route': 'regions/jordan-trail-dana-petra-wadi-rum/jordan-trail-route.geojson',
    },
    'cordillera-blanca': {
        'labels': [('huaraz', 10, 25), ('huascaran', 10, 32), ('cashapampa', -150, 25), ('llanganuco', 10, -14)],
        'roads': [[(-77.82, -10.10), (-77.528, -9.53), (-77.744, -9.141), (-77.72, -8.70), (-77.70, -8.30)], [(-77.744, -9.141), (-77.65, -9.05), (-77.489, -9.008)]],
        'rivers': [[(-77.76, -8.30), (-77.75, -9.14), (-77.58, -9.53), (-77.55, -10.10)]],
        'waters': [[(-77.68, -9.08), (-77.63, -9.07), (-77.61, -9.04), (-77.66, -9.02)]],
        'road_labels': [('PE-3N', -77.67, -9.63)], 'scale': 30,
    },
    'cordillera-huayhuash': {
        'labels': [('chiquian', -125, -12), ('llamac', 10, 25), ('cuartelhuain', 10, -12), ('carhuacocha', 10, -12), ('huayhuash', 10, 25), ('cajatambo', 10, 25)],
        'roads': [[(-77.35, -10.10), (-77.155, -10.151), (-76.989, -10.138), (-76.883, -10.084)], [(-77.15, -10.75), (-76.994, -10.474), (-76.917, -10.40)]],
        'rivers': [[(-76.90, -9.80), (-76.91, -10.27), (-76.99, -10.47), (-77.05, -10.75)]],
        'waters': [[(-76.96, -10.30), (-76.91, -10.29), (-76.89, -10.25), (-76.94, -10.24)], [(-76.94, -10.44), (-76.89, -10.43), (-76.88, -10.39), (-76.92, -10.38)]],
        'road_labels': [('Chiquián approach', -77.23, -10.17)], 'scale': 30,
    },
    'cerro-castillo': {
        'labels': [('las-horquetas', -155, -12), ('laguna-chiguay', 10, -12), ('cerro-castillo', -155, -12), ('laguna-castillo', -175, 25), ('villa-cerro-castillo', 10, 25)],
        'roads': [[(-72.20, -45.55), (-72.187, -45.907), (-72.067, -45.962), (-72.07, -46.119), (-71.82, -46.45)]],
        'rivers': [[(-72.30, -45.70), (-72.19, -45.91), (-72.17, -46.08), (-72.07, -46.12), (-71.80, -46.30)]],
        'waters': [[(-72.20, -46.10), (-72.16, -46.10), (-72.14, -46.07), (-72.18, -46.05)], [(-72.10, -45.98), (-72.05, -45.98), (-72.04, -45.95), (-72.08, -45.94)]],
        'road_labels': [('Carretera Austral · Route 7', -72.12, -45.78)], 'scale': 20,
    },
}


def coverage_svg(region):
    metadata = profile(region)
    spec = SPECS[region]
    west, south, east, north = metadata['bounds']
    pad_x, pad_y, map_width, map_height = 50, 30, 740, 390

    def point(coordinate):
        x = pad_x + (coordinate[0] - west) / (east - west) * map_width
        y = pad_y + (north - coordinate[1]) / (north - south) * map_height
        return x, y

    def path_line(coordinates, close=False):
        values = [point(coordinate) for coordinate in coordinates]
        return 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in values) + ('Z' if close else '')

    def geometry_path(geometry):
        tolerance = max(east - west, north - south) / 700
        geometry = geometry.simplify(tolerance, preserve_topology=True)
        polygons = geometry.geoms if geometry.geom_type == 'MultiPolygon' else (geometry,)
        pieces = []
        for polygon in polygons:
            pieces.append(path_line(polygon.exterior.coords, True))
            pieces.extend(path_line(ring.coords, True) for ring in polygon.interiors)
        return ' '.join(pieces)

    coverage = shape(json.loads((ROOT / 'regions' / region / 'garmin/render-coverage.geojson').read_text())['features'][0]['geometry'])
    label = escape(metadata['label'])
    background = spec.get('land_fill', '#f5f3e9')
    layers = [f'<rect width="840" height="450" fill="#d7e9ef"/>']
    land = spec.get('land')
    if land:
        layers.extend(f'<path d="{path_line(polygon, True)}" fill="{background}" stroke="#8faab1" stroke-width="1.7"/>' for polygon in land)
    else:
        layers.append(f'<rect x="0" y="0" width="840" height="450" fill="{background}"/>')
    layers.extend(f'<path d="{path_line(polygon, True)}" fill="#b9dce8" stroke="#88b7c7" stroke-width="1.6"/>' for polygon in spec.get('waters', []))
    layers.extend(f'<path d="{path_line(line)}" fill="none" stroke="#9bc8d7" stroke-width="5" stroke-linecap="round"/>' for line in spec.get('rivers', []))
    for road in spec.get('roads', []):
        road_path = path_line(road)
        layers.append(f'<path d="{road_path}" fill="none" stroke="#fffefa" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>')
        layers.append(f'<path d="{road_path}" fill="none" stroke="#b68a57" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>')
    layers.append(f'<path d="{geometry_path(coverage)}" fill="#55a265" fill-opacity=".26" stroke="#146b35" stroke-width="3.3" stroke-linejoin="round" fill-rule="evenodd"/>')
    if spec.get('route'):
        route = json.loads((ROOT / spec['route']).read_text())
        for feature in route['features']:
            geometry = shape(feature['geometry']).simplify(.001, preserve_topology=True)
            lines = geometry.geoms if geometry.geom_type == 'MultiLineString' else (geometry,)
            layers.extend(f'<path d="{path_line(line.coords)}" fill="none" stroke="#7337a8" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>' for line in lines)

    destinations = metadata['destinations']
    destination_labels = metadata['destinationLabels']
    labels = []
    for key, dx, dy in spec['labels']:
        x, y = point(destinations[key][:2])
        labels.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5"/><text x="{x + dx:.1f}" y="{y + dy:.1f}">{escape(destination_labels[key])}</text>')
    road_labels = []
    for text, longitude, latitude in spec.get('road_labels', []):
        x, y = point((longitude, latitude))
        road_labels.append(f'<text x="{x:.1f}" y="{y:.1f}" transform="rotate(-8 {x:.1f} {y:.1f})">{escape(text)}</text>')

    middle_latitude = (south + north) / 2
    width_km = (east - west) * 111.32 * math.cos(math.radians(middle_latitude))
    scale_km = spec['scale']
    scale_pixels = map_width * scale_km / width_km
    scale_start = min(590, 750 - scale_pixels)
    footer_route = ''
    if spec.get('route'):
        footer_route = '<path d="M315 474H355" stroke="#7337a8" stroke-width="5" stroke-linecap="round"/><text x="368" y="483">Jordan Trail</text>'

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 498" role="img">
<title>{label} map coverage</title>
<defs><clipPath id="map"><rect width="840" height="450"/></clipPath></defs>
<g clip-path="url(#map)">{''.join(layers)}
<g fill="#1c3026" stroke="#fffefa" stroke-width="4" paint-order="stroke" stroke-linejoin="round" font-family="Arial,sans-serif" font-size="21" font-weight="700">{''.join(labels)}</g>
<g fill="#765f43" stroke="#fffefa" stroke-width="3" paint-order="stroke" font-family="Arial,sans-serif" font-size="17" font-weight="700">{''.join(road_labels)}</g>
<g fill="#1c3026" font-family="Arial,sans-serif" font-size="23" font-weight="700" text-anchor="middle"><rect x="784" y="13" width="43" height="62" rx="9" fill="#fffefa" fill-opacity=".88"/><text x="805.5" y="39">N</text><path d="M805.5 46l-8 18 8-5 8 5z"/></g></g>
<g font-family="Arial,sans-serif" font-size="24" fill="#1c3026"><rect y="450" width="840" height="48" fill="#fafbf7"/><path d="M0 450H840" stroke="#c8d5c6"/><rect x="20" y="464" width="25" height="20" rx="3" fill="#c2ddbf" stroke="#146b35" stroke-width="2.5"/><text x="57" y="483">Map coverage</text>{footer_route}<path d="M{scale_start} 467v12h{scale_start + scale_pixels:.1f}v-12" fill="none" stroke="#1c3026" stroke-width="2.5"/><text x="{scale_start + scale_pixels + 14:.1f}" y="483">{scale_km} km</text></g></svg>\n'''


if __name__ == '__main__':
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument('--region', choices=sorted(SPECS), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(coverage_svg(args.region))
