import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('photon_status', ROOT / 'PHOTON/PHOTON_STATUS.py')
photon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(photon)


class PhotonInventoryTests(unittest.TestCase):
    def test_malformed_and_empty_inventory_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(photon, 'HERE', root):
                for value in ('', 'not a checksum', '0' * 64 + '  ../external\n'):
                    (root / 'SHA256SUMS.txt').write_text(value, encoding='utf-8')
                    self.assertFalse(photon.check_inventory()['ok'])

    def test_status_is_not_execution_attestation(self):
        doc = json.loads((ROOT / 'PHOTON/control_plane/config/photon_host.json').read_text(encoding='utf-8'))
        self.assertIs(doc['bound'], False)
        self.assertEqual(doc['integration_profile'], 'VENDORED_UNBOUND')


if __name__ == '__main__':
    unittest.main()
