#!/usr/bin/env python3
"""Phase 10B: generate band-limited spectral shape variants offline.

No existing table is overwritten. The generated variants can be used in a
future runtime lookup layer after size and audio regression review.
"""
import math
from spectral_shape import spectral_shape, _fft

N = 256
BAND_LIMITS = (96, 64, 48, 32, 24, 16, 8, 4, 1)
SHAPES = (
    ("neutral", 0.0, 1.0),
    ("dark", -0.65, 1.0),
    ("bright", 0.45, 1.0),
    ("filtered", 0.0, 0.20),
)

def source_wave(harmonics, limit, n=N):
    """Deterministic original spectral source for validation, not an existing bank."""
    values = [0.0] * n
    for h in harmonics:
        if h > limit or h >= n // 2:
            continue
        weight = 0.5 / h
        for i in range(n):
            values[i] += weight * math.sin(2 * math.pi * h * i / n)
    return values

def make_variants(samples, band_limit, shapes=SHAPES):
    """Transform and explicitly suppress harmonics above the source band limit."""
    n = len(samples)
    if not 1 <= band_limit < n // 2:
        raise ValueError("invalid band limit")
    variants = {}
    for name, tilt, cutoff in shapes:
        shaped = spectral_shape(samples, tilt=tilt, cutoff=cutoff)
        bins = _fft(shaped)
        for h in range(band_limit + 1, n - band_limit):
            bins[h] = 0j
        clean = _fft(bins, inverse=True)
        variants[name] = [v.real for v in clean]
    return variants

def footprint_bytes(table_count, frames=4, bands=len(BAND_LIMITS),
                    variants=len(SHAPES), samples=N, bytes_per_sample=4):
    if min(table_count, frames, bands, variants, samples, bytes_per_sample) < 0:
        raise ValueError("negative dimension")
    return table_count * frames * bands * variants * samples * bytes_per_sample

if __name__ == "__main__":
    for count in (4, 104, 108):
        print(f"{count} tables, {len(SHAPES)} variants: {footprint_bytes(count):,} bytes")
