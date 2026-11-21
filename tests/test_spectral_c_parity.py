"""Cross-check the native C spectral-bin operators against an independent
Python translation of the same *quantized* Phase B contract.

This deliberately does not compare to spectral_reference.py, whose
fractional Shift and full-range Fold are different experimental algorithms.
"""
import ctypes
import math
import pathlib
import random
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class Complex(ctypes.Structure):
    _fields_ = [("re", ctypes.c_float), ("im", ctypes.c_float)]


def reference(values, shift, fold, scramble, seed, ceiling, protect):
    x = [complex(v) for v in values]
    top = min(127, max(1, ceiling))
    p = min(top, max(0, protect))
    ds, df, dc = (min(1.0, max(0.0, z)) for z in (shift, fold, scramble))
    if not (ds or df or dc):
        return x
    if ds:
        distance = min(int(12 * ds + 0.5), max(1, (top - p) // 3))
        y = [v if not p < k <= top else 0j for k, v in enumerate(x)]
        for k in range(p + 1, top + 1):
            if k + distance <= top:
                y[k + distance] += x[k]
        x = [x[k] * (1 - ds) + y[k] * ds if p < k <= top else x[k]
             for k in range(129)]
    if df and top > p + 1:
        span = max(1, min(8, (top - p) // 2))
        period = 2 * span
        y = [v if not p < k <= top else 0j for k, v in enumerate(x)]
        for k in range(p + 1, top + 1):
            offset = (k - p - 1) % period
            target = p + 1 + (offset if offset <= span else period - offset)
            y[target] += x[k]
        x = [x[k] * (1 - df) + y[k] * df if p < k <= top else x[k]
             for k in range(129)]
    if dc and top > p + 1:
        indices = list(range(p + 1, top + 1))
        state = (seed or 0x9e3779b9) & 0xffffffff
        for i in range(len(indices) - 1, 0, -1):
            state ^= (state << 13) & 0xffffffff
            state ^= state >> 17
            state ^= (state << 5) & 0xffffffff
            state &= 0xffffffff
            j = state % (i + 1)
            indices[i], indices[j] = indices[j], indices[i]
        y = list(x)
        for i, source in enumerate(indices):
            y[p + 1 + i] = x[source]
        x = [x[k] * (1 - dc) + y[k] * dc if p < k <= top else x[k]
             for k in range(129)]
    for k in range(top + 1, 129):
        x[k] = 0j
    x[128] = 0j
    return x


class SpectralCParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        wrapper = pathlib.Path(cls.tmp.name) / "wrapper.c"
        wrapper.write_text(
            '#include "spectral_bins.h"\n'
            'void spectral_test(se_complex *x,float a,float b,float c,'
            'unsigned seed,int ceiling,int protect){'
            'se_spectral_apply(x,a,b,c,seed,ceiling,protect);}\n'
        )
        lib = pathlib.Path(cls.tmp.name) / "spectral.so"
        subprocess.run(["gcc", "-std=c11", "-O2", "-shared", "-fPIC",
                        "-I", str(ROOT / "src"), str(wrapper), "-o", str(lib)],
                       check=True)
        cls.library = ctypes.CDLL(str(lib))
        cls.fn = cls.library.spectral_test
        cls.fn.argtypes = [ctypes.POINTER(Complex), ctypes.c_float,
                           ctypes.c_float, ctypes.c_float, ctypes.c_uint,
                           ctypes.c_int, ctypes.c_int]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_randomized_parity(self):
        rng = random.Random(20261121)
        for trial in range(64):
            values = [complex(rng.uniform(-0.5, 0.5),
                              rng.uniform(-0.5, 0.5)) for _ in range(129)]
            # Compare against float32 input, not Python's original doubles.
            c_array = (Complex * 129)(*(Complex(z.real, z.imag) for z in values))
            original = [complex(v.re, v.im) for v in c_array]
            shift, fold, scramble = [rng.choice([0, 0.25, 0.5, 0.75, 1])
                                     for _ in range(3)]
            seed = rng.randrange(1, 10000)
            ceiling = rng.choice([12, 32, 64, 96, 127])
            protect = rng.choice([0, 1, 3, 6])
            expected = reference(original, shift, fold, scramble,
                                 seed, ceiling, protect)
            self.fn(c_array, shift, fold, scramble, seed, ceiling, protect)
            for k, (got, want) in enumerate(zip(c_array, expected)):
                with self.subTest(trial=trial, bin=k):
                    self.assertTrue(math.isfinite(got.re) and math.isfinite(got.im))
                    self.assertAlmostEqual(got.re, want.real, delta=0.0001)
                    self.assertAlmostEqual(got.im, want.imag, delta=0.0001)


    def test_offline_generated_corners_match_native_full_depth_engine(self):
        # The shipped wavetable generator must agree with the same C engine
        # audited separately, including deterministic scramble permutations.
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from spectral_composition import compose_bins
        rng = random.Random(82315)
        for limit in (1, 4, 8, 16, 32, 64, 96):
            for mask in range(1, 8):
                values = [complex(rng.uniform(-0.5, 0.5),
                                  rng.uniform(-0.5, 0.5)) for _ in range(129)]
                c_array = (Complex * 129)(*(Complex(z.real, z.imag) for z in values))
                seed = rng.randrange(1, 100000)
                expected = compose_bins([complex(v.re, v.im) for v in c_array],
                                        mask, limit, protect=3, seed=seed)
                self.fn(c_array, float(bool(mask & 1)), float(bool(mask & 2)),
                        float(bool(mask & 4)), seed, limit, 3)
                for k, (got, want) in enumerate(zip(c_array, expected)):
                    with self.subTest(limit=limit, mask=mask, bin=k):
                        self.assertAlmostEqual(got.re, want.real, delta=0.0001)
                        self.assertAlmostEqual(got.im, want.imag, delta=0.0001)


if __name__ == "__main__":
    unittest.main()
