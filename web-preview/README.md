# Independent public map previews

The regional previews use the full accepted maps, with separate entry pages and PMTiles archives. They do not load or modify a BareGPS app.

- [Ireland preview](https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/ireland/index.html)
- [England & Wales preview](https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/england-wales/index.html)
- [Scotland preview](https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/scotland/index.html)

Each provides pan/zoom, regional destinations, a collapsible regional key with a clickable full-size, zoomable legend and source notices. Website buttons open the chosen region directly. Both device downloads and native app-resource exports remain separate from these online previews.

## Rebuild

Restore the selected region map databases with Git LFS. Python PMTiles 3.8.1 is required; the builder vendors PMTiles JS 4.5.0 from its official npm archive. Existing MapLibre, font and symbol assets are reused unchanged.

```sh
python3 -m pip install --target work/python pmtiles==3.8.1
PYTHONPATH=work/python python3 scripts/build_web_previews.py \
  --output /absolute/new/web-previews \
  --origin https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2
```

The destination must be new. The exporter checks selected input hashes, preserves all zoom levels, verifies archive tile counts and writes `manifest.json` with separate per-region input/output checksums. The coast layer is extracted from the selected topography at its existing zoom cap. No regional sampling or new cartographic processing is performed.

The output is a static directory: `assets/`, `data/ireland/`, `data/england-wales/`, `data/scotland/` and separate `ireland/`, `england-wales/`, `scotland/` entry pages. Host it on storage supporting HTTP byte ranges. The current R2 custom domain hosts the pages and data on the same origin; this avoids cross-origin data access. Use explicit `index.html` URLs because R2 does not automatically resolve directory indexes. See [the PMTiles MapLibre integration](https://docs.protomaps.com/pmtiles/maplibre).

For a future map revision, use a new origin prefix and output directory, publish the complete generated directory, verify all affected previews, then change the website links. Do not replace an archive at a cached old URL while users have it open.

## Include on appsbyonzy.dev

Links require no server-side map code:

```html
<a href="https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/ireland/index.html">Preview Ireland</a>
<a href="https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/england-wales/index.html">Preview England &amp; Wales</a>
```

To embed a map, use the corresponding URL in an iframe:

```html
<iframe title="OpenBareMap Ireland" loading="lazy"
  src="https://downloads.appsbyonzy.dev/OpenBareMap/preview-v2/ireland/index.html"
  style="width:100%;height:650px;border:0"></iframe>
```

Change both the title and region path for England/Wales or Scotland. The website integration snapshot in `site/` contains the separate regional preview and Garmin buttons. Its other app links are preserved.

## Update the key or preview controls

The website and the repository README link to the same regional pages. Each map key opens `legend.html` in a separate browser tab/window, with +/−, fit-to-page, 100% and image download controls. Mouse users can drag enlarged images; touch users can scroll and pinch to zoom.

To package page/key updates without rebuilding or uploading map archives:

```sh
python3 scripts/package_preview_ui.py --output /absolute/new/preview-ui
```

Upload that directory's files under the existing `OpenBareMap/preview-v2/` prefix, retaining all other files. The full preview builder also includes these pages and images automatically. The legend images come from `app-legend/` for Ireland and `regions/<region>/legend/` for England & Wales and Scotland.

Use `--regions scotland` with the full exporter to build only the new Scotland archives. When publishing into the shared preview prefix, retain other editions and merge their manifest records; do not replace the shared manifest with a single-edition inventory.
