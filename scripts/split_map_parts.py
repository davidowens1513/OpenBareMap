"""Pin large selected databases as independently verified Git LFS parts."""
import hashlib
from pathlib import Path
from openbaremap import ROOT, digest, write

def split_map(path, root=ROOT, part_bytes=1024**3):
    root = Path(root).resolve(); path = Path(path).resolve()
    if not path.is_relative_to(root) or part_bytes <= 0:
        raise ValueError('Invalid map path or part size')
    expected = digest(path); total = path.stat().st_size
    if not total:
        raise ValueError('Cannot pin an empty map')
    manifest = path.with_name(path.name + '.parts.json')
    parts = []; combined = hashlib.sha256()
    with path.open('rb') as source:
        for index, start in enumerate(range(0, total, part_bytes)):
            target = path.with_name(path.name + f'.part{index:02d}')
            temporary = target.with_name(target.name + '.building')
            count = min(part_bytes, total-start); remaining = count; sha = hashlib.sha256()
            out = None if target.exists() else temporary.open('wb')
            try:
                while remaining:
                    block = source.read(min(1024**2, remaining))
                    if not block:
                        raise ValueError('Source map shortened during splitting')
                    remaining -= len(block); sha.update(block); combined.update(block)
                    if out is not None:
                        out.write(block)
            finally:
                if out is not None:
                    out.close()
            if target.exists():
                if target.stat().st_size != count or digest(target) != sha.hexdigest():
                    raise ValueError('Existing map part differs: ' + str(target))
            else:
                temporary.rename(target)
            parts.append({'path': str(target.relative_to(root)), 'bytes': count,
                          'sha256': sha.hexdigest()})
    if combined.hexdigest() != expected or path.stat().st_size != total:
        raise ValueError('Source map changed during splitting')
    record = {'format': 'openbaremap-lfs-map-parts-v1', 'path': str(path.relative_to(root)),
              'bytes': total, 'sha256': expected, 'parts': parts}
    write(manifest, record)
    return record
