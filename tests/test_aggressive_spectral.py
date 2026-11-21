"""Phase 10B.2: deterministic, bounded harmonic-domain spectral algorithms."""
import math
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from aggressive_spectral import MODES,transform_row
from curated_wavetables import generate_row
from generate_shape_variants import BAND_LIMITS,N

class AggressiveSpectralTests(unittest.TestCase):
    def test_neutral_bit_identical(self):
        for t in (0,5,7,12,15):
            for mode in range(3):
                self.assertEqual(transform_row(t,1,BAND_LIMITS[0],mode,0),
                                 generate_row(t,1,BAND_LIMITS[0]))
    def test_deterministic_and_bounded(self):
        for mode in range(3):
            for limit in BAND_LIMITS:
                a=transform_row(7,2,limit,mode,1)
                self.assertEqual(len(a),N)
                self.assertEqual(a,transform_row(7,2,limit,mode,1))
                self.assertTrue(all(math.isfinite(v) and abs(v)<=.801 for v in a))
                self.assertLess(abs(sum(a)/N),1e-5)
    def test_audibly_distinct_proxy(self):
        base=generate_row(7,2,BAND_LIMITS[0])
        for mode in range(3):
            changed=transform_row(7,2,BAND_LIMITS[0],mode,1)
            difference=math.sqrt(sum((a-b)**2 for a,b in zip(base,changed))/N)
            self.assertGreater(difference,.08,(MODES[mode],difference))
    def test_fold_preserves_fundamental_and_reflects_above_ceiling(self):
        from aggressive_spectral import _target
        for depth in (0.0001, 0.1, 0.5, 1.0):
            self.assertEqual(_target(1, 1, depth, 64, 0), 1)
        # At depth=1, ceiling=15: harmonics 1..15 stay in order.
        self.assertEqual([_target(1, h, 1.0, 64, 0) for h in range(1, 18)],
                         list(range(1, 16)) + [14, 13])
        # The previous implementation reversed the fundamental to harmonic 15.
        self.assertEqual(_target(1, 2, 0.0001, 64, 0), 2)

    def test_invalid(self):
        with self.assertRaises(ValueError):transform_row(0,0,BAND_LIMITS[0],0,1.1)
        with self.assertRaises(ValueError):transform_row(0,0,BAND_LIMITS[0],3,0.5)

if __name__=="__main__":unittest.main()
