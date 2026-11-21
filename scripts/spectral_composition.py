#!/usr/bin/env python3
"""Offline compositional spectral wavetable corners (Shift -> Fold -> Scramble).

Seven transformed endpoints plus the exact original supply a 2x2x2
trilinear spectral cube. Runtime playback only interpolates immutable tables,
never calls an FFT or allocates memory. All output remains single-cycle and
harmonic, not truly inharmonic.
"""
import math
from curated_wavetables import N, generate_row
from generate_shape_variants import BAND_LIMITS
from spectral_shape import _fft

CORNER_MASKS = tuple(range(1, 8))
CORNER_NAMES = ("Shift", "Fold", "Shift+Fold", "Scramble",
                "Shift+Scramble", "Fold+Scramble", "Shift+Fold+Scramble")
PROTECTED_HARMONICS = 3
PEAK_LIMIT = 0.8


def compose_bins(bins, mask, ceiling, protect=PROTECTED_HARMONICS, seed=1):
    """Apply the same full-depth integer-bin routing as spectral_bins.h.

    bins: 129 nonredundant complex bins. Never modifies the input in place.
    Only bins 1..ceiling contribute to the time-domain output.
    """
    if len(bins) != N // 2 + 1 or mask not in range(8):
        raise ValueError("invalid spectral bins or corner")
    if ceiling not in BAND_LIMITS:
        raise ValueError("invalid harmonic ceiling")
    x = [complex(z) for z in bins]
    if mask == 0:
        return x
    top = min(127, max(1, ceiling))
    p = min(top, max(0, protect))
    if mask & 1:  # Shift upward, respecting pitch-band ceiling
        y = [v if not p < k <= top else 0j for k, v in enumerate(x)]
        distance = min(12, max(1, (top - p) // 3))
        for k in range(p + 1, top + 1):
            if k + distance <= top:
                y[k + distance] += x[k]
        x = y
    if mask & 2 and top > p + 1:  # Triangular fold through audible mid harmonics
        span = max(1, min(8, (top - p) // 2))
        period = 2 * span
        y = [v if not p < k <= top else 0j for k, v in enumerate(x)]
        for k in range(p + 1, top + 1):
            offset = (k - p - 1) % period
            target = p + 1 + (offset if offset <= span else period - offset)
            y[target] += x[k]
        x = y
    if mask & 4 and top > p + 1:  # Deterministic complex-bin permutation
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
        x = y
    for k in range(top + 1, N // 2 + 1):
        x[k] = 0j
    x[N // 2] = 0j
    # Match the C operator: preserve DC here; remove it after reconstruction.
    return x


def compose_from_base(base, frame, limit, table, mask, base_spectrum=None):
    """Generate a bounded, DC-free, energy-matched corner from a base row.

    Extended to original 0..107 source IDs for full WT spectral support.
    An optional precomputed spectrum avoids re-running the FFT seven times
    for every table when building the immutable bank.
    """
    if len(base) != N or not 0 <= frame < 4 or not 0 <= table < 108:
        raise ValueError("invalid source row")
    if mask not in range(8) or limit not in BAND_LIMITS:
        raise ValueError("invalid corner or band")
    if mask == 0:
        return list(base)  # exact original, including float spelling
    spectrum = list(base_spectrum) if base_spectrum is not None else _fft(base)[:N // 2 + 1]
    if len(spectrum) != N // 2 + 1:
        raise ValueError("invalid prepared spectrum")
    # A fundamentally pure waveform has no upper partials to move or fold.
    # Seed a modest, fixed harmonic scaffold *only in the wet endpoints*,
    # keeping dry lookup byte-identical while giving controls a sonic target.
    if limit >= 8:
        mid_energy = sum(abs(spectrum[k]) ** 2 for k in range(4, min(limit, 127) + 1))
        low_energy = sum(abs(spectrum[k]) ** 2 for k in range(1, 4))
        if low_energy > 1e-12 and mid_energy < .025 * low_energy:
            fundamental = spectrum[1] if abs(spectrum[1]) > 1e-9 else spectrum[2]
            for harmonic, level in ((6, .21), (11, .16), (17, .13), (23, .1)):
                if harmonic <= limit:
                    spectrum[harmonic] += fundamental * level * complex(
                        math.cos(harmonic * .71 + frame * .3),
                        math.sin(harmonic * .71 + frame * .3))
    # Fixed per-table/frame/band seed makes every mask a consistent composition.
    seed = ((table + 1) * 0x9e3779b1 ^ (frame + 1) * 0x85ebca6b ^ limit) & 0xffffffff
    positive = compose_bins(spectrum, mask, limit, seed=seed)
    full = positive + [positive[N - k].conjugate() for k in range(N // 2 + 1, N)]
    values = [z.real for z in _fft(full, inverse=True)]
    mean = sum(values) / N
    values = [v - mean for v in values]
    base_rms = math.sqrt(sum(v * v for v in base) / N)
    rms = math.sqrt(sum(v * v for v in values) / N)
    peak = max(abs(v) for v in values)
    if rms < 1e-12 or peak < 1e-12:
        return [0.0] * N
    gain = min(base_rms / rms, PEAK_LIMIT / peak)
    return [v * gain for v in values]


def compose_row(table, frame, limit, mask):
    return compose_from_base(generate_row(table, frame, limit), frame, limit, table, mask)
