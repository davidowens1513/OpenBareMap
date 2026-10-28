# OpenBareMap 2.0 for Android

MapLibre Native Android implementation, separated from the iOS integration. Shared map data and styling remain in the repository root. The reference app is for testing/integration, not a signed production release.

## Ready-to-use outputs

- `dist/OpenBareMap-debug.apk`: installable, debug-signed reference app. The map is imported separately.
- `dist/openbaremap-loader-release.aar`: reusable Android library for installation, verification and local style resolution.
- `package/OpenBareMap/`: complete full-Ireland runtime resource package, tracked in Git with LFS for large files.
- `package/OpenBareMap-Android.zip`: local import archive, a full-island dataset. The duplicate ZIP is generated and not tracked; regenerate it after cloning.

Install the APK on a test device, transfer the ZIP to a location accessible through Android's document picker, launch OpenBareMap and tap **Import map**. Extraction and checksum verification run on a worker thread. The map, legend and credits then work offline. Import uses app-private storage without requesting broad storage or location access. Allow several GB of working storage for the archive and installed map. Previous installed map versions are retained; the reference app does not yet offer version management/removal.

## Android Studio / command-line build

Open this `android/` directory in Android Studio. Set its Android SDK location through Android Studio or an ignored `local.properties`. Use JDK 17+ (tested using Android Studio's bundled JDK), Android SDK 36.1 and the pinned Gradle wrapper.

```sh
./gradlew :loader:testDebugUnitTest :loader:assembleRelease :app:assembleDebug
```

The app uses MapLibre Native **13.6.1 OpenGL ES**, selected for broad device compatibility. Minimum Android API is 23; target API is 36. Gradle is 9.4.1 and Android Gradle Plugin is 9.2.1. Dependency lockfiles and the wrapper distribution checksum are checked in. Native binaries in the debug APK are supplied by MapLibre; release signing is the consuming app's responsibility.

## Restore or assemble the map

From the repository root:

```sh
git lfs pull
python3 android/build_package.py --zip-only
```

This exports the import ZIP from `android/package/OpenBareMap/`, verifying checksums first. To assemble a new snapshot, use a new output directory:

```sh
python3 android/build_package.py --output /absolute/path/to/new-package
```

It reads `active-map.json` and the shared style/fonts/sprites/legend. It does not read the iOS bundle. Both platform builders share the coast-capping function in `scripts/package_resources.py`. The capped coast archive keeps coast overzoom separate from the full 20 m contour archive.

## Use the loader in another Android app

Add the `loader` module or its AAR to your app and add the pinned MapLibre SDK. The loader itself uses Android's built-in JSON support and ordinary streaming/file APIs. Install the ZIP on a background thread, then resolve the style:

```kotlin
// Worker thread:
val directory = OpenBareMapResources.installZip(inputStream, File(context.filesDir, "maps"))
val styleJson = OpenBareMapResources.prepareStyle(directory)
// Main thread, after getMapAsync:
map.setStyle(Style.Builder().fromJson(styleJson))
```

The importer rejects escaping paths, duplicate ZIP entries, excessive entry counts/sizes, corrupt resources and unlisted files. It stages installation before publishing a verified version. Checksums detect corruption; they do not authenticate an unknown package publisher. Package distribution should remain under your control.

The loader resolves `mbtiles:///...` sources and absolute local font/sprite/GeoJSON URLs at runtime; no localhost server or web map service is needed. Keep the installed resource directory accessible for the lifetime of the map. Follow the MapView lifecycle shown in `app/`. Display the supplied attribution and terrain notices in the consuming app.

## Validation

Tests cover escaped sandbox paths, offline URL resolution, repeatable installation, preservation of previous versions, corruption/unlisted-file rejection and ZIP traversal rollback. The real full-Ireland package is additionally checked by:

```sh
./gradlew :loader:testDebugUnitTest -PmapPackage=/absolute/path/to/package/OpenBareMap
```

The reference APK and loader AAR compile successfully; real package checks and SQLite integrity checks pass. No connected device or configured emulator was available, so Android rendering, import speed, memory use and UI layout remain to be tested on hardware. The reference app does not yet provide a production map-update service, release signing or old-version management.

References: [MapLibre Android quickstart](https://maplibre.org/maplibre-native/android/examples/getting-started/), [renderer artifacts](https://maplibre.org/maplibre-native/android/examples/artifacts/), [Style.Builder.fromJson](https://maplibre.org/maplibre-native/android/api/-map-libre%20-native%20-android/org.maplibre.android.maps/-style/-builder/from-json.html), [local MBTiles discussion](https://github.com/maplibre/maplibre-native/discussions/393).

## Map storage revision

The current resource package uses `2.0.0-storage-r3`, approximately 1.01 GB. It preserves all-Ireland coverage, 20 m contours and national/county borders. Local border lines are omitted; townland and settlement names remain. Contour segments intersecting the tile plus a 128-pixel buffer retain their original coordinates and attributes; distant segments are omitted. Other feature geometry is unchanged. Overview tiles omit features the pinned style does not display. The capped coast archive contains only the unchanged land layer, with empty tile positions retained. Resource checksums and package validation identify the exact files. Existing app installations require a resource update. The BareGPS Android app includes these resources; the Samsung SM-A075F installation is verified. iOS device appearance comparison remains pending.

Cliffs use a shared periodic teeth pattern with 16 × 6 logical-pixel cells, supplied at both atlas resolutions. Cliff line weight and visibility start at zoom 11. Device appearance comparison remains pending.

The shared app legend uses bold dark labels, enlarged line samples and outlined colour swatches with enhanced contrast and saturation. These presentation adjustments aid reading; the map style is unchanged.
