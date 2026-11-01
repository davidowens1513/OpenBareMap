# Maintaining regional editions

OpenBareMap uses one repository and shared cartography for Ireland and England/Wales. Each edition selects its own source snapshots, coordinate grid, map databases and platform packages. A regional release does not replace another edition's resources or require it to be released at the same time.

Ireland remains the default for existing build, viewer and packaging commands. Its selected map stays in the root `active-map.json`. The accepted Ireland inputs and outputs are recorded in `regions/ireland/preservation-baseline.json`; regional validation verifies their checksums.

## England/Wales scope

The edition uses both complete Geofabrik extracts, merged by OSM object identity/version. It includes England, Wales and their offshore islands, including the Isles of Scilly and Anglesey. It is not a pilot or a sample. Terrain acquisition covers every one-degree cell in longitude −7 to +3 and latitude 49 to 56. Surrounding coastal land/terrain is context; the OSM coverage follows the source extracts.

It shares the Ireland edition's colours, symbols, transport passes, hillshade processing, 20 m contours, 100 m index contours and bounded geometry smoothing. In the England/Wales overview, rivers and canals remain visible while smaller waterways appear from zoom 10; all source features remain in the databases. Surrounding coastlines extend beyond the country coverage so the map has no rectangular land cutoffs. Welsh `name:cy` values replace the Ireland-specific Irish-language fallback in this edition's processing/style. Source `name` and English names are retained. The transport schema also retains OSM designation, horse/bicycle/foot access, trail visibility and hiking difficulty for inspection; these tags do not certify a legal right of way.

The generated British National Grid uses EPSG:27700, with 1 km/10 km lines and projected metre-coordinate labels. Its exact transformation, library version and stated accuracy are recorded in `grid-provenance.json` in the geometry build. It is a cartographic overlay. Empty multipolygon assemblies in the OSM source are recorded explicitly in the geometry report; missing locations or failed nonempty geometry remain build errors. The grid overlay is included in the browser and mobile packages; the Garmin export does not embed grid lines. Ireland retains its pinned Irish Grid and townland points; neither is included in England/Wales packages.

## Paths and release independence

| Resource | Ireland | England/Wales |
| --- | --- | --- |
| Edition settings | `regions/ireland/region.json` | `regions/england-wales/region.json` |
| Active selection | `active-map.json` | `regions/england-wales/active-map.json` |
| OSM and terrain locks | Root lock files | `regions/england-wales/*-sources.lock.json` and `sources.lock.json` |
| Build outputs | Existing `build/` selections | `build/england-wales-*` |
| iOS resources | `ios/package/` | `regions/england-wales/ios/` |
| Android import package | `android/package/` | `regions/england-wales/android/` |
| Garmin | Family 4831 | Family 4832, tiles starting 48320001 |
| Release records | `releases/2.0.0/` | `releases/england-wales/2.0.0/` |

The Garmin family and tile identifiers differ, allowing both images to coexist. Both Garmin editions are display-only. The Android resource loader installs map packages by manifest hash and preserves older versions. Consuming applications choose which map to load; this map build does not modify BareGPS applications. The iOS resources use the same loader, with an edition-specific bundle identifier; a host app decides which bundle or installed resource directory to load.

## Complete build

The current source date is selected explicitly in the edition profile. Downloads are verified against upstream MD5 and then recorded with SHA-256. England and Wales must have identical replication timestamps. A locked source is never silently refreshed.

Install the additional Python packages into the ignored local runtime:

```sh
python3 -m pip install --target work/python -r scripts/requirements-regions.txt
```

The existing Tilemaker, QGIS/GDAL and Garmin Java toolchain locks still apply. The regional requirements include the shared legend generator’s pinned Pillow version. The build uses the existing downloaded Garmin archives and Android Studio Java when available.

Run every stage for the complete edition:

```sh
PYTHONPATH=work/python python3 scripts/run_full_region.py --region england-wales
```

This acquires and locks full inputs, builds the basemap/terrain, smooths complete source geometry, generates the grid, selects display detail, packages iOS/Android resources, compiles Garmin and validates outputs. Existing completed stages are reused only where their recorded checks pass. Incomplete stages are errors; inspect their records before choosing a new destination or removing an unsuccessful generated directory. Accepted outputs are not silently overwritten.

Individual stages remain available:

```sh
PYTHONPATH=work/python python3 scripts/fetch_region.py --region england-wales
python3 scripts/build_topography.py england-wales-topography --region england-wales
PYTHONPATH=work/python python3 scripts/build_region.py --region england-wales
PYTHONPATH=work/python python3 scripts/build_region_garmin.py --region england-wales
python3 scripts/validate_region.py --region england-wales
```

Platform packaging can be repeated into fresh destinations with `--region england-wales --output /absolute/new/directory`. Default Ireland commands retain their existing meaning.

For future data updates, retain the prior release manifest and locked inputs. Select a new snapshot/release and fresh build/output names rather than replacing a released database in place. The first England/Wales orchestration uses fixed, edition-specific stage names; subsequent source releases must use new names before starting. Shared styling or software changes can be made once, then packaged and released for either edition independently.

## Local viewing

```sh
python3 scripts/serve.py --region england-wales --port 8766
python3 scripts/serve.py --port 8765
```

Accepted regional databases are copied into the versioned release directory; intermediate stages remain under `build/`.

The first command serves England/Wales; the second serves Ireland. Both use local assets and checksum-verified selected map databases. The viewer's destinations and initial extent follow the edition.

## Acceptance records

`releases/england-wales/2.0.0/validation.json` checks detailed coverage around geographically distributed anchors, all contour intervals, selected boundaries, SQLite integrity, package checksums and Ireland preservation. The Garmin inspector requires the distinct family configuration, contours, DEM, TYP, summit/bog features, city labels and absence of routing sections. Release manifests pin exact artifact hashes.

Automated checks do not establish geographic completeness of OpenStreetMap, legal access, or native-device appearance. Browser visual review and mobile/Garmin device testing have separate records. No hardware installation is performed by the build.
