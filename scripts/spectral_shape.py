#!/usr/bin/env python3
"""Phase 10B offline spectral shaping. No runtime Move DSP dependency."""
import cmath
import math

def _fft(values, inverse=False):
    """In-place radix-2 Cooley-Tukey transform, standard-library only."""
    n = len(values)
    if n < 4 or n & (n - 1):
        raise ValueError("FFT length must be a power of two >= 4")
    a = [complex(x) for x in values]
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    size = 2
    while size <= n:
        root = cmath.exp((1j if inverse else -1j) * 2 * math.pi / size)
        for start in range(0, n, size):
            w = 1 + 0j
            for k in range(size // 2):
                u = a[start + k]
                v = a[start + k + size // 2] * w
                a[start + k] = u + v
                a[start + k + size // 2] = u - v
                w *= root
        size <<= 1
    if inverse:
        return [v / n for v in a]
    return a

def spectral_shape(samples, tilt=0.0, cutoff=1.0, mix=1.0):
    """Shape a periodic real waveform via harmonic amplitudes.

    tilt: -1..1, positive brightens upper harmonics
    cutoff: 0..1, soft harmonic lowpass; 1 bypasses
    mix: 0..1, 0 is exact bypass
    """
    n = len(samples)
    if n < 4 or n & (n - 1):
        raise ValueError("sample count must be a power of two >= 4")
    if not all(math.isfinite(x) for x in samples):
        raise ValueError("non-finite waveform sample")
    if not all(math.isfinite(x) for x in (tilt, cutoff, mix)):
        raise ValueError("non-finite shaping parameter")
    if not -1 <= tilt <= 1 or not 0 <= cutoff <= 1 or not 0 <= mix <= 1:
        raise ValueError("shaping parameter out of range")
    if mix == 0 or (tilt == 0 and cutoff == 1):
        return list(samples)
    bins = _fft(samples)
    nyquist = n // 2
    for harmonic in range(1, nyquist + 1):
        gain = harmonic ** tilt
        if cutoff < 1:
            edge = max(1.0, cutoff * nyquist)
            gain *= 1.0 / (1.0 + (harmonic / edge) ** 8)
        gain = min(gain, 8.0)
        bins[harmonic] *= gain
        if harmonic != nyquist:
            bins[n - harmonic] *= gain
    shaped = _fft(bins, inverse=True)
    return [original + mix * (value.real - original)
            for original, value in zip(samples, shaped)]
