# Synth_esis Phase 10 + 11 integration roadmap

Branch: `development-phase10-11`; draft PR #33. Never merge without explicit approval.

## Product decision: quality-first 16 + early custom wavetables

- **16 curated primary tables** for new patches. The curated list is a design target, not a claim that the audio engine already exposes them.
- **Preserve IDs 0–107** and existing presets during migration; do not delete the legacy banks until explicit migration testing and approval.
- **Bring custom wavetable format and offline import/export into Phase 10B**, before the full web editor. Start with a deterministic, validated, versioned JSON interchange format; Move runtime loading comes only after security, size and host compatibility checks.
- Keep new shaping neutral/bypassed for existing presets. Never reuse existing parameter IDs or alter the current page layout silently.
- Keep Move audio thread allocation-free, bounded and without FFT work. No third-party GPL code copied.

## Phase 10

| Stage | Work | Acceptance |
| --- | --- | --- |
| 10A | Unified wavetable lookup | CI and Move hardware PASS |
| 10B-1 | Offline harmonic tilt/filtering, FFT, band-limited shape prototypes | CI PASS |
| **10B-2** | **16-table curated bank plan + versioned custom interchange, validated import/export** | Schema roundtrip, invalid data and size tests |
| 10B-3 | Actual curated source waveforms, quality review, aliasing/level and footprint benchmarks | Audio/size tests; explicit table selection approval |
| 10B-4 | Neutral-by-default per-oscillator spectral shaping in live DSP | Legacy preset audio comparison, ARM64/CPU checks |
| 10C | DSP-derived waveform and spectral visuals | Canvas and hardware test |
| 10D | Harmonic shift/fold and phase transforms | Aliasing and headroom checks |
| 10E | Two OSC SHAPE hardware pages and matrix integration | Encoder, navigation, preset regression |
| 10F | Move-safe custom wavetable loader and editor integration | Invalid input, memory and offline/online testing |

## Phase 11

| Stage | Work | Acceptance |
| --- | --- | --- |
| 11A | Custom wavetable workflow refinement and preset migration | Version compatibility and migration |
| 11B | Schwung web harmonic/draw editor and preview | Host and UI validation |
| 11C | User bank management, transfer, import/export and standalone playback | Roundtrip and hardware tests |
| 11D | Eight-voice stress, stability, rollback, CPU and memory optimization | Sustained hardware testing |
| 11E | Single consolidated Phase 10+11 release candidate | CI + Move validation + explicit merge approval |

## 16 proposed timbral slots (subject to listening review)

Sine, Saw, Square, Triangle, Odd, Formant, Hollow, Metallic,
Glass, Vocal, Organic, Resonant, Inharmonic, Spectral Sweep, Fractal, Noise-like.

These are **target identities**, not newly implemented DSP assets. Curated tables should use the existing 4-frame / 9-band / 256-sample representation unless testing justifies a change.

## Current checkpoint

10B-2: introduce standalone interchange schema and tests; no audio engine change, no hardware installation required. Subsequent changes stay on this branch and draft PR #33. Never merge automatically.
