# OpenBareMap 2.0

OpenBareMap is an offline topographic map for hiking, available as separate regional versions for **Ireland**, **England & Wales**, **Scotland** and **Sierra Nevada, Spain**. Each edition has **20 m contours**, its own source coverage, map databases and platform packages. Mobile bundles are integration components for apps using MapLibre Native; Garmin downloads are display-only maps.

## Downloads and incorporation instructions

Each iOS download contains the complete regional resource bundle, Swift loader, example view controller, dependency information and instructions. Each Android download contains the complete importable map ZIP, loader AAR and Kotlin source, an example Activity, dependency information and instructions. Both include checksums, legends and attribution. Install the MapLibre renderer through the dependency instructions supplied with the bundle.

| Region | iOS Bundle | Android Bundle | Garmin |
| --- | --- | --- | --- |
| Ireland | [Download](https://downloads.appsbyonzy.dev/OpenBareMap/ireland/2.0.0/app-bundles-v1/ios/OpenBareMap-Ireland-iOS-Bundle.zip) · [Instructions](https://downloads.appsbyonzy.dev/OpenBareMap/ireland/2.0.0/app-bundles-v1/ios/instructions.txt) | [Download](https://downloads.appsbyonzy.dev/OpenBareMap/ireland/2.0.0/app-bundles-v1/android/OpenBareMap-Ireland-Android-Bundle.zip) · [Instructions](https://downloads.appsbyonzy.dev/OpenBareMap/ireland/2.0.0/app-bundles-v1/android/instructions.txt) | [Download](https://downloads.appsbyonzy.dev/Garmin/OpenBareMap-Ireland.img) · [Instructions](https://downloads.appsbyonzy.dev/Garmin/instructions.txt) |
| England & Wales | [Download](https://downloads.appsbyonzy.dev/OpenBareMap/england-wales/2.0.0/app-bundles-v1/ios/OpenBareMap-England-Wales-iOS-Bundle.zip) · [Instructions](https://downloads.appsbyonzy.dev/OpenBareMap/england-wales/2.0.0/app-bundles-v1/ios/instructions.txt) | [Download](https://downloads.appsbyonzy.dev/OpenBareMap/england-wales/2.0.0/app-bundles-v1/android/OpenBareMap-England-Wales-Android-Bundle.zip) · [Instructions](https://downloads.appsbyonzy.dev/OpenBareMap/england-wales/2.0.0/app-bundles-v1/android/instructions.txt) | [Download](https://downloads.appsbyonzy.dev/Garmin/OpenBareMap-England-Wales.img) · [Instructions](https://downloads.appsbyonzy.dev/Garmin/england-wales-instructions.txt) |
| Scotland | [Download](https://downloads.appsbyonzy.dev/OpenBareMap/scotland/2.0.0/app-bundles-v1/ios/OpenBareMap-Scotland-iOS-Bundle.zip) · [Instructions](https://downloads.appsbyonzy.dev/OpenBareMap/scotland/2.0.0/app-bundles-v1/ios/instructions.txt) | [Download](https://downloads.appsbyonzy.dev/OpenBareMap/scotland/2.0.0/app-bundles-v1/android/OpenBareMap-Scotland-Android-Bundle.zip) · [Instructions](https://downloads.appsbyonzy.dev/OpenBareMap/scotland/2.0.0/app-bundles-v1/android/instructions.txt) | [Download](https://downloads.appsbyonzy.dev/Garmin/OpenBareMap-Scotland.img) · [Instructions](https://downloads.appsbyonzy.dev/Garmin/scotland-instructions.txt) |
| Sierra Nevada (Spain) | [Download](https://downloads.appsbyonzy.dev/OpenBareMap/sierra-nevada/2.0.0/app-bundles-v1/ios/OpenBareMap-Sierra-Nevada-iOS-Bundle.zip) · [Instructions](https://downloads.appsbyonzy.dev/OpenBareMap/sierra-nevada/2.0.0/app-bundles-v1/ios/instructions.txt) | [Download](https://downloads.appsbyonzy.dev/OpenBareMap/sierra-nevada/2.0.0/app-bundles-v1/android/OpenBareMap-Sierra-Nevada-Android-Bundle.zip) · [Instructions](https://downloads.appsbyonzy.dev/OpenBareMap/sierra-nevada/2.0.0/app-bundles-v1/android/instructions.txt) | [Download](https://downloads.appsbyonzy.dev/Garmin/OpenBareMap-Sierra-Nevada.img) · [Instructions](https://downloads.appsbyonzy.dev/Garmin/sierra-nevada-instructions.txt) |

The outer Android Bundle ZIP must be extracted first. The included `OpenBareMap-Resources.zip` is the input to the Android loader. The iOS bundle is copied intact into the app target or opened from persistent application storage. Region-specific instructions cover setup, dependency versions, verification, offline use and attribution. Each download's R2 folder contains `SHA256SUMS.txt` and a manifest.

## Regional coverage

| Region | Coverage | OSM snapshot | Grid / regional labels | Selected databases | Garmin family ID |
| --- | --- | --- | --- | --- | --- |
| Ireland | Whole island, Northern Ireland and offshore islands | 24 October 2026 | Irish Grid and townlands | [Ireland](active-map.json) | 4831 |
| England & Wales | Complete England and Wales extracts, including offshore islands | 30 October 2026 | British National Grid; Welsh name fallback | [England/Wales](regions/england-wales/active-map.json) | 4833 |
| Scotland | Complete Scotland extract, including the Hebrides, Orkney, Shetland, St Kilda and Rockall | 31 October 2026 | British National Grid; Scottish Gaelic name fallback | [Scotland](regions/scotland/active-map.json) | 4834 |
| Sierra Nevada (Spain) | Official national park plus 25 km around its boundary, about 7,607 km² | 31 October 2026 | ETRS89 / UTM 30N (EPSG:25830); Spanish name fallback | [Sierra Nevada](regions/sierra-nevada/active-map.json) | 4835 |

Sierra Nevada uses the MITECO/OAPN national park boundary and a 25,000 m buffer calculated in ETRS89 / UTM 30N. The purple line marks the park and the dashed line marks the buffered coverage. Mobile and web styles mask tile padding outside that footprint. Garmin uses a conservative tile envelope containing the whole footprint and can show additional context; both boundary lines are included. [Boundary provenance](regions/sierra-nevada/boundary-source.json).

## The map

- Terrain: gently smoothed 20 m contours, 100 m index contours, hillshade, summit and saddle names, summit dots and cliff markings.
- Land cover: woodland, farmland, grass, heath, scrub, wetlands, textured bog, peat workings, rock, scree, sand and beaches.
- Transport: roads, bridges and tunnels, tracks, paths, footways, bridleways, cycleways, steps, walking/cycling routes, railways and ferries.
- Places and facilities: settlements, islands, water names, outdoor facilities, parking and regional labels.
- Offline resources: local databases, styles, fonts, sprites, legends and attribution notices.

Mobile and web maps share cartography. Garmin uses its native fonts, symbols, terrain presentation and detail levels. All Garmin editions are display-only, with native elevation data and no turn-by-turn routing. Regional filenames and identifiers allow the Garmin maps to coexist. Follow the linked generic installation instructions and the mapping product's manual.

## Public previews — all regions

| Region | Map preview | Zoomable key |
| --- | --- | --- |
| Ireland | [Open map preview](https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/ireland/index.html) | <a href="https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/ireland/legend.html"><img src="https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/assets/legends/ireland@2x.png" width="160" alt="Ireland map key — click to open and zoom"></a> |
| England & Wales | [Open map preview](https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/england-wales/index.html) | <a href="https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/england-wales/legend.html"><img src="https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/assets/legends/england-wales@2x.png" width="160" alt="England & Wales map key — click to open and zoom"></a> |
| Scotland | [Open map preview](https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/scotland/index.html) | <a href="https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/scotland/legend.html"><img src="https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/assets/legends/scotland@2x.png" width="160" alt="Scotland map key — click to open and zoom"></a> |
| Sierra Nevada (Spain) | [Open map preview](https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/sierra-nevada/index.html) | <a href="https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/sierra-nevada/legend.html"><img src="https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/assets/legends/sierra-nevada@2x.png" width="160" alt="Sierra Nevada (Spain) map key — click to open and zoom"></a> |

Click a key to open its full-size legend with zoom controls, fit-to-page and image download. The website previews use these same legend pages. Ireland uses the Irish Grid key; England & Wales and Scotland use British National Grid keys. Sierra Nevada uses an ETRS89 / UTM 30N key with the national park and 25 km coverage lines.

Each preview displays the complete selected map with regional destinations. Online previews load tiles as needed and remain separate from offline downloads. See [web preview packaging](web-preview/README.md).


The previews retain a directly overhead view. Pan, zoom, regional destinations and the separate zoomable map keys are available for every edition.

## App integration

For iOS, add the full `OpenBareMap.bundle` as a resource and the supplied Swift loader to the application target, then load its resolved style using MapLibre. The kit includes a UIKit example suitable for adaptation to UIKit or SwiftUI. Use explicit Bundle URLs when an app contains multiple regions.

For Android, add the supplied loader AAR or Kotlin source and the documented renderer dependencies. Install the inner resource ZIP on a worker thread into persistent app-private storage, then load the resolved style on the main thread. The example includes MapView lifecycle handling, map import, legend and credits.

The bundles contain map data and integration support. The consuming app supplies its renderer dependency, interface, signing, distribution and any location features. Check resource integrity, rendering, memory use and offline behavior with the app's selected SDK and deployment targets. [Android integration](android/README.md) and [iOS integration](ios/README.md) describe the repository components.

## Source, export and local viewing

Git LFS stores the large source archives, map databases and binary outputs. Restore the required LFS files before exporting; pointer files cannot be used as map resources. Existing commands without a region argument select Ireland.

```sh
git lfs install --local
git lfs pull

# Separate resource exports; destinations must be new.
python3 ios/build_bundle.py --region scotland --output /absolute/new/scotland-ios
python3 android/build_package.py --region scotland --output /absolute/new/scotland-android

# Local viewers
python3 scripts/serve.py --region ireland --port 8765
python3 scripts/serve.py --region england-wales --port 8766
python3 scripts/serve.py --region scotland --port 8767
```

Use `ireland`, `england-wales`, `scotland` or `sierra-nevada` for the resource exporters. The versioned integration kits are assembled by `scripts/build_app_distribution.py`; [distribution packaging](distribution/README.md) describes their contents and storage. [Regional build reference](docs/regional-editions.md) covers sources and full map builds. The England/Wales basemap is stored as verified LFS parts and restored automatically when selected; allow space for the parts and reconstructed database.

## Data and attribution

OpenStreetMap-derived data uses the [Open Database Licence](https://opendatacommons.org/licenses/odbl/1-0/) with [OpenStreetMap attribution](https://www.openstreetmap.org/copyright). Bundles include the applicable map, font and terrain notices. Sierra Nevada national park boundaries are credited to Organismo Autónomo Parques Nacionales (MITECO/OAPN), CC BY 4.0, with source details in the regional provenance. Consuming apps must make those notices accessible to users.

Elevation comes from approximately 30 m composite Terrain Tiles data, including Copernicus EU-DEM, USGS and NOAA sources. The 20 m contour interval describes line spacing rather than terrain accuracy. [Terrain attribution](viewer/terrain-attribution.html) and the regional source locks identify the inputs.

Source completeness, geographic accuracy and readability depend on the input data and renderer. Cliff symbols are not certified as indicating the downhill side; access tags do not establish route suitability or access rights. Townland, grid and inherited font provenance is described in the source records.

| Reference | Location |
| --- | --- |
| Ireland source and terrain locks | [OSM](sources.lock.json), [terrain](terrain-sources.lock.json) |
| England/Wales source and terrain locks | [OSM](regions/england-wales/sources.lock.json), [terrain](regions/england-wales/terrain-sources.lock.json) |
| Scotland source and terrain locks | [OSM](regions/scotland/sources.lock.json), [terrain](regions/scotland/terrain-sources.lock.json) |
| Shared coastline and inherited assets | [Coast](coast-sources.lock.json), [reference assets](legacy-assets.lock.json) |
| Sierra Nevada source, terrain and park boundary | [OSM](regions/sierra-nevada/sources.lock.json), [terrain](regions/sierra-nevada/terrain-sources.lock.json), [park boundary](regions/sierra-nevada/boundary-source.json) |
| Integration bundle catalog | [Catalog](distribution/app-bundles-v1/catalog.json) |
| Platform references | [Garmin](garmin/README.md), [Android](android/README.md), [iOS](ios/README.md) |
