# OpenBareMap — My Tracks

Separate, transparent Garmin map layer of Onzy's recorded Irish tracks: **355 included; 202 excluded**. Purple polylines and green start markers. One start marker per original GPX track. Neither start markers nor track lines carry names, including when selected. Original segment breaks are preserved; a single-point segment is retained as a point but cannot form a line. No navigation routes, GPX imports, descriptions or photos are installed.

## On the Montana

Copy `garmin/dist/OpenBareMap-My-Tracks.img` into the device or card's `Garmin` folder. Keep `OpenBareMap-Ireland.img` installed too. Under **Setup → Map → Configure Maps**, enable **OpenBareMap - My Tracks** to show the lines and starts; disable just that layer to hide them. Automatic Maps may need to be off for manual map selection.

Keep Map Points text enabled under **Map Setup → Advanced Setup → Text Size**, and Map Points zoom set to Auto. The device's point-text setting was confirmed to hide summit names and parking in the original map until enabled. Tracks start at Garmin resolution 20, start markers at 22; exact display scales depend on the device's detail setting. No turn-by-turn routing is generated.

## Source selection and rebuild

Source archive: Desktop/MountainViews-Onzy-Complete, 557 GPX files. Retain an entire track only if every recorded coordinate lies within the shared Ireland extent, longitude −11 to −5 and latitude 51 to 56. This is an extent test, not a newly surveyed political/coast boundary. Tracks extending outside it are excluded entirely, not clipped. It produces the agreed 355/202 selection.

`inputs.lock.json` records the source GPX checksums and included/excluded IDs. `inputs/tracks-ireland.json.gz` retains just the selected coordinates, titles and IDs, with deterministic compression. Original GPX segments are kept separately. No timestamps, elevation values, photos, comments or descriptions are copied into the map layer. Track source: the user's Onzy records, exported from MountainViews; original archive notices reference https://mountainviews.ie/conditions/.

Run from the repository root:

```sh
python3 garmin/my-tracks/build.py
```

To refresh from the original archive, add `--source /path/to/MountainViews-Onzy-Complete`. Preserve/move `garmin/work/my-tracks/compiled` before rebuilding; the builder refuses to overwrite a prior build. Pinned mkgmap tools are shared with the Garmin basemap build. The custom layer uses a distinct family ID (4832), transparent flag and draw priority 31; the basemap has family ID 4831 and default priority 25.

Read-back validation:

```sh
javac -cp garmin/tools/mkgmap-r4924/mkgmap.jar -d garmin/work/my-tracks garmin/my-tracks/InspectTracks.java
java -cp garmin/work/my-tracks:garmin/tools/mkgmap-r4924/mkgmap.jar InspectTracks garmin/work/my-tracks/compiled
```

`build-report.json` records 355 unlabelled start points, 695 encoded line pieces, embedded custom symbols, transparency, priority and absence of routing. The compiler can subdivide a source line into multiple encoded pieces. Device rendering still requires review.
