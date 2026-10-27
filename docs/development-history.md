# Development history and build workflow

This document records the development of OpenBareMap and the structure of its build pipeline. The [main README](../README.md) describes the available map and platform packages.

## Cartography and shared data

The project uses OpenBareMap 1.1 as its cartographic reference. Selected colours, terrain textures, typography resources, townland labels and Irish Grid assets are retained under recorded checksums. Reference material is in `assets/legacy-1.1/`; copied resources and their provenance are listed in `legacy-assets.lock.json`. The townland dataset contains 50,380 label points. Original generation recipes for some inherited resources are incomplete.

The basemap pipeline processes a full Ireland and Northern Ireland OpenStreetMap snapshot dated 24 October 2026. Coastline inputs and composite elevation grids have independent source locks. Contours use a 10-metre interval from the shared elevation data, with separate hillshade and grid resources. `active-map.json` selects the databases consumed by the viewer and platform packagers.

Cartographic development covered land-cover colours and patterns, progressive contours and label density, settlement and summit visibility, dashed paths and tracks, transport links, bridge/tunnel ordering, text sizes and legend consistency. Text halos were omitted. Parking uses a conventional white P on blue; summit and outdoor features use dots and text. The active style and transport configuration are the authority for current presentation values, rather than the sequence of historical adjustments.

The browser viewer uses vendored MapLibre GL JS and local resources. Its legend derives samples from the active style. Build reports, source locks and screenshots provide records of the selected map datasets and presentation.

## iOS and Android packaging

The iOS resource bundle packages the selected databases, a zoom-capped coast archive, townland points, fonts, sprites, legend and notices. The Swift loader resolves local resource URLs for MapLibre Native. Resources and loader code are kept under `ios/`.

The Android implementation includes a Kotlin loader, Android Studio reference app and offline import package. The app imports its map separately from the APK. It verifies and stages the package in app-private storage before making it available. Android and iOS share the coast-capping helper in `scripts/package_resources.py`; Android packaging does not depend on the iOS bundle.

Platform validation records distinguish resource, loader and build checks from actual renderer and device acceptance.

## Garmin export and device checks

The Garmin edition uses mkgmap and splitter to compile a native, non-routing IMG map. It combines the shared OSM snapshot with contours, coast geometry and townland points. A custom TYP supplies colours, line patterns, dots, parking symbols and terrain textures. Native DEM data supports device terrain rendering. Additional neighbouring elevation grids provide interpolation padding.

The Garmin format has its own font and detail-level rules, so its presentation differs from MapLibre. The map contains 70 detail tiles with DEM and custom TYP data and has no NET/NOD routing sections. `garmin/build-report.json` records binary inspection and repeat-build comparison. Repeated compiles differ beyond creation timestamps, including a 76-byte difference in RGN payload sizes; strict binary reproducibility is an open build issue.

The map was installed on a Montana 750i and GPSMAP 67i, with transferred files read back or hashed for verification. The Montana's point-text controls initially hid mountain names; enabling point text made mountain names and parking visible. The GPSMAP 67i exposes storage through MTP on macOS, and its satellite imagery has separate layer controls. Installation verification does not constitute comprehensive geographic or performance acceptance.

A separate local personal-track overlay contains 355 tracks selected from the user's 557-track MountainViews/Onzy archive. Tracks extending outside the shared Ireland extent were excluded as whole tracks. The transparent overlay preserves GPX segment breaks and displays purple lines and green start markers without names. The personal track files are separate from the published basemap; this documentation update does not publish those files.

## Maintenance commands

Run commands from the repository root unless a platform guide specifies otherwise. Git LFS must restore the actual large-file contents before validation or packaging.

```sh
git lfs pull
python3 -m unittest discover -s tests -v
```

### Shared map

Use fresh build names; build commands refuse to overwrite existing output directories.

```sh
python3 scripts/openbaremap.py build ireland-custom-a
python3 scripts/openbaremap.py build ireland-custom-b
python3 scripts/openbaremap.py compare ireland-custom-a ireland-custom-b
```

Build records capture input checksums, processor configuration and the Tilemaker binary. Terrain generation is implemented in `scripts/build_topography.py` and `scripts/build_hillshade.py`. Their source locks and reports retain the independent elevation provenance.

Transport drawing passes are generated from `config/transport-style.json`:

```sh
python3 scripts/style_transport.py
```

Sprite generation uses the dependencies in `assets/requirements.txt`:

```sh
python3 scripts/build_sprites.py
```

`assets/sprites.lock.json` records output hashes and the Pillow version.

### Platform packages

- [Garmin guide](../garmin/README.md): native style, source preparation, pinned tools, compilation and binary inspection.
- [Android guide](../android/README.md): Android Studio/Gradle, loader integration, map ZIP export and validation.
- [iOS guide](../ios/README.md): bundle assembly, Xcode integration and Swift loader checks.

Use new package/build destinations where the platform builder requires them. Keep source/tool locks, output checksums and validation records consistent with any published package.
