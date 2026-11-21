# Synth_esis: Phase 10–11 hardware acceptance and Phase 12 recommendation

**Hardware-tested baseline:** `77f6633ec82ac9addd94f63a35d5aa698a9c5c7f`
**Build:** https://github.com/chutneyrebel/synth_esis/actions/runs/44943304854
**Development branch:** `development-phase10-11`
**Acceptance reported:** 2026-11-22
**Status:** **14 PASS / 0 FAIL / 0 NOT TESTED**, user-reported Ableton Move hardware testing
**Merge policy:** `main` unchanged; no merge without explicit approval

## Acceptance closure

The first hardware report for this build recorded 12 PASS, 0 FAIL and 2 NOT TESTED. The user later completed both remaining acceptance gates:

1. **OSC2 spectral waveform: PASS.** The OSC2 Spectral page's Wavetable 30 waveform/source display test is now accepted.
2. **Regular Wavetable preset recall: PASS.** Active legacy source and saved parameters were restored correctly.

No additional observations were reported. The original 12 passing items remain the hardware evidence for OSC1/OSC2 Curated graphics and note-gated motion, both spectral effect visual/audio response paths, distinguishable Curated 8–16 sound design at cutoff 100 and 80, C5/C6 quality checks, eight-voice stability and Curated preset recall.

**Disposition:** Mark commit `77f6633e` a *hardware-accepted known-good baseline*. This is the tested source/build SHA. Later documentation commits on the branch do not change that baseline. Do not treat all future branch-tip changes or artifacts as hardware-accepted automatically.

## What, how and why previous failures are now closed

| Prior failure | Implementation that addressed it | Hardware acceptance |
| --- | --- | --- |
| Curated values failed to update oscillator graphics | Source-aware live/snapshot priority and explicit Cnn/Wnnn source display in `src/canvas.js` | Both OSC faces PASS |
| Note-gated graphics froze | Voice-activity merge and bounded visual phase movement in `src/canvas.js` | Both oscillators PASS |
| Spectral pages lacked waveform | Reused `face_osc1` / `face_osc2` canvases in `src/module.json` and `src/ui_metadata.h` | OSC1 and OSC2 PASS |
| Spectral changes inaudible/invisible on legacy bank | Unified spectral lookup and graphical response for original 0–107 wavetables | Audio and visuals PASS |
| Curated 8–16 sounded like filtered variations | Distinct curated harmonic designs plus per-oscillator bounded temporal character modulation in `src/dsp.c` | Musical distinctness at cutoff 100/80 PASS |
| Source-mode or patch-state regressions | Explicit stored source flags and corrected preset restores | Curated and legacy preset recall PASS |

The user confirmed zero failures. Do not introduce speculative bug fixes to the accepted baseline.

## Important limits

- Hardware evidence is user-reported; the assistant did not directly operate the Move.
- No quantitative CPU/RAM measurements or calibrated alias analysis have been collected.
- A PASS on the targeted test does not validate every possible patch, pitch, modulation, or host version.
- The oscillator graphics are parameter-derived illustrations, not live spectral FFT readouts.

## Proposed next phase: Phase 12, Expressive Spectral Motion

### Goal

Move from manually swept static spectral transformations to musical long-form timbral evolution, using the current working sound engine and page layout.

### Recommended priority order

**12A — Modulation destination plumbing (first):** Extend the existing modulation matrix with destinations for OSC1/OSC2 spectral Shift, Fold and Scramble; map the modulated depth through a bounded, smooth control path per oscillator. Keep direct encoder value as base and preserve existing presets. Confirm destination enumeration remains compatible with saved matrix settings and Schwung page metadata.

**12B — Musical motion:** Use the existing LFO sync/rate/waveform infrastructure to offer predictable slow motion, synchronized cyclic or stepped timbral changes. Prefer reusing controls before adding a new page or independent scheduler. Validate no per-sample allocations, FFT, locks or expensive reconstruction.

**12C — Expressivity:** Consider velocity-sensitive spectral depth and key-following/band-aware intensity only after 12A and 12B pass host audio tests; expose an enable/amount setting and preserve neutral legacy behavior.

### Architecture guardrails

- Develop on a new Phase 12 branch **from the immutable tested SHA `77f6633e`**, not by assuming the latest documentation-only branch tip is audio accepted. `development-phase10-11` can remain the historical checkpoint.
- No merge into `main`.
- Keep the existing curated/legacy bank selection, source flags, preset serialization, OSC faces and spectral pages unchanged unless a test-driven need is established.
- Reuse existing spectral precomputed corners and smooth modulation depths. No FFT or table generation in the real-time path.
- Preserve exact zero-modulation output where possible, enforce pitch-band and amplitude limits, and avoid knob/timing regressions.
- Test per-oscillator isolation, eight-voice stress, rapid modulation sweeps, preset migration, preset export, output stability, graphics/snapshot correctness and ARM64 packaging.
- Run development builds and CI freely in batches; request a **focused hardware test** after 12A + 12B produce audible musical evolution. Hardware tests for every minor commit are unnecessary.
- If new destinations require changing matrix enum orders, append without renumbering existing destinations, and add compatibility tests.

### Proposed test gate after implementation

1. Both oscillator spectral destinations react to LFO1/LFO2 without turning an encoder.
2. The programmed effect amount returns to dry at 0 and never changes an unrelated oscillator.
3. Sync values and ramp/step behavior feel musical at slow tempo.
4. Both spectral-page graphics track the *effective* modulated sound rather than only the base encoder value, or explicitly disclose if the graphic is an approximation.
5. Existing 77f6633e presets load correctly and preserve both source selections.
6. Eight-voice notes/sustain and encoder sweeps remain stable; no obvious high-note aliasing, pops or CPU distress.

### Alternatives to select before coding

**A — Phase 12A + 12B (recommended):** Modulation integration and musical evolving motion, scoped to existing pages, followed by one hardware validation gate.

**B — Pure DSP character design:** Expand synthesis models for more dramatic sounds, without reworking modulation. Greater sonic ambition, higher DSP and patch-compatibility risk.

**C — Performance/diagnostics:** Measure and reduce CPU, memory and update latency first; best if hardware resources are a concern, but less immediate creative benefit.

**D — Consolidation only:** Freeze the accepted baseline, clean documentation and prioritize packaging/preset library without new synthesis changes.

No Phase 12 option has been selected by the user. Do not interpret this recommendation as authorization to merge or to implement a specific new phase.
