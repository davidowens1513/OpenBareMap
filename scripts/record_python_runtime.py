"""Record the installed, pinned regional build dependencies without downloading."""
import argparse
import importlib.metadata
import platform
import sys
from openbaremap import ROOT, digest, write
from regions import REGIONS, region_path

def record(region):
    requirements = ROOT / 'scripts/requirements-regions.txt'
    packages = {}
    for line in requirements.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name, expected = line.split('==')
        actual = importlib.metadata.version(name)
        if actual != expected:
            raise ValueError(f'Pinned package differs: {name}: expected {expected}, found {actual}')
        packages[name] = actual
    result = {'python': sys.version, 'platform': platform.platform(), 'packages': packages,
              'requirementsSHA256': digest(requirements)}
    path = region_path(region, 'python-runtime.json')
    if path.exists():
        raise FileExistsError('Runtime provenance already recorded: ' + str(path))
    write(path, result)
    print('Pinned Python runtime recorded:', region, flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--region', choices=REGIONS, required=True)
    record(parser.parse_args().region)
