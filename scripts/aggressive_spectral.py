#!/usr/bin/env python3
"""Original offline harmonic-domain transformations for Synth_esis.

No runtime FFT, allocations or third-party DSP. Harmonic weights are routed
through an output bin map and synthesized using the existing inverse FFT.
Neutral depth is a strict bypass and never changes existing tables.
"""
import math
from curated_wavetables import N, FRAMES, harmonic_weight
from generate_shape_variants import BAND_LIMITS
from spectral_shape import _fft

MODES = ("Shift", "Fold", "Scramble")

def _phase(table, h, frame):
    return h*h*0.037+frame*h*0.13 if table >= 7 else 0.0

def _target(mode, harmonic, depth, limit, frame):
    # A frequency-bin map rather than a time-domain phase warp.
    if mode == 0:
        # Aggressive upward shift: fundamental can move to 4th/8th/12th partial.
        return harmonic + int(round(depth * min(32, max(4, limit//2))))
    if mode == 1:
        # Preserve lower harmonics; reflect only those crossing the spectral ceiling.
        ceiling=max(3, int(round(limit*(1.0-0.76*depth))))
        offset=(harmonic-1) % (2*ceiling-2)
        return 1 + min(offset, 2*ceiling-2-offset)
    # Deterministic scrambled harmonic bins; depth controls displacement.
    seed=(harmonic*73+frame*47+19) % 127
    displacement=int(round(depth*(seed-63)*0.46))
    return harmonic+displacement

def transform_row(table, frame, limit, mode, depth):
    if not 0 <= table < 16 or not 0 <= frame < FRAMES or limit not in BAND_LIMITS:
        raise ValueError("invalid wavetable dimensions")
    if mode not in range(len(MODES)) or not 0 <= depth <= 1:
        raise ValueError("invalid spectral transform")
    from curated_wavetables import generate_row
    if depth == 0:
        return generate_row(table, frame, limit)
    bins=[0j]*N
    for h in range(1,limit+1):
        weight=harmonic_weight(table,h,frame)
        target=_target(mode,h,depth,limit,frame)
        # Clamp instead of aliasing above the available pitch-band harmonics.
        if not 1 <= target <= min(limit,N//2-1):
            continue
        phase=_phase(table,h,frame)
        # Deliberately asymmetric phase rotations to make dense spectra move.
        phase+=depth*(h*0.17+frame*0.51) if mode==2 else 0
        coefficient=0.5j*weight*complex(math.cos(phase),math.sin(phase))
        bins[target]-=coefficient
        bins[N-target]+=coefficient.conjugate()
    row=[x.real for x in _fft(bins,inverse=True)]
    peak=max(abs(x) for x in row)
    return [0.8*x/peak for x in row] if peak else row

if __name__=="__main__":
    for mode,name in enumerate(MODES):
        row=transform_row(7,2,BAND_LIMITS[0],mode,1.0)
        print(name, min(row),max(row))
