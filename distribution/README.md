# Regional app integration bundles

`app-bundles-v1/catalog.json` identifies the iOS and Android kit for each edition,
including its public R2 URL, instructions, archive size and SHA-256. Each region
uses `OpenBareMap/<region>/<map-version>/app-bundles-v1/<platform>/` in R2. The shared
catalog is published at `OpenBareMap/app-bundles-v1/catalog.json`.

The iOS ZIP contains an unchanged, checksum-verified regional OpenBareMap.bundle,
the Swift runtime path loader, a UIKit example, dependency information and the
common-format instructions. The Android ZIP contains the unchanged flat native
import archive as OpenBareMap-Resources.zip, a tested loader AAR, Kotlin source,
an Activity/manifest example and dependency information. CHECKSUMS.txt covers
each kit's contents; SHA256SUMS.txt beside each public download covers the ZIP
and linked instructions. SDK renderer binaries are installed by the documented
Swift Package Manager or Maven dependency, rather than duplicated in each kit.

Build the loader before assembling the kits:

```sh
cd android
./gradlew :loader:testDebugUnitTest :loader:assembleRelease
cd ..
PYTHONPATH=work/python python3 scripts/build_app_distribution.py
python3 scripts/build_distribution_instructions.py
```

Runtime maps must already be assembled in ios/package and android/package for
Ireland, or regions/<region>/<platform> for England/Wales, Scotland and Sierra Nevada. The
builder verifies all resource hashes against their current map selections,
checks the native Android ZIP's individual members, creates the outer kits and
verifies their CRCs. It writes only a new work/app-bundles-v1 directory and the
small catalog; existing kits are not overwritten. Optional --regions selects
individual editions and retains catalog records for other completed editions.

Publish only the delivery files, excluding each temporary payload directory:

```sh
rclone copy work/app-bundles-v1/<region> \
  r2:baregps-production-assets/OpenBareMap/<region>/<map-version>/app-bundles-v1 \
  --exclude '**/payload/**' --checksum --s3-no-check-bucket
```

The website and root README use the catalog's URLs. Public file readbacks,
SDK example checks and browser checks are recorded beside the catalog. Garmin
instructions use one template across editions; device-specific installation and
historical build records remain in the platform/release subdirectories.

The catalog records versions per region: England/Wales includes the Isle of Man in 2.0.1; the other editions remain 2.0.0. Use the catalog URL and checksum for the selected region. `--platforms ios` or `--platforms android` packages one platform at a time when disk space is limited.
