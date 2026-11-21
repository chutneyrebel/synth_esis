#!/usr/bin/env python3
"""Curated wavetable design contracts, not a Move DSP integration test."""
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from curated_wavetables import NAMES, FRAMES, N, BAND_LIMITS, generate_row, raw_float32_bytes
from spectral_shape import _fft

class CuratedWavetableTests(unittest.TestCase):
    def test_library_size_and_footprint(self):
        self.assertEqual(len(NAMES), 16)
        self.assertEqual(len(set(NAMES)), 16)
        self.assertEqual(raw_float32_bytes(), 16 * 4 * 9 * 256 * 4)
    def test_all_tables_are_finite_and_bounded(self):
        for table in range(16):
            for frame in range(FRAMES):
                for band in BAND_LIMITS:
                    row = generate_row(table, frame, band)
                    self.assertEqual(len(row), N)
                    self.assertTrue(all(math.isfinite(x) and abs(x) <= 0.800001 for x in row))
    def test_bandlimiting(self):
        for table in range(16):
            for limit in (1, 8, 32, 96):
                bins = _fft(generate_row(table, 2, limit))
                self.assertLess(max(abs(x) for x in bins[limit+1:N-limit]), 1e-7)
    def test_frames_evolve(self):
        for table in range(1, 16):
            a = generate_row(table, 0, 48)
            b = generate_row(table, 3, 48)
            self.assertGreater(max(abs(x-y) for x,y in zip(a,b)), 1e-5)
    def test_position_changes_harmonic_magnitudes_not_just_phase(self):
        # Old implementation varied phase noticeably while the audible
        # magnitude spectrum barely moved. Require broad spectral travel.
        def normalized_profile(table, frame, limit=48):
            bins=_fft(generate_row(table,frame,limit))
            magnitudes=[abs(bins[h]) for h in range(1,limit+1)]
            mass=sum(magnitudes) or 1.0
            return [x/mass for x in magnitudes]
        for table in range(1,16):
            profiles=[normalized_profile(table,f) for f in range(FRAMES)]
            for f in range(3):
                distance=sum(abs(a-b) for a,b in zip(profiles[f],profiles[f+1]))
                self.assertGreater(distance,.18,
                    (NAMES[table],f,f+1,"weak spectral position evolution",distance))
        metallic=[normalized_profile(7,f) for f in range(FRAMES)]
        for a,b in zip(metallic,metallic[1:]):
            self.assertGreater(sum(abs(x-y) for x,y in zip(a,b)),.42,
                               "Metallic Position must reshape harmonics")

    def test_sine_is_nearly_pure(self):
        bins = _fft(generate_row(0, 0, 96))
        self.assertLess(max(abs(x) for x in bins[2:96]), 1e-8)
if __name__ == "__main__":
    unittest.main()
