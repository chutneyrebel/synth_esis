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
         "Bell Partials", "Spectral Sweep", "Fractal", "Noise-like")
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
    if table == 8:  # Glass: sparse glassy partials, not another metal cluster
        scenes = ((2, 5, 11), (3, 7, 14), (2, 9, 17), (4, 11, 23))
        a, b, c = scenes[f]
        return (0.13 if h == 1 else 0.003 / h) + (
            1.45 * bell(h, a, 0.42) + 1.0 * bell(h, b, 0.45) +
            0.72 * bell(h, c, 0.62))
    if table == 9:  # Vocal: continuously voiced buzz through wide, migrating vowels
        a, b = ((2, 6), (3, 8), (4, 10), (2, 11))[f]
        buzz = (1 if h % 2 else .62) / h ** (.63 + .09 * f)
        return buzz * (.18 + 2.5 * bell(h, a, 1.8) +
                       1.65 * bell(h, b, 2.9))
    if table == 10:  # Organic: PWM / analog pulse, with audible low partials
        duty = (.16, .28, .41, .49)[f]
        pulse = abs(math.sin(math.pi * h * duty))
        low = .07 + .93 * pulse
        return low / h ** (.54 + .11 * f) + (.27 if h == 1 else 0.0)
    if table == 11:  # Resonant: simple tonal reed with one mobile ringing partial
        overtone = (3, 5, 8, 12)[f]
        return (1.4 if h == 1 else 0.013 / h) + (
            2.2 * bell(h, overtone, .58) + .35 * bell(h, overtone * 2, .85))
    if table == 12:  # Bell Partials: thin, widely separated harmonic chimes
        scenes = ((2, 7, 13), (3, 8, 15), (2, 10, 19), (5, 12, 23))
        a, b, c = scenes[f]
        return (0.18 if h == 1 else 0.001 / h) + (
            1.7 * bell(h, a, .36) + 1.15 * bell(h, b, .42) +
            1.3 * bell(h, c, .55))
    if table == 13:  # Spectral Sweep: dense broadband saw with sweeping *notch*
        notch = (3, 5, 8, 11)[f]
        inverse_notch = 1.0 - .97 * bell(h, notch, 1.2 + f * .28)
        bright = h ** (-[1.2, .82, .65, .53][f])
        return bright * inverse_notch * (1.0 if h % 2 else .72)
    if table == 14:  # Fractal: deliberately structured harmonic combs/organ teeth
        spacing = (2, 3, 4, 5)[f]
        tooth = 1.0 if (h - 1) % spacing == 0 else .025
        secondary = .45 if (h - 2) % (spacing + 2) == 0 else 0.0
        return (tooth + secondary) / h ** (.38 + .12 * f)
    # Noise-like: broad, irregular phase-rich harmonic cloud (still pitched)
    jitter = abs(math.sin(h * (9.91 + f * 1.3) + table * 13.0))
    tilt = (.47, .35, .24, .18)[f]
    return (.08 + .92 * jitter) / h ** tilt

def generate_row(table, frame, limit):
    if not 0 <= table < len(NAMES) or not 0 <= frame < FRAMES or limit not in BAND_LIMITS:
        raise ValueError("invalid table/frame/band")
    bins = [0j] * N
    for h in range(1, limit + 1):
        weight = harmonic_weight(table, h, frame)
        # Do not give every upper curated sound the same spectral phase map.
        # Their differences should survive even with the filter partly closed.
        if table == 7: phase = h * h * .037 + frame * h * .13
        elif table == 8: phase = h * h * .23 + frame * h * .31
        elif table == 9: phase = h * .045 + frame * .08
        elif table == 10: phase = .45 * math.sin(h * .31 + frame * .65)
        elif table == 11: phase = .03 * h
        elif table == 12: phase = math.pi * (h % 3 == 0) + h * h * .17
        elif table == 13: phase = frame * .025 * h
        elif table == 14: phase = .27 * (h % 5) + .1 * frame * h
        elif table == 15: phase = h * h * (1.71 + frame * .13)
        else: phase = 0.0
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
