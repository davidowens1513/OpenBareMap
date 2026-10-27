# OpenBareMap 2.0 for Garmin

Display-only, full-island Ireland and Northern Ireland map. The deliverable is `dist/OpenBareMap-Ireland.img` (size and checksum in the release manifest). Copy instructions are in `dist/INSTALL.txt`. The same IMG is installed on the Montana 750i, GPSMAP 67i and GPSMAP H1. Full-file read-back verification is recorded in [device-installations.json](device-installations.json). Townland appearance is accepted on the Montana; visual acceptance on the 67i and H1 remains pending. The Garmin package revision is `2.0.0-townland-labels`, within map version 2.0.0.

Includes roads, tracks, footways, bridleways, cycleways, steps, walking/cycling overlays, water, land cover, buildings, boundaries, townlands, place names, summit dots, parking P symbols, bog texture and cliff teeth. Contours use the shared, gently smoothed 10 m geometry. Land-cover polygons use the shared smoothed source snapshot. Native DEM elevation data supports Garmin's terrain rendering. No routing network or turn instructions are generated.

## Native cartography

Garmin renders its own fonts, labels and detail levels. This is a native adaptation, not pixel-identical to the MapLibre map. SmallFont is used for most names, NormalFont for cities and townlands; device settings affect actual size. Text has no custom halo. Day and night palettes currently match. Bog/rock patterns are native two-colour bitmaps. The supplied legend is generated from the same palette and patterns.

| Detail level | Garmin resolution | Contours |
| --- | --- | --- |
| 0, closest | 24 | 10 m, 50 m and 100 m |
| 1 | 22 | Fine 50 m overview strokes and 100 m |
| 2 | 20 | Fine 100 m overview strokes |
| 3 | 18 | None |
| 4, overview | 16 | None |

These are Garmin resolution bits, not web zoom numbers. Native close-detail contour elevation attributes use feet; set device elevation units to metres. Overview-only contour types have no labels. The underlying spacing remains 10 m. Irish Grid lines are not exported in this version. Bridges and tunnels do not yet receive a distinct Garmin rendering. MapLibre raster hillshade, pixel text sizes and label spacing do not transfer directly.

Townlands use Garmin’s standard region-text category, without a marker, in muted grey-brown (`#817b70`). Source names are uppercase; the device controls the displayed capitalisation and size. The current rendering has been accepted on the Montana 750i. The label profile is installed on the GPSMAP 67i and H1, with file integrity verified; its on-screen appearance has not yet been reviewed on those models.

## Source and tool records

- Shared `sources.lock.json`, `terrain-sources.lock.json` and townland data remain authoritative.
- `inputs.lock.json`: exact compressed shared contour geometry and full-island coast mask.
- `dem-padding.lock.json`: five adjacent eastern elevation cells needed by DEM interpolation.
- `toolchain.lock.json`: pinned mkgmap r4924, splitter r654 and macOS ARM Python 3.12 osmium wheel. Archives retain their upstream licence notices.
- `config.json`, `style/`, `generate_typ.py`: native map profile and custom symbols.
- `build-report.json`: output checksums, source counts, binary read-back and repeat-build comparison.
- `work/`: ignored intermediate files; `dist/`: installable map and notices.

## Rebuild

Run from the repository root after `git lfs pull`. Use Java 17 or newer and Python 3.12 with osmium 4.2.0. The builder uses JAVA_HOME, Android Studio's bundled Java on macOS, or Java on PATH. Set JAVA_HOME explicitly for other environments. Allow roughly 15 GB working space and at least 8 GB RAM.

On macOS ARM with Python 3.12:

```sh
python3.12 -m pip install --no-deps --target garmin/work/python garmin/tools/osmium-4.2.0-cp312-cp312-macosx_11_0_arm64.whl
python3.12 garmin/build.py --name compile-release
```

On other platforms install the pinned osmium version for that Python/platform. Pillow is needed only to regenerate the legend (`make_legend.py`). The builder verifies pinned tool archives and extracts them locally. It prepares the full contour/coast/townland overlay, merges it with the locked OSM snapshot, splits complete features and compiles the map. Existing split/build directories cause an error: preserve or move an old work directory before a fresh build, then reinstall the local Python dependency. The build never silently overwrites a previous compiled map.

Read back the compiled files before publishing:

```sh
javac -cp garmin/tools/mkgmap-r4924/mkgmap.jar -d garmin/work garmin/InspectMap.java
java -Xmx2g -cp garmin/work:garmin/tools/mkgmap-r4924/mkgmap.jar InspectMap garmin/work/compile-release > garmin/work/inspection.json
```

Use the platform classpath separator on Windows. The inspector requires embedded DEM/TYP, all three contour types, summit/bog features, known place names, and no NET/NOD routing sections. After successful inspection, copy that build's `gmapsupp.img` into `dist/OpenBareMap-Ireland.img` and refresh checksums/report.

## Validation and limitations

The version 2.0 build report records the compiled tile inventory, DEM, custom TYP, progressive contours and names including Carrauntoohil, Belfast and Dublin. Automated checks cover the map profile, smoothing behaviour and deterministic TYP generation.

Strict binary recompilation reproducibility is unresolved. A repeated-build comparison of the preceding profile found a 76-byte RGN payload-size difference beyond creation timestamps. The release manifest pins the exact version 2.0 IMG bytes without claiming byte-identical recompilation.

Keep Map Points text enabled and its zoom setting on Auto. Version 2.0 hardware rendering, contour-unit and performance acceptance is required on both devices. Its binaries are not automatically installed when the repository is updated.

On the GPSMAP 67i, installed detailed maps are managed under Setup > Map > Map Manager. Satellite imagery is controlled separately from the map page using MENU > Map Layers. Display appearance is under Setup > Display > Appearance > Mode (Day, Night or Auto). A personal-track overlay is a separate optional map layer and can be toggled independently of OpenBareMap.
