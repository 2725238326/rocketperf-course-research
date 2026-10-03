"""Immutable synthetic cycle archive integrity; no engine-validation claim."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from cycle_validation import check_archive


class CycleArchiveTests(unittest.TestCase):
    def test_fixed_archive_and_equations(self):
        self.assertEqual(len(check_archive(ROOT/'results/validation/prescribed_cycle_v1_20261004')),86)

    def test_modified_result_and_missing_file_rejected(self):
        (ROOT/'build/test-tmp').mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='cycle-archive-',dir=ROOT/'build/test-tmp') as temporary:
            folder=Path(temporary)/'archive'
            shutil.copytree(ROOT/'results/validation/prescribed_cycle_v1_20261004',folder)
            result=json.loads((folder/'result.json').read_text(encoding='utf-8'))
            result['energy']['pump_power_w']*=2
            (folder/'result.json').write_text(json.dumps(result),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'hash mismatch'): check_archive(folder)
            (folder/'result.json').unlink()
            with self.assertRaises(OSError): check_archive(folder)


if __name__=='__main__': unittest.main(verbosity=2)
