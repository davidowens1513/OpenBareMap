import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import stage_us_national_parks as publisher


class CollectionPublicationTests(unittest.TestCase):
    def test_failed_website_validation_preserves_both_public_catalogues(self):
        originals = {
            publisher.APP_CATALOGUE: b'{"regions": {"old": {}}, "mapVersions": {"old": "1"}}\n',
            publisher.WORLDWIDE_CATALOGUE: b'{"schemaVersion": 1, "regions": [{"id": "old"}]}\n',
        }
        with TemporaryDirectory() as temp:
            output = Path(temp)
            (output / 'app-bundles-catalog.json').write_text(json.dumps({
                'regions': {'new': {}}, 'mapVersions': {'new': '1'},
            }))
            (output / 'worldwide-catalog-v1.json').write_text(json.dumps({
                'schemaVersion': 1, 'regions': [{'id': 'new'}],
            }))
            (output / 'release-plan.json').write_text(json.dumps({'assets': [], 'regions': {'new': {}}}))

            def validate(_plan, count):
                self.assertEqual(count, 2)
                raise ValueError('invalid website')

            with (
                patch.object(publisher, 'public_catalogue', side_effect=originals.__getitem__),
                patch.object(publisher, 'upload_release_assets') as upload,
                patch.object(publisher, 'publish_preview_ui') as publish_preview,
                patch.object(publisher, 'transfer_asset') as transfer,
            ):
                with self.assertRaisesRegex(ValueError, 'invalid website'):
                    publisher.publish(output, None, regions=('new',), prepare_release=validate)
                upload.assert_not_called()
                publish_preview.assert_not_called()
                transfer.assert_not_called()

            backup = next((output / 'previous-catalogues').iterdir())
            for filename, key in publisher.CATALOGUES:
                self.assertEqual((backup / filename).read_bytes(), originals[key])


if __name__ == '__main__':
    unittest.main()
