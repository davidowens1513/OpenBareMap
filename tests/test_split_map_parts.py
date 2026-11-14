from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from split_map_parts import split_map
from restore_map_parts import restore


class SplitSelectedMapTests(unittest.TestCase):
    def test_split_then_restore_preserves_every_byte(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / 'maps/test.mbtiles'
            path.parent.mkdir(); original = bytes(range(256)) * 37 + b'last partial block'
            path.write_bytes(original)
            record = split_map(path, root=root, part_bytes=1024)
            self.assertEqual(sum(p['bytes'] for p in record['parts']), len(original))
            path.unlink()
            restore(path.with_name(path.name + '.parts.json'), root=root)
            self.assertEqual(path.read_bytes(), original)

    def test_changed_existing_part_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / 'test.mbtiles'; path.write_bytes(b'original map bytes')
            record = split_map(path, root=root, part_bytes=8)
            part = root / record['parts'][0]['path']; part.write_bytes(b'changed!')
            with self.assertRaisesRegex(ValueError, 'Existing map part differs'):
                split_map(path, root=root, part_bytes=8)
            self.assertEqual(part.read_bytes(), b'changed!')
