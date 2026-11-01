# OpenBareMap 2.0

OpenBareMap provides two independently usable offline topographic map editions: **Ireland** and **England & Wales**. Both use shared cartography and build tools, with separate source snapshots, selected databases, packages and release records. Both releases are **2.0.0**, with **20 m contours**. Updating or exporting one region does not replace the other, and does not modify a BareGPS host app.

## Choose a region

| | Ireland | England & Wales |
| --- | --- | --- |
| Coverage | Whole island, Northern Ireland and offshore islands | Complete England and Wales extracts, including offshore islands; no pilot |
| OSM snapshot | 24 October 2026 | 30 October 2026 |
| Grid / regional labels | Irish Grid and townlands | British National Grid (EPSG:27700), Welsh name fallback; no Irish townlands |
| Selected map | [Ireland selection](active-map.json) | [England/Wales selection](regions/england-wales/active-map.json) |
| Release records | [Ireland manifest](releases/2.0.0/manifest.json) | [England/Wales manifest](releases/england-wales/2.0.0/manifest.json) |
| Garmin map | [OpenBareMap-Ireland.img](garmin/dist/OpenBareMap-Ireland.img) | [OpenBareMap-England-Wales.img](regions/england-wales/garmin/dist/OpenBareMap-England-Wales.img) |
| Garmin family ID | 4831 | 4833 |
| iOS resource bundle | `ios/package/OpenBareMap.bundle` | `regions/england-wales/ios/OpenBareMap.bundle` |
| Android resources | `android/package/OpenBareMap` | `regions/england-wales/android/OpenBareMap` |

## Export each region separately

Install Git LFS and restore the files before exporting. Each command below writes only its selected region to a new destination; existing outputs are never overwritten. The region selection is explicit, so both packages can be extracted independently from the same checkout.

```sh
# Ireland
python3 ios/build_bundle.py --region ireland --output /absolute/new/ireland-ios
python3 android/build_package.py --region ireland --output /absolute/new/ireland-android

# England & Wales
python3 ios/build_bundle.py --region england-wales --output /absolute/new/england-wales-ios
python3 android/build_package.py --region england-wales --output /absolute/new/england-wales-android
```

To download only one region’s large files after cloning with `GIT_LFS_SKIP_SMUDGE=1`, use the matching selection below. Source OSM/elevation archives are needed for rebuilding, but not for exporting the accepted maps.

```sh
# Ireland map resources and Garmin image only
git lfs pull --include="build/detail-2.0/basemap.mbtiles,build/padding-2.0/topography.mbtiles,build/hillshade-a/hillshade.mbtiles,assets/irish-grid.mbtiles,viewer/townlands.geojson,garmin/dist/OpenBareMap-Ireland.img"

# England/Wales map resources and Garmin image only
git lfs pull --include="releases/england-wales/2.0.0/maps/*.mbtiles*,regions/england-wales/garmin/dist/OpenBareMap-England-Wales.img"
```

The England/Wales basemap exceeds GitHub’s single-object limit, so Git LFS stores it as three verified parts. The viewer and resource exporters reassemble the identical database automatically when selected. You can also run `python3 scripts/restore_map_parts.py` explicitly. Allow space for both the downloaded parts and the restored database.

Each iOS export contains `OpenBareMap.bundle` and its Swift loader. Each Android export contains an `OpenBareMap` resource folder and its own `OpenBareMap-Android.zip`. Keep exports in separate region-named folders. These are map resources, not changes to an installed BareGPS app. Garmin maps already have distinct filenames and identifiers and can coexist on a device.

Open independent local previews:

```sh
python3 scripts/serve.py --region ireland --port 8765
python3 scripts/serve.py --region england-wales --port 8766
```

See [regional builds and maintenance](docs/regional-editions.md) for independent source updates and full rebuilds. Existing commands without `--region` continue to select Ireland.

## The map

