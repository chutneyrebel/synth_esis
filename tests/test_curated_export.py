#!/usr/bin/env python3
"""Curated bank export contract."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from export_curated_wavetables import export
from curated_wavetables import NAMES
from custom_wavetable import load

class CuratedExportTests(unittest.TestCase):
    def test_all_sixteen_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = export(directory)
            self.assertEqual(len(paths), 16)
            self.assertEqual(len({p.name for p in paths}), 16)
            for index, path in enumerate(paths):
                data = load(path)
                self.assertEqual(data["name"], NAMES[index])
                self.assertEqual(len(data["frames"]), 4)
                self.assertEqual(len(data["frames"][0]), 256)
    def test_deterministic_exports(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            left = export(first)
            right = export(second)
            self.assertEqual([p.read_bytes() for p in left],
                             [p.read_bytes() for p in right])
if __name__ == "__main__":
    unittest.main()
