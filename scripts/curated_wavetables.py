#!/usr/bin/env python3
"""16 audibly evolving curated wavetables for Synth_esis.

Offline-only. Four frames, nine band limits, 256 samples per row.
Does not modify legacy 108 table IDs or Move runtime.
"""
import math
from spectral_shape import _fft
from generate_shape_variants import BAND_LIMITS, N

NAMES = ("Sine", "Saw", "Square", "Triangle", "Odd", "Formant",
         "Hollow", "Metallic", "Glass", "Vocal", "Organic", "Resonant",
         "Inharmonic", "Spectral Sweep", "Fractal", "Noise-like")
FRAMES = 4

def _bell(h, center, width):
    """Compact harmonic formant: positive and deterministic, with no runtime DSP."""
    z = (h - center) / width
    return math.exp(-0.5 * z * z)


def harmonic_weight(table, h, frame):
    """Four intentionally contrasting timbral scenes per curated wavetable.

    Previous frames mostly altered phase or a weak spectral tilt, leaving
    Position practically inaudible. New frames move actual harmonic energy
    among low, mid, and high formants. Interpolation happens in the Move DSP
    between precomputed, pitch-band-limited rows, never in this generator.
    """
    f = int(frame)
    t = f / (FRAMES - 1)
    bell = _bell
    if table == 0:
        return 1.0 if h == 1 else 0.0  # Pure sine is intentionally static
    if table == 1:  # Analog saw: mellow -> classic -> vowel -> cutting
        base = h ** (-[1.65, 1.05, 0.8, 0.65][f])
        return base * [1.0, 1.0,
                       0.18 + 2.0 * bell(h, 7, 2.0) + 1.25 * bell(h, 18, 3.0),
                       0.20 + 1.4 * bell(h, 12, 3.2) + 1.1 * bell(h, 25, 4.0)][f]
    if table == 2:  # Odd square: deep -> open -> pinched -> abrasive
        if h % 2 == 0:
            return 0.0
        return h ** (-[1.7, 1.0, 0.75, 0.55][f]) * [
            1.0, 1.0,
            0.2 + 2.4 * bell(h, 9, 2.5),
            0.2 + 2.4 * bell(h, 17, 4.5) + bell(h, 5, 1.2)][f]
    if table == 3:  # Triangle to resonant odd-partial shimmer
        if h % 2 == 0:
            return 0.0
        return h ** (-[2.4, 1.9, 1.2, 0.95][f]) * [
            1.0, 1.0, 0.2 + 4.0 * bell(h, 7, 2.0),
            0.15 + 4.0 * bell(h, 15, 3.0)][f]
    if table == 4:  # Hollow odd: moving harmonic gaps
        if h % 2 == 0:
            return 0.02 / h
        return h ** (-[1.35, 0.85, 0.72, 0.58][f]) * [
            0.2 + 2 * bell(h, 3, 2.0),
            0.15 + 2.5 * bell(h, 9, 2.3),
            0.1 + 3.0 * bell(h, 17, 3.0),
            0.15 + 2.3 * bell(h, 7, 1.4) + 2.1 * bell(h, 23, 4.0)][f]
    if table == 5:  # Formant: moving double-vowel bands
        centers = ((3, 9), (5, 14), (8, 21), (4, 26))
        a, b = centers[f]
        return (0.38 if h == 1 else 0.045 / h) + 1.7 * bell(h, a, 1.7) + 1.4 * bell(h, b, 2.6)
    if table == 6:  # Hollow: formants carve deep contrasting cavities
        base = h ** (-[1.55, 1.0, 0.78, 0.75][f])
        return base * [0.25 + 2.0 * bell(h, 4, 1.3),
                       0.12 + 2.7 * bell(h, 10, 2.2),
                       0.12 + 2.7 * bell(h, 19, 3.3),
                       0.12 + 2.5 * bell(h, 5, 1.2) + 2.2 * bell(h, 25, 3.0)][f]
    if table == 7:  # Metallic: low clang -> brassy ring -> shattered -> razor
        scenes = (((4, 1.4, 1.8), (9, 1.3, 2.0), (17, 0.6, 2.4)),
                  ((8, 1.6, 1.4), (14, 1.3, 2.0), (23, 0.9, 3.0)),
                  ((5, 1.3, 1.0), (17, 1.7, 1.7), (29, 1.1, 2.6)),
                  ((11, 1.8, 1.2), (20, 1.4, 2.0), (33, 1.3, 3.0)))
        return (0.37 if h == 1 else 0.012 / (h ** 0.4)) + sum(
            a * bell(h, center, width) for center, a, width in scenes[f])
    if table == 8:  # Glass: low bell -> struck plates -> bright split -> glass rain
        scenes = ((6, 13, 20), (9, 16, 27), (4, 19, 33), (12, 25, 38))
        a, b, c = scenes[f]
        return (0.19 if h == 1 else 0.015 / h) + (
            1.2 * bell(h, a, 0.9) + 1.0 * bell(h, b, 1.5) + 0.75 * bell(h, c, 2.0))
    if table == 9:  # Vocal: shifting two-vowel formants
        scenes = ((3, 11, 18), (5, 14, 23), (8, 20, 29), (4, 9, 34))
        a, b, c = scenes[f]
        return (0.18 if h == 1 else 0.01 / h) + (
            1.7 * bell(h, a, 1.0) + 1.4 * bell(h, b, 1.6) + 0.9 * bell(h, c, 2.4))
    if table == 10:  # Organic: asymmetric bloom, dark -> open -> tense -> diffuse
        center = (3, 8, 16, 27)[f]
        return (0.28 if h == 1 else 0.025 / h) + (
            1.4 * bell(h, center, 1.7 + f) +
            0.8 * bell(h, center * 1.75, 2.3 + f) +
            0.3 * abs(math.sin(h * (0.39 + f * 0.17))) / (h ** 0.65))
    if table == 11:  # Resonant: sharply migrating formant whistle
        center = (4, 9, 17, 30)[f]
        return (0.27 if h == 1 else 0.02 / h) + (
            2.2 * bell(h, center, 1.0 + 0.6 * f) +
            0.7 * bell(h, center * 1.55, 2.0))
    if table == 12:  # Bell partials: sparse non-octave *harmonic indices*
        centers = ((2, 5, 9), (4, 11, 17), (7, 15, 26), (3, 19, 37))
        a, b, c = centers[f]
        return (0.18 if h == 1 else 0.005 / h) + (
            1.3 * bell(h, a, 0.55) + 1.2 * bell(h, b, 0.75) +
            1.2 * bell(h, c, 1.1))
    if table == 13:  # Spectral sweep: radically migrating narrow harmonic island
        center = (3, 9, 18, 34)[f]
        return (0.28 if h == 1 else 0.02 / h) + (
            2.2 * bell(h, center, 2.0 + f * 0.8) +
            0.8 * bell(h, center * 1.6, 2.5))
    if table == 14:  # Fractal: multiple recursively displaced clusters
        root = (3, 6, 11, 19)[f]
        return (0.24 if h == 1 else 0.012 / h) + (
            1.35 * bell(h, root, 0.85) + 1.1 * bell(h, root * 2 + 1, 1.3) +
            0.9 * bell(h, root * 3 + 2, 2.1))
    # Noise-like: pitch-locked rough harmonic mist, not broadband noise
    center = (5, 11, 20, 35)[f]
    texture = (0.3 + 0.7 * abs(math.sin(h * (9.91 + f * 1.3) + table * 13.0)))
    return (0.20 if h == 1 else 0.01 / h) + (
        1.7 * bell(h, center, 3.5 + f * 1.2) * texture +
        0.5 * bell(h, center * 1.5, 5.0) * texture)

def generate_row(table, frame, limit):
    if not 0 <= table < len(NAMES) or not 0 <= frame < FRAMES or limit not in BAND_LIMITS:
        raise ValueError("invalid table/frame/band")
    bins = [0j] * N
    for h in range(1, limit + 1):
        weight = harmonic_weight(table, h, frame)
        phase = (h * h * 0.037 + frame * h * 0.13) if table >= 7 else 0.0
        coefficient = 0.5j * weight * complex(math.cos(phase), math.sin(phase))
        bins[h] = -coefficient
        bins[N-h] = coefficient.conjugate() * -1
    row = [x.real for x in _fft(bins, inverse=True)]
    peak = max(abs(x) for x in row)
    if peak:
        row = [0.8 * x / peak for x in row]
    return row

def generate_bank():
    return [[ [generate_row(table, frame, limit) for limit in BAND_LIMITS]
              for frame in range(FRAMES)] for table in range(len(NAMES))]

def raw_float32_bytes():
    return len(NAMES) * FRAMES * len(BAND_LIMITS) * N * 4

if __name__ == "__main__":
    print("Curated tables:", len(NAMES))
    print("Float32 bytes:", raw_float32_bytes())