- **Terrain:** Gently smoothed 20-metre contours with fine overview strokes for 100 m index lines, hillshade, summit and saddle names, summit dots and fine cliff markings.
- **Land cover:** smoothed boundaries for woodland, farmland, grass, heath, scrub, wetlands, textured bog, peat workings, rock, scree, sand and beaches.
- **Transport:** roads and connecting links, tracks, paths, footways, bridleways, cycleways, steps, walking and cycling routes, railways and ferries.
- **Places and facilities:** settlements, islands, water names, Ireland townlands, outdoor facilities and points of interest. Parking uses a white P on blue; outdoor facilities use dots and text.
- **Offline resources:** local map databases, styles, symbols, fonts, legends and attribution notices. An internet connection is not required to display the installed map.

The MapLibre presentation uses Open Sans text without halos, bridge/tunnel styling and a regional grid overlay: Irish Grid for Ireland or British National Grid for England/Wales. Paths and footways are saturated green; tracks are orange-brown, with distinct dash patterns and prominent strokes for contrast over higher-ground fills. Cliff markings use a repeating teeth pattern from zoom 11.

The shared app legend has bold dark labels, enlarged line samples and outlined colour swatches with enhanced contrast and saturation. Its samples are enhanced for readability; the map itself retains its cartographic colours. The public previews use matching regional legend images with a separate zoomable view; the local development viewer reads its legend samples from the active map style.

Garmin uses native device fonts, symbols, terrain rendering and detail levels. The presentations share source data but have different rendering capabilities.

## Garmin — both regions

