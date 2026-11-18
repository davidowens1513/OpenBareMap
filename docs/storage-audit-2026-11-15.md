# Release storage audit — 15 November 2026

## Scope and evidence

Compared the current Git index and ignore rules with all ten active map selections,
the app-bundle catalog, the R2 restore inventory, Garmin publication manifests,
and Norway publication/readback records dated 14 November 2026.

The Cloudflare R2 dashboard was inspected in Chrome on 15 November: all three
Norway Garmin images and all six Norway integration ZIPs were present, with
rounded sizes matching the release metadata. Their instructions, manifests and
phone checksum files were also listed. The dashboard reported public access enabled.
This was an object-presence check, not a new complete public checksum readback.
Direct HTTP checks from the command environment failed at DNS resolution, and
the web retrieval service could not open the catalog or Norway preview. Yesterday's
full public checksum reports remain the integrity evidence for those releases.

This is an audit of current advertised releases and their restoration paths,
not a complete bucket inventory, historical Git LFS billing audit, or backup test.

## Findings and corrections

| Finding | Correction |
| --- | --- |
| Root README's opening, downloads, coverage and preview tables omitted Norway | Added Southern, Central and Northern Norway, platform downloads and instructions, preview/key links, source date, grid, family IDs, overlaps and sizes. |
| README said large resources were in Git LFS and active databases remained tracked | Replaced with an explicit distinction between Git, Git LFS, Cloudflare delivery files and local-only working resources. |
| Restore inventory contained 13 files, approximately 7.49 GB | Expanded to all 30 currently advertised delivery files, 38,710,347,717 bytes (38.71 GB). |
| All nine Norway delivery files were absent from the restore inventory | Added six phone bundles and three Garmin images using recorded paths, URLs, sizes and SHA-256 checksums. |
| Eight older phone bundles were also absent | Added iOS/Android kits for Ireland, England/Wales, Scotland and Sierra Nevada from the catalog. Retained their existing `work/` destinations. |
| Restore command's help still advertised the old total | Removed the fixed total from help and added a computed count/size to `--list`. |

All 20 current app kits and ten Garmin images are outside the Git index; their
URLs and checksum records remain tracked. Cloudflare hosting applies to small
regional release files too, not just files exceeding a size threshold.

## Working database availability after cloning

| Editions | Selected development databases |
| --- | --- |
| Ireland, Scotland, Sierra Nevada, Pyrenees | Active database paths are tracked in Git LFS. LFS content must be fetched. |
| England/Wales | Basemap is assembled from tracked LFS parts; other selected databases are tracked in LFS. |
| Dolomites, Faroe Islands | Basemap, grid and hillshade are tracked in LFS. The accidental ignore rules for selected `topography-context.mbtiles` have been removed so both contour databases will be included in the next Git LFS commit. |
| Southern, Central, Northern Norway | All selected databases and binary parts are excluded. Small `.parts.json` files are tracked, but their referenced payloads are not. Source/elevation bulk data is also excluded. |

The active-map JSON files identify expected database bytes and checksums.
A parts manifest's `openbaremap-lfs-map-parts-v1` format name is not evidence that
its payloads are tracked: Norway retains these manifests as build records only.
`git lfs pull` cannot recover ignored files absent from the index.

Restoring an outer phone kit downloads the published deliverable. It does not
extract or install its databases at `active-map.json` paths. Some packaged map
resources are transformed for distribution; recovery from a kit must verify the
selected database's exact size and SHA-256 before using it as a working resource.

## Contour database correction and Norway policy

The selected contour databases already existed locally and were verified against
their active-map size and SHA-256 records, SQLite `quick_check`, and tile counts:

| Edition | Selected database | Bytes | Tiles |
| --- | --- | --- | --- |
| Dolomites | `releases/dolomites/2.0.0/maps/topography-context.mbtiles` | 277,413,888 | 250,107 |
| Faroe Islands | `releases/faroe-islands/2.0.0/maps/topography-context.mbtiles` | 12,447,744 | 3,198 |

Both paths now pass the ignore rules and match the existing `*.mbtiles` Git LFS
attributes. They are ready for inclusion in the next commit. The unselected
`topography.mbtiles` intermediates remain ignored.

Norway's bulk-file exclusions are intentional: source data and working databases
can be recreated when required. Do not add these files to Git/LFS or upload them
to Cloudflare for backup. Finished delivery files and public previews remain on
Cloudflare; configuration and provenance remain in Git. Rebuilding does not
promise byte-identical historical output if upstream sources have changed.

## Recommended next improvements

1. **Prevent inventory drift.** Check the restore inventory against the app catalog
   and each Garmin manifest whenever publishing. Generate the README's link and
   size tables from those records to avoid updating several lists by hand.
2. **Preserve the agreed Norway rebuild policy.** Keep bulk sources, terrain,
   working databases and binary database parts excluded from Git/LFS and Cloudflare
   backups. Use the documented build workflow when these files are needed again.
3. **Keep restoration scope explicit.** `restore_r2_assets.py --all` restores
   finished delivery files. It does not prepare Norway development databases.
   Other editions use their selected LFS databases, including the corrected
   Dolomites/Faroe contour paths.
4. **Stabilize restore destinations over time.** Older phone kits currently use
   `work/` paths from their catalog. A future packaging change could use uniform
   `releases/<region>/<version>/app-bundles-v1/` paths, updating the catalog and
   restore inventory together rather than silently moving current paths.
5. **Treat historical LFS storage separately.** Current exclusions do not remove
   previous Git LFS versions. Review remote LFS usage and historical references
   before considering any purge; this audit made no Git history or storage changes.

No assets were uploaded, deleted, moved or downloaded in bulk during this audit.
No Git history was rewritten and no commit or push was performed.

## Follow-up on 18 November 2026

The four Mediterranean editions follow the Norway rebuild policy. Git contains
the build configuration, source locks, checksums and small release records.
Raw OSM, Copernicus inputs, derived regional databases and Garmin build inputs
stay local. The finished iOS and Android integration kits, Garmin IMG files
and browser previews are delivery assets for Cloudflare R2. The restore
inventory records the kit and IMG paths and hashes.
