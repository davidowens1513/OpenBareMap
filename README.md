# OpenBareMap 2.0

OpenBareMap is an offline topographic map of the whole island of Ireland, including Northern Ireland and offshore islands. It provides map resources for Garmin handhelds, Android and iOS, plus a browser viewer for inspecting the map on a computer.

The map release is **2.0.0**, identified by Git tag `v2.0.0` and the [release manifest](releases/2.0.0/manifest.json). Platform packages record their source revision and resource checksums.

## The map

- **Terrain:** Gently smoothed 10-metre contours with fine overview strokes for 100 m and 50 m lines, hillshade, summit and saddle names, summit dots and fine cliff markings.
- **Land cover:** smoothed boundaries for woodland, farmland, grass, heath, scrub, wetlands, textured bog, peat workings, rock, scree, sand and beaches.
- **Transport:** roads and connecting links, tracks, paths, footways, bridleways, cycleways, steps, walking and cycling routes, railways and ferries.
- **Places and facilities:** settlements, townlands, islands, water names, outdoor facilities and points of interest. Parking uses a white P on blue; outdoor facilities use dots and text.
- **Offline resources:** local map databases, styles, symbols, fonts, legends and attribution notices. An internet connection is not required to display the installed map.

The MapLibre presentation uses Open Sans text without halos, dashed tracks and paths, bridge/tunnel styling and an Irish Grid overlay. Garmin uses native device fonts, symbols, terrain rendering and detail levels. The presentations share source data but have different rendering capabilities.

## Garmin

The Garmin edition is a **display-only map**, with no turn-by-turn routing. It includes 10-metre contours, native elevation data, land-cover textures, cliff markings, place names and outdoor features.

| Resource | Location |
| --- | --- |
| Installable map, see release manifest for file size | [OpenBareMap-Ireland.img](garmin/dist/OpenBareMap-Ireland.img) |
| Installation instructions | [INSTALL.txt](garmin/dist/INSTALL.txt) |
| Legend | [Montana-750i-Legend.png](garmin/dist/Montana-750i-Legend.png) |
| Build, integration and validation details | [Garmin guide](garmin/README.md) |

Target devices are the **Montana 750i** and **GPSMAP 67i**. The same IMG serves both devices. Version 2.0 has binary-content checks; device rendering and performance require acceptance on each model.

Install the `.img` in the device's `Garmin` folder or on a supported memory card, and enable **OpenBareMap Ireland** in the device's map controls. The 67i uses MTP for USB file transfers on macOS. Point-label text must be enabled for mountain names. Disable overlapping detailed maps and satellite imagery when viewing OpenBareMap on its own.

Personal recorded tracks can be displayed as a separate transparent map layer and switched independently of the basemap. The personal track package is separate from the basemap distributed here.

Garmin uses its own zoom and font controls. Irish Grid lines and distinct bridge/tunnel styling are not included in this edition. Set elevation units to metres for metric contour labels.

## Android

The Android edition uses **MapLibre Native** and includes a reference app and a reusable Kotlin resource loader. It supports Android 6.0 / API 23 and later.

| Resource | Location |
| --- | --- |
| Debug-signed reference app | [OpenBareMap-debug.apk](android/dist/OpenBareMap-debug.apk) |
| Reusable loader library | [openbaremap-loader-release.aar](android/dist/openbaremap-loader-release.aar) |
| Offline map resources, full-island package | [android/package/OpenBareMap](android/package/OpenBareMap/) |
| Setup, building and integration | [Android guide](android/README.md) |

Install the APK, open the app and choose **Import map** to select the map ZIP. The map, legend and credits are available offline after import. The resource package is separate from the APK; allow several GB of storage for the archive and installed map.

To generate the import ZIP from a restored checkout, run:

```sh
python3 android/build_package.py --zip-only
```

Open `android/` in Android Studio for app development. The reference app is debug-signed; production signing and distribution belong to the consuming application. Build, loader and resource-integrity checks pass. Device rendering, import performance and memory use require hardware assessment.

## iOS

The iOS edition is a **resource bundle and Swift loader for MapLibre Native**, intended for integration into an iOS application.

| Resource | Location |
| --- | --- |
| Offline resource bundle, full-island package | [OpenBareMap.bundle](ios/package/OpenBareMap.bundle/) |
| Swift loader | [OpenBareMapResources.swift](ios/OpenBareMapResources.swift) |
| Xcode integration example | [INTEGRATION.txt](ios/INTEGRATION.txt) |
| Packaging and validation | [iOS guide](ios/README.md) |

Add the complete bundle as an Xcode resource and include the Swift loader in the app target. The loader resolves local style and resource paths for MapLibre Native without a local web server. The host app supplies the renderer, map interface and access to the attribution notices.

The bundle contains map databases, townland points, styles, glyphs, sprites, a legend and provenance records. Resource integrity and Swift loader checks pass; MapLibre rendering and performance require simulator/device assessment. This package is an integration component rather than a standalone iOS app.

## Browser viewer

The repository includes a MapLibre GL JS viewer with an interactive legend. To restore the large files and open the map locally:

```sh
git clone https://github.com/davidowens1513/OpenBareMap.git
cd OpenBareMap
git lfs install --local
git lfs pull
python3 scripts/serve.py
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765) while the server is running. The viewer serves local map, font, symbol and townland resources. Its active databases and checksums are listed in [active-map.json](active-map.json).

Git LFS is required to obtain the map databases, source archives and packaged binaries. A checkout containing only LFS pointer files is not a usable offline package.

## Data, attribution and validation

The OpenStreetMap extract covers Ireland and Northern Ireland and is dated **24 October 2026**. Terrain uses approximately 30-metre composite elevation data from Terrain Tiles. The 10-metre contour interval describes line spacing, not a guarantee of 10-metre terrain accuracy.

| Source or record | Details |
| --- | --- |
| OpenStreetMap extract | [sources.lock.json](sources.lock.json) |
| Coastline data | [coast-sources.lock.json](coast-sources.lock.json) |
| Elevation grids | [terrain-sources.lock.json](terrain-sources.lock.json) |
| Townlands, Irish Grid and reference assets | [legacy-assets.lock.json](legacy-assets.lock.json) |
| Elevation source notices | [Terrain attribution](viewer/terrain-attribution.html) |
| Platform-specific source and tool records | [Garmin](garmin/README.md), [Android](android/README.md), [iOS](ios/README.md) |

OpenStreetMap-derived data is subject to the [Open Database Licence](https://opendatacommons.org/licenses/odbl/1-0/), with [OpenStreetMap attribution](https://www.openstreetmap.org/copyright). Packages include source, font and other applicable notices; consuming applications must make those notices available to users.

Source completeness, geographic accuracy and device readability require assessment independently of software tests. Cliff markings are not certified as indicating the downhill side. Source access tags do not establish a right of access or route safety. Townland, grid and font-generation recipes have incomplete provenance. Release artifacts are pinned by checksum. Exact byte-for-byte recompilation is not guaranteed; Garmin compilation has known binary differences between repeated builds.

[Map versioning and platform adaptations](docs/versioning-and-platforms.md) explains what is pinned, how each application uses the map, and the proposed release structure.

[Development history and build workflow](docs/development-history.md) describes the project's development, packaging approach and maintenance commands. [Architecture](docs/architecture.md) describes the underlying map pipeline.
