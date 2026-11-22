"""Classify selected OSM outlines using the published Pyrenean ice inventories."""

import argparse
import json
from pathlib import Path

from openbaremap import digest, write

ATTRIBUTION = ('Selected OpenStreetMap ice outlines are approximate and can overstate current extent. '
               'Classification uses the 2023 survey and OPCC 2024 inventory. '
               'In 2026 the Aneto survey reported four separate ice bodies.')

GLACIERS = {
    "Glacier d'Arcouzan", "Glacier d'Ossoue", 'Glacier de Las Néous',
    'Glacier de la Munia', 'Glacier des Oulettes de Gaube', 'Glacier du Petit Vignemale',
    'Glacier du Taillon', 'Glaciar de Llardana', 'Glaciar de Tempestades',
    'Glaciar de la Maladeta', 'Glaciar del Aneto', 'Glaciar del Infierno',
    'Seil de la Baque Est',
}
ICE_PATCHES = {
    "Glacier d'Astazou", 'Glacier de Barroude', 'Glacier de Pailla Ouest',
    'Glacier des Gabiétous', 'Glacier du Montferrat', 'Glacier du Pabat',
    'Glaciar Occidental de la Madaleta', 'Glaciar de Barrancs', 'Glaciar de la Paúl',
}


def reviewed_outline(feature):
    from shapely.geometry import shape

    properties = feature['properties']
    name = properties.get('name')
    if name == 'Glaciar Monte Perdido':
        # The locked extract uses the same name for the lower and upper bodies.
        kind = 'glacier' if shape(feature['geometry']).centroid.y > 42.68 else 'permanent_snow'
    elif name in GLACIERS:
        kind = 'glacier'
    elif name in ICE_PATCHES:
        kind = 'permanent_snow'
    else:
        return None
    return {**feature, 'properties': {**properties, 'class': kind}}


def review(source, destination):
    collection = json.loads(source.read_text())
    features = [reviewed for feature in collection['features'] if (reviewed := reviewed_outline(feature))]
    counts = {kind: sum(f['properties']['class'] == kind for f in features)
              for kind in ('glacier', 'permanent_snow')}
    if not all(counts.values()):
        raise ValueError('The reviewed source is missing glacier or ice patch geometry')
    write(destination, {**collection, 'features': features})
    return {'sourceGeometrySHA256': digest(source), 'geometrySHA256': digest(destination),
            'sourcePolygons': len(collection['features']), 'permanentIce': counts}


def patch_preview(style_file, reviewed_geometry, output):
    """Use the reviewed ice with the already published preview tiles."""
    style = json.loads(style_file.read_text())
    style['sources']['reviewed-ice'] = {'type': 'geojson', 'maxzoom': 14,
                                        'data': json.loads(reviewed_geometry.read_text())}
    style['sources']['basemap']['attribution'] = (
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> · ' + ATTRIBUTION)
    for layer in style['layers']:
        if layer.get('source-layer') == 'permanent_ice':
            del layer['source-layer']
            layer['source'] = 'reviewed-ice'
    output.write_text(json.dumps(style, ensure_ascii=False, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--preview-style', type=Path)
    parser.add_argument('--preview-output', type=Path)
    args = parser.parse_args()
    if bool(args.preview_style) != bool(args.preview_output):
        parser.error('--preview-style and --preview-output must be used together')
    print(json.dumps(review(args.source, args.destination)))
    if args.preview_style:
        patch_preview(args.preview_style, args.destination, args.preview_output)
