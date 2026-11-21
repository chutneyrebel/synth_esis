"""Audio-safe precomputed 2x2x2 spectral corner regression tests."""
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from spectral_composition import (CORNER_MASKS, CORNER_NAMES, PEAK_LIMIT,
                                  compose_bins, compose_from_base, compose_row)
from curated_wavetables import generate_row
from generate_shape_variants import BAND_LIMITS, N
from spectral_shape import _fft


class ComposedSpectralTests(unittest.TestCase):
    def test_eight_corners_and_exact_neutral(self):
        self.assertEqual(CORNER_MASKS, tuple(range(1, 8)))
        self.assertEqual(len(CORNER_NAMES), 7)
        for table in (0, 7, 12):
            base = generate_row(table, 2, BAND_LIMITS[0])
            self.assertEqual(compose_from_base(base, 2, BAND_LIMITS[0], table, 0), base)

    def test_all_corner_rows_are_bandlimited_and_peak_safe(self):
        for limit in BAND_LIMITS:
            for mask in CORNER_MASKS:
                row = compose_row(7, 2, limit, mask)
                self.assertEqual(len(row), N)
                self.assertTrue(all(math.isfinite(v) for v in row))
                self.assertLessEqual(max(abs(v) for v in row), PEAK_LIMIT + 1e-8)
                self.assertLess(abs(sum(row) / N), 1e-7)
                spectrum = _fft(row)
                for harmonic in range(limit + 1, N // 2 + 1):
                    self.assertLess(abs(spectrum[harmonic]), 1e-6,
                                    (mask, limit, harmonic))

    def test_operators_are_independent_and_composed(self):
        table, frame, limit = 7, 2, BAND_LIMITS[0]
        rows = [compose_row(table, frame, limit, mask) for mask in range(8)]
        self.assertEqual(len({tuple(round(x, 5) for x in row) for row in rows}), 8)
        # A true composed corner is different from the mean of three singles.
        naive = [(rows[1][i] + rows[2][i] + rows[4][i]) / 3.0
                 for i in range(N)]
        difference = math.sqrt(sum((rows[7][i] - naive[i]) ** 2
                                   for i in range(N)) / N)
        self.assertGreater(difference, 0.01)

    def test_protected_low_harmonics_and_seed_repeatability(self):
        for mask in CORNER_MASKS:
            x = [0j] * (N // 2 + 1)
            x[1], x[2], x[3], x[15], x[63] = 4 + 2j, 3j, -2 + 1j, 2 + 1j, 8 - 3j
            a = compose_bins(x, mask, BAND_LIMITS[0], seed=123)
            b = compose_bins(x, mask, BAND_LIMITS[0], seed=123)
            self.assertEqual(a, b)
            self.assertEqual(a[1:4], x[1:4])
            self.assertEqual(a[0], 0j)
            self.assertEqual(a[128], 0j)
            self.assertEqual(x[63], 8 - 3j)

    def test_silence_stays_silent(self):
        for mask in CORNER_MASKS:
            self.assertEqual(compose_bins([0j] * 129, mask, BAND_LIMITS[0]),
                             [0j] * 129)

    def test_runtime_has_smoothing_and_only_immutable_lookup(self):
        dsp = (ROOT / "src/dsp.c").read_text()
        self.assertIn("float smooth_spectral[2][3]", dsp)
        self.assertIn("for(int mask=1;mask<=SYNTH_ESIS_SPECTRAL_MODES;mask++)", dsp)
        self.assertIn("spectral_table_at(mask-1,index,p0,band,phase)", dsp)
        self.assertIn("if(total<=0.f)return original", dsp)
        self.assertNotIn('#include "spectral_bins.h"', dsp)
        for osc in (0, 1):
            for axis in range(3):
                self.assertIn(f"s->smooth_spectral[{osc}][{axis}]+=.004f*", dsp)
        self.assertNotIn(".01f*s->osc1_spectral_shift", dsp)
        self.assertNotIn(".01f*s->osc2_spectral_shift", dsp)
        self.assertIn("float x=spectral_morph_at(source1,pos,v->band,p1", dsp)
        self.assertIn("float second=spectral_morph_at(source2,pos2,v->band,p2", dsp)


if __name__ == "__main__":
    unittest.main()
