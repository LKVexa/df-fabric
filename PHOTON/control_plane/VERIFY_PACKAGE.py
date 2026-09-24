"""Verify the vendored Photon inventory without requiring absent VM packages."""
from pathlib import Path
import sys

PHOTON_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PHOTON_ROOT))
from PHOTON_STATUS import check_inventory


def verify_package(strict=True):
    report = check_inventory()
    return {'verdict': 'PASS' if report['ok'] else 'FAIL', 'inventory': report,
            'scope': 'Vendored Photon static files; no native execution attestation.'}


if __name__ == '__main__':
    import json
    result = verify_package()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['verdict'] == 'PASS' else 1)
