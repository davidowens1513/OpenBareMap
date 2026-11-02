# Sierra Nevada · Spain

The map covers the official Sierra Nevada National Park plus 25,000 metres
around its boundary, calculated in ETRS89 / UTM 30N (EPSG:25830). The buffered
footprint covers about 7,607 km². It uses the national park proper, excluding
the surrounding Natural Park and protection zone as the basis for the buffer.

The MITECO/OAPN boundary download is pinned by its KML SHA-256. The source page
labels this layer February 2023; this is not a claim of a new 2026 legal survey.
Boundary attribution: Fuente: Organismo Autónomo Parques Nacionales, CC BY 4.0.
`boundary-source.json` records the source, calculations and coverage bounds.

OpenStreetMap is the complete Geofabrik Andalucía snapshot of 31 October 2026.
Terrain uses the pinned Terrain Tiles / Mapzen composite at approximately 30 m,
with smoothed 20 m contours and 100 m index contours. Spanish name fallback and
ETRS89 / UTM 30N grids are included. `coverage.geojson` is the exact footprint;
mobile/web styles embed the park, coverage and outside-mask geometry offline.

Garmin family 4835 and tile IDs 48350001–48359999 are reserved for this edition.
Garmin uses rectangular native tiles selected with a conservative convex
coverage envelope, retaining the full park and 25 km area. Additional tile
context can appear beyond the dashed coverage line. Exact park and coverage
outlines are included as native line overlays. Land geometry extends beyond
the selection so coastal/background polygons remain present at low detail.
The map is display-only with native elevation and no turn-by-turn routing.
Automated binary checks are recorded separately from actual hardware testing.

## Build

Use the repository's pinned Python dependencies, Tilemaker, GDAL and Garmin
compiler tools described in the regional build reference. Prepare the pinned
boundary/profile, then run the regional build and integration-kit exporter:

```sh
PYTHONPATH=work/python python3 scripts/prepare_sierra_nevada.py
PYTHONPATH=work/python python3 scripts/run_full_region.py --region sierra-nevada
PYTHONPATH=work/python python3 scripts/build_app_distribution.py --regions sierra-nevada
```

Builders refuse to overwrite accepted map files or existing integration-kit
payloads. The selected release is `active-map.json`; the public integration
catalog is `distribution/app-bundles-v1/catalog.json` at repository root.