Choose the region-specific `.img` in the table above. England/Wales is installed on the Montana 750i and GPSMAP 67i with full read-back verification; [separate device records](regions/england-wales/garmin/device-installations.json) confirm that Ireland and personal tracks were preserved. England/Wales revision **2.0.0-garmin-r2** fixes the large blue-area display issue and uses identifiers separate from both Ireland and the optional personal-track layer. The repaired appearance has been accepted on GPSMAP 67i; Montana visual review remains pending. The public [England/Wales download](https://downloads.appsbyonzy.dev/Garmin/OpenBareMap-England-Wales.img) matches the installed repair. The details below describe the established Ireland package; England/Wales has its own [installation instructions](regions/england-wales/garmin/dist/INSTALL.txt) and [build inspection](regions/england-wales/garmin/build-report.json). Both are display-only.

The Garmin edition is a **display-only map**, with no turn-by-turn routing. It includes 20-metre contours, native elevation data, land-cover textures, cliff markings, place names and outdoor features.

| Resource | Location |
| --- | --- |
| Installable map, see release manifest for file size | [OpenBareMap-Ireland.img](garmin/dist/OpenBareMap-Ireland.img) |
| Installation instructions | [INSTALL.txt](garmin/dist/INSTALL.txt) |
| Legend | [Montana-750i-Legend.png](garmin/dist/Montana-750i-Legend.png) |
| Build, integration and validation details | [Garmin guide](garmin/README.md) |

The 20 m Garmin edition is installed on the **Montana 750i** and **GPSMAP 67i**, with full file read-back verification. The GPSMAP H1 has the 10 m edition installed. Visual review of the new edition is pending. [Device installation records](garmin/device-installations.json) identify the exact installed revisions.

The Ireland Garmin package revision is **2.0.0-20m**. Townlands use a native text category, NormalFont and muted grey-brown, without a marker. Displayed capitalisation and size depend on the device. This native label treatment applies to Garmin; MapLibre applications use the shared font and label resources.

Install the `.img` in the device's `Garmin` folder or on a supported memory card, and enable **OpenBareMap Ireland** in the device's map controls. The 67i and H1 use MTP for USB file transfers on macOS. Point-label text must be enabled for mountain names. Disable overlapping detailed maps and satellite imagery when viewing OpenBareMap on its own.

Personal recorded tracks can be displayed as a separate transparent map layer and switched independently of the basemap. The personal track package is separate from the basemap distributed here.

Garmin uses its own zoom and font controls. Irish Grid lines and distinct bridge/tunnel styling are not included in this edition. Set elevation units to metres for metric contour labels.

## Android — map resources for each region

Use the export commands above for either region. The reference app and links below are the existing Ireland integration; no England/Wales host app is created or installed by the map build.

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

Open `android/` in Android Studio for app development. The reference app is debug-signed; production signing and distribution belong to the consuming application. Build, loader and resource-integrity checks pass. The host application requires device-specific rendering, import-performance and memory assessment. The [BareGPS Android app](https://github.com/davidowens1513/BareGPS-Ireland-Android) bundles the map directly and supplies its own map interface and zoom-dependent hill/start markers.

## iOS — map resources for each region

Use the export commands above to produce a separate bundle for the chosen region. The links below describe the existing Ireland integration.

The iOS edition is a **resource bundle and Swift loader for MapLibre Native**, intended for integration into an iOS application.

| Resource | Location |
| --- | --- |
| Offline resource bundle, full-island package | [OpenBareMap.bundle](ios/package/OpenBareMap.bundle/) |
| Swift loader | [OpenBareMapResources.swift](ios/OpenBareMapResources.swift) |
| Xcode integration example | [INTEGRATION.txt](ios/INTEGRATION.txt) |
| Packaging and validation | [iOS guide](ios/README.md) |

Add the complete bundle as an Xcode resource and include the Swift loader in the app target. The loader resolves local style and resource paths for MapLibre Native without a local web server. The host app supplies the renderer, map interface and access to the attribution notices.

The bundle contains map databases, townland points, styles, glyphs, sprites, a legend and provenance records. Resource integrity and Swift loader checks pass; MapLibre rendering and performance require simulator/device assessment. This package is an integration component rather than a standalone iOS app.

## Public previews — both regions

| Ireland | England & Wales |
| --- | --- |
| [Open map preview](https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/ireland/index.html) · [Open zoomable map key](https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/ireland/legend.html) | [Open map preview](https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/england-wales/index.html) · [Open zoomable map key](https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/england-wales/legend.html) |
| <a href="https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/ireland/legend.html"><img src="https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/assets/legends/ireland@2x.png" width="220" alt="Ireland map key — click to open and zoom"></a> | <a href="https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/england-wales/legend.html"><img src="https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/assets/legends/england-wales@2x.png" width="220" alt="England and Wales map key — click to open and zoom"></a> |

Click a key image or its link to open the full-size legend. The separate legend page has zoom controls, a fit-to-page view and image download; larger views can be scrolled or dragged. Ireland uses the Irish Grid key and England & Wales uses the British National Grid key. The website previews use these same legend pages.

Both previews display the complete selected map, with pan/zoom and regional destinations. These online previews load tiles as needed; they do not replace the offline downloads. See [web preview packaging](web-preview/README.md) for updating and embedding them.

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

Ireland uses the **24 October 2026** Ireland/Northern Ireland extract. England/Wales uses both complete **30 October 2026** extracts, with a shared replication timestamp; its separate [source lock](regions/england-wales/sources.lock.json) and [terrain lock](regions/england-wales/terrain-sources.lock.json) pin the inputs. Terrain uses approximately 30-metre composite elevation data from Terrain Tiles. The shared map’s 20-metre contour interval describes line spacing, not a statement of terrain accuracy.

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

[Map versioning and platform adaptations](docs/versioning-and-platforms.md) explains pinned resources, platform profiles and package revisions. [Contour storage checks](releases/2.0.0/contour-padding-report.json) and [detail selection checks](releases/2.0.0/detail-report.json) describe the distributed datasets.

[Development history and build workflow](docs/development-history.md) describes the project's development, packaging approach and maintenance commands. [Architecture](docs/architecture.md) describes the underlying map pipeline.
