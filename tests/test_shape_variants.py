#!/usr/bin/env python3
"""Phase 10B band-limited spectral variant contract tests."""
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from generate_shape_variants import (N, SHAPES, BAND_LIMITS, source_wave,
                                     make_variants, footprint_bytes)
from spectral_shape import _fft

class ShapeVariantTests(unittest.TestCase):
    def test_variant_names_and_lengths(self):
        source = source_wave(range(1, 60), 24)
        variants = make_variants(source, 24)
        self.assertEqual(set(variants), {s[0] for s in SHAPES})
        self.assertTrue(all(len(v) == N for v in variants.values()))
    def test_high_harmonics_are_removed(self):
        source = source_wave(range(1, 100), 32)
        for samples in make_variants(source, 32).values():
            bins = _fft(samples)
            self.assertLess(max(abs(b) for b in bins[33:N-32]), 1e-8)
    def test_spectral_tilt_direction(self):
        source = source_wave(range(1, 17), 16)
        variants = make_variants(source, 16)
        def ratio(samples):
            bins = _fft(samples)
            return abs(bins[12]) / abs(bins[1])
        self.assertLess(ratio(variants["dark"]), ratio(variants["neutral"]))
        self.assertGreater(ratio(variants["bright"]), ratio(variants["neutral"]))
        self.assertLess(ratio(variants["filtered"]), ratio(variants["neutral"]))
    def test_footprint_budget(self):
        self.assertEqual(footprint_bytes(108), 108*4*9*4*256*4)
        self.assertGreater(footprint_bytes(108), 6_000_000)
        self.assertEqual(len(BAND_LIMITS), 9)
    def test_invalid_band(self):
        with self.assertRaises(ValueError):
            make_variants(source_wave([1], 1), N//2)
if __name__ == "__main__":
    unittest.main()
