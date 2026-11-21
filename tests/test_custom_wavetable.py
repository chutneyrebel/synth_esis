#!/usr/bin/env python3
"""Phase 10B custom wavetable format and safety tests."""
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from custom_wavetable import encode, decode, save, load

def frames():
    return [[0.5 * math.sin(2 * math.pi * (i / 256) * (f + 1))
             for i in range(256)] for f in range(4)]

class CustomWavetableTests(unittest.TestCase):
    def test_roundtrip(self):
        data = encode("Test Wave", frames())
        self.assertEqual(decode(data)["frames"], frames())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wave.json"
            save(path, "Test Wave", frames())
            self.assertEqual(load(path)["name"], "Test Wave")
    def test_reject_invalid_samples(self):
        for value in (float("nan"), float("inf"), 1.01, True, "0"):
            samples = frames()
            samples[0][0] = value
            with self.assertRaises(ValueError):
                encode("Invalid", samples)
    def test_reject_bad_shape_and_version(self):
        with self.assertRaises(ValueError):
            encode("Bad", frames()[:3])
        data = json.loads(encode("Good", frames()))
        data["version"] = 2
        with self.assertRaises(ValueError):
            decode(json.dumps(data))
    def test_reject_duplicate_and_oversized_json(self):
        with self.assertRaises(ValueError):
            decode('{"version":1,"version":1}')
        with self.assertRaises(ValueError):
            decode("x" * 100001)
    def test_reject_extra_fields(self):
        data = json.loads(encode("Good", frames()))
        data["path"] = "../../bad"
        with self.assertRaises(ValueError):
            decode(json.dumps(data))
if __name__ == "__main__":
    unittest.main()
