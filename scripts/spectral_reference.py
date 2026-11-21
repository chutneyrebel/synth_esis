"""Offline spectral-transform reference for Synth_esis.

Not used in the audio callback. Standard-library-only, deliberately explicit
O(N^2) DFT/IDFT for deterministic reference vectors and small test tables.
"""
import cmath
import math
import random

SIZE = 256
BINS = SIZE // 2


def _check(samples, shift, fold, scramble):
    if len(samples) != SIZE:
        raise ValueError("expected 256 samples")
    if not all(math.isfinite(float(x)) for x in samples):
        raise ValueError("nonfinite samples")
    for depth in (shift, fold, scramble):
        if not isinstance(depth, (int, float)) or not math.isfinite(depth) or not 0 <= depth <= 1:
            raise ValueError("depth must be in [0, 1]")


def analyze(samples):
    """Positive-frequency DFT, including DC and Nyquist."""
    return [
        sum(samples[t] * cmath.exp(-2j * math.pi * k * t / SIZE)
            for t in range(SIZE))
        for k in range(BINS + 1)
    ]


def synthesize(spectrum):
    if len(spectrum) != BINS + 1:
        raise ValueError("expected 129 bins")
    # Real DC and Nyquist; all other bins have conjugate partners.
    full = [0j] * SIZE
    full[0] = complex(spectrum[0].real, 0)
    full[BINS] = complex(spectrum[BINS].real, 0)
    for k in range(1, BINS):
        full[k] = spectrum[k]
        full[SIZE - k] = spectrum[k].conjugate()
    return [
        (sum(full[k] * cmath.exp(2j * math.pi * k * t / SIZE)
             for k in range(SIZE)) / SIZE).real
        for t in range(SIZE)
    ]


def transform(samples, shift=0.0, fold=0.0, scramble=0.0, seed=0):
    """Compose Shift -> Fold -> Scramble on positive-frequency bins.

    Shift translates energy toward higher harmonics, Fold reflects the
    upper band back into the audible range, Scramble deterministically
    permutes harmonics. Each stage interpolates from its incoming state,
    not from the original signal. DC is preserved; Nyquist stays real.
    """
    _check(samples, shift, fold, scramble)
    if shift == fold == scramble == 0:
        return list(samples)  # Exact bypass; no DFT roundoff.
    x = analyze(samples)
    if shift:
        # Fractional upward translation of the non-DC harmonic band.
        displacement = 12.0 * shift
        moved = [0j] * (BINS + 1)
        moved[0] = x[0]
        for k in range(1, BINS):
            target = k + displacement
            low = int(target)
            frac = target - low
            if low < BINS:
                moved[low] += x[k] * (1 - frac)
            if low + 1 < BINS:
                moved[low + 1] += x[k] * frac
        x = [x[k] * (1 - shift) + moved[k] * shift for k in range(BINS + 1)]
    if fold:
        reflected = list(x)
        for k in range(1, BINS):
            # Reflect the upper half into the lower half; preserve low band.
            if k < BINS // 2:
                reflected[k] += x[BINS - k]
            else:
                reflected[k] = 0j
        x = [x[k] * (1 - fold) + reflected[k] * fold for k in range(BINS + 1)]
    if scramble:
        indices = list(range(1, BINS))
        shuffled = indices[:]
        random.Random(seed).shuffle(shuffled)
        shuffled_bins = list(x)
        for target, source in zip(indices, shuffled):
            shuffled_bins[target] = x[source]
        x = [x[k] * (1 - scramble) + shuffled_bins[k] * scramble
             for k in range(BINS + 1)]
    x[0] = complex(x[0].real, 0)
    x[BINS] = complex(x[BINS].real, 0)
    return synthesize(x)
