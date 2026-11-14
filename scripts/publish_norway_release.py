#!/usr/bin/env python3
"""Publish the prepared Norway release, verify readbacks, then update navigation."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
from openbaremap import ROOT, digest, write
from verify_app_distribution import verify, read_hash

REGIONS = ('norway-south', 'norway-central', 'norway-north')

def run(*args):
    subprocess.run(list(map(str, args)), cwd=ROOT, check=True)

def pages_target(project):
    if not shutil.which('wrangler') and not shutil.which('npx'):
        raise ValueError('Website deployment requires Wrangler or Node.js/npx in this Terminal. '
                         'Run without --website to publish maps first; the prepared website ZIP '
                         'can then be uploaded to the existing appsbyonzy Pages project.')
    command = ['wrangler'] if shutil.which('wrangler') else ['npx', '--yes', 'wrangler']
    response = subprocess.check_output([*command, 'pages', 'project', 'list', '--json'], cwd=ROOT, text=True)
    projects = json.loads(response)
    if isinstance(projects, dict):
        projects = projects.get('result', projects.get('projects', []))
    for item in projects:
        normalized = {str(k).lower().replace('_', '').replace(' ', ''): v for k, v in item.items()}
        if normalized.get('name', normalized.get('projectname')) == project:
            branch = normalized.get('productionbranch')
            if isinstance(branch, str) and branch:
                return command, branch
    raise ValueError('Cannot identify the existing Pages project and production branch: ' + project)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--publish', action='store_true', help='Upload and verify the staged release; otherwise show its plan')
    parser.add_argument('--website', action='store_true', help='Deploy the reviewed website after all map readbacks pass')
    args = parser.parse_args()
    plan = json.loads((ROOT / 'work/norway-publication-plan.json').read_text())
    if plan['status'] != 'prepared locally; not published':
        raise ValueError('Publication plan is not ready')
    if not args.publish:
        print(json.dumps(plan, indent=2))
        return
    if not shutil.which('rclone'):
        raise ValueError('The configured rclone client is required')
    pages = None
    if args.website:
        if digest(ROOT / plan['websiteSource']) != plan['websiteSourceSHA256'] or digest(ROOT / plan['websiteArchive']) != plan['websiteArchiveSHA256']:
            raise ValueError('Website changed after staging; prepare publication again')
        print('Checking the existing Cloudflare Pages production project', flush=True)
        pages = pages_target(plan['cloudflarePagesProject'])
    for item in plan['uploads']:
        if not item['remote'].startswith('r2:baregps-production-assets/'):
            raise ValueError('Unexpected publication destination')
        print('Publishing', item['remote'], flush=True)
        command = ['rclone', 'copyto' if item.get('singleFile') else 'copy', item['source'], item['remote'],
                   '--checksum', '--s3-no-check-bucket', '--transfers', '4', '--s3-upload-concurrency', '2']
        if item.get('exclude'):
            command += ['--exclude', item['exclude']]
        run(*command)
    native_checks = {}
    for region in REGIONS:
        verify(region)
        path = ROOT / 'distribution/app-bundles-v1/garmin' / region / 'manifest.json'
        manifest = json.loads(path.read_text())
        size, sha, mime = read_hash(manifest['downloadURL'])
        if size != manifest['bytes'] or sha != manifest['imageSHA256']:
            raise ValueError('Public Garmin image differs: ' + region)
        manifest.update(fullPublicReadbackVerified=True, verifiedUTC=datetime.now(timezone.utc).isoformat())
        write(path, manifest); native_checks[region] = {'bytes': size, 'sha256': sha}
        run('rclone', 'copyto', path,
            'r2:baregps-production-assets/Garmin/' + region + '/manifest.json', '--s3-no-check-bucket')
    # Existing preview menus must not point at the new maps until uploads pass.
    staging = ROOT / 'work' / ('norway-live-preview-ui-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S'))
    run(sys.executable, 'scripts/publish_preview_ui.py', '--output', staging)
    if pages is not None:
        command, branch = pages
        run(*command, 'pages', 'deploy', ROOT / 'web-preview/site',
            '--project-name=' + plan['cloudflarePagesProject'], '--branch=' + branch)
        request = urllib.request.Request('https://appsbyonzy.dev/?release=20261114-norway', headers={'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(request, timeout=60) as response:
            html = response.read().decode('utf-8')
        for label in ('Southern Norway', 'Central Norway', 'Northern Norway', 'BareGPS Tools', 'Figuring out how to steer them'):
            if label not in html:
                raise ValueError('Production website has not returned the reviewed content: ' + label)
    write(ROOT / 'web-preview/verification/norway-publication.json', {
        'verifiedUTC': datetime.now(timezone.utc).isoformat(), 'nativeReadbacks': native_checks,
        'phoneBundleReadbacks': True, 'previewNavigationPublished': True,
        'websiteDeployedAndChecked': pages is not None,
    })
    print('Norway maps published and full download readbacks verified', flush=True)

if __name__ == '__main__':
    main()
