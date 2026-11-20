#!/usr/bin/env python3
"""Stage verified Norway release files and an explicit Cloudflare upload plan."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
from openbaremap import ROOT, digest, write
from build_distribution_instructions import garmin_instructions
from regions import profile

REGIONS = ('norway-south', 'norway-central', 'norway-north')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--website-repo', type=Path,
                        help='Package the committed site from the AppsByOnzy-Website checkout')
    args = parser.parse_args()
    website = {}
    if args.website_repo:
        website_zip = ROOT / 'work/norway-website-20261114.zip'
        temporary_zip = website_zip.with_suffix('.zip.building')
        git = ['git', '-C', str(args.website_repo.resolve())]
        commit = subprocess.check_output([*git, 'rev-parse', 'HEAD'], text=True).strip()
        subprocess.run([*git, 'archive', '--format=zip', '--output', str(temporary_zip),
                        commit + ':site'], check=True)
        with zipfile.ZipFile(temporary_zip) as archive:
            if archive.testzip() is not None or 'index.html' not in archive.namelist():
                raise ValueError('Website archive integrity failed')
        temporary_zip.replace(website_zip)
        website = {'websiteCommit': commit, 'websiteArchive': str(website_zip.relative_to(ROOT)),
                   'websiteArchiveSHA256': digest(website_zip), 'cloudflarePagesProject': 'appsbyonzy'}
    catalog_path = ROOT / 'distribution/app-bundles-v1/catalog.json'
    catalog = json.loads(catalog_path.read_text())
    preview = ROOT / 'work/norway-web-2.0.0'
    preview_manifest = json.loads((preview / 'manifest.json').read_text())
    # Validate all three editions before creating or changing publication records.
    for region in REGIONS:
        manifest = json.loads((ROOT / 'releases' / region / '2.0.0/manifest.json').read_text())
        validation = ROOT / 'releases' / region / '2.0.0/validation.json'
        if not validation.exists() or manifest['region'] != region:
            raise ValueError('Missing complete validation: ' + region)
        for item in manifest['datasets'].values():
            if digest(ROOT / item['path']) != item['sha256']:
                raise ValueError('Selected dataset changed: ' + item['path'])
        for platform, item in catalog['regions'][region].items():
            if digest(ROOT / item['localPath']) != item['sha256']:
                raise ValueError('Integration archive changed: ' + region + '/' + platform)
        for name, item in preview_manifest['regions'][region].items():
            if digest(preview / 'data' / region / (name + '.pmtiles')) != item['sha256']:
                raise ValueError('Preview archive changed: ' + region + '/' + name)
    public_garmin = ROOT / 'work/norway-public-garmin'
    public_garmin.mkdir(exist_ok=True)
    uploads = []
    for region in REGIONS:
        p = profile(region); name = p['garminFilename']
        release = ROOT / 'releases' / region / '2.0.0'
        manifest_path = release / 'manifest.json'
        release_manifest = json.loads(manifest_path.read_text())
        # Retain build provenance; reproducible bulk payloads stay outside Git.
        for stage in ('geometry', 'topography', 'release'):
            source_dir = ROOT / 'build' / (region + '-' + stage)
            records = release / 'build-records' / source_dir.name
            records.mkdir(parents=True, exist_ok=True)
            for source in source_dir.glob('*.json'):
                if source.stat().st_size < 2 * 1024**2:
                    shutil.copyfile(source, records / source.name)
        geometry_report = release / 'build-records' / (region + '-geometry') / 'geometry-report.json'
        if digest(geometry_report) != release_manifest['geometryReport']['sha256']:
            raise ValueError('Archived geometry report differs: ' + region)
        release_manifest['geometryReport']['path'] = str(geometry_report.relative_to(ROOT))
        write(manifest_path, release_manifest)
        dist = ROOT / 'regions' / region / 'garmin/dist'
        report = json.loads((dist.parent / 'build-report.json').read_text())
        if digest(dist / name) != report['output']['sha256']:
            raise ValueError('Garmin image changed: ' + region)
        record_dir = ROOT / 'distribution/app-bundles-v1/garmin' / region
        record_dir.mkdir(parents=True, exist_ok=True)
        (record_dir / 'instructions.txt').write_text(garmin_instructions(region, name))
        (record_dir / 'SHA256SUMS.txt').write_text(report['output']['sha256'] + '  ' + name + '\n')
        for n in ('ATTRIBUTION.txt', 'terrain-attribution.md', 'terrain-data-sources.md'):
            shutil.copyfile(dist / n, record_dir / n)
        shutil.copyfile(ROOT / 'regions' / region / 'copernicus-license.pdf', record_dir / 'copernicus-license.pdf')
        write(record_dir / 'manifest.json', {
            'region': region, 'downloadURL': 'https://downloads.appsbyonzy.dev/Garmin/' + name,
            'instructionsURL': 'https://downloads.appsbyonzy.dev/Garmin/' + region + '-instructions.txt',
            'imageSHA256': report['output']['sha256'],
            'instructionsSHA256': digest(record_dir / 'instructions.txt'),
            'bytes': report['output']['bytes'], 'fullPublicReadbackVerified': False,
        })
        target = public_garmin / name
        if target.exists():
            if digest(target) != report['output']['sha256']:
                raise ValueError('Existing staged Garmin image differs: ' + name)
        else:
            os.link(dist / name, target)
        shutil.copyfile(record_dir / 'instructions.txt', public_garmin / (region + '-instructions.txt'))
        shutil.copyfile(record_dir / 'SHA256SUMS.txt', public_garmin / (region + '-SHA256SUMS.txt'))
        shutil.copytree(record_dir, public_garmin / region, dirs_exist_ok=True)
        for platform, item in catalog['regions'][region].items():
            source = ROOT / item['localPath']
            pinned = ROOT / 'releases' / region / '2.0.0/app-bundles-v1' / platform / source.name
            pinned.parent.mkdir(parents=True, exist_ok=True)
            if not pinned.exists():
                os.link(source, pinned)
            if digest(pinned) != item['sha256']:
                raise ValueError('Pinned integration archive differs')
            item['localPath'] = str(pinned.relative_to(ROOT))
        uploads.append({'source': str(ROOT / 'work/app-bundles-v1' / region),
                        'remote': 'r2:baregps-production-assets/OpenBareMap/' + region + '/2.0.0/app-bundles-v1',
                        'exclude': '**/payload/**'})
    write(catalog_path, catalog)
    uploads.extend([
        {'source': str(preview), 'remote': 'r2:baregps-production-assets/OpenBareMap/norway/2.0.0/preview'},
        {'source': str(public_garmin), 'remote': 'r2:baregps-production-assets/Garmin'},
        {'source': str(catalog_path), 'remote': 'r2:baregps-production-assets/OpenBareMap/app-bundles-v1/catalog.json', 'singleFile': True},
    ])
    write(ROOT / 'work/norway-publication-plan.json', {
        'status': 'prepared locally; not published', 'uploads': uploads,
        'previewUIStaging': 'work/norway-preview-ui-staging-20261114',
        'publicationOrder': 'Upload maps and kits, verify public downloads, then publish preview navigation',
        **website,
    })
    print('All Norway publication files staged; uploads and public readbacks pending', flush=True)

if __name__ == '__main__':
    main()
