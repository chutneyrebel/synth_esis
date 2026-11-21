# Synth_esis Move hardware checkpoint: build 77f6633e

**Reported:** 2026-11-22 (user-supplied Ableton Move results)
**Tested artifact:** `77f6633ec82ac9addd94f63a35d5aa698a9c5c7f`
**Build:** https://github.com/chutneyrebel/synth_esis/actions/runs/44943304854 (CI success)
**Development branch:** `development-phase10-11`
**Main branch:** no merge authorized

## Result

**12 PASS, 0 FAIL, 2 NOT TESTED** across 14 named checks.

### 1. Animation and source tracking: 4/4 PASS
- [PASS] OSC1 Curated 8 → 9 → 16 → 0 updates source identifier and waveform.
- [PASS] OSC2 same sequence independently.
- [PASS] OSC1 held notes animate; releasing ends movement.
- [PASS] OSC2 held notes animate; releasing ends movement.

**What this validates:** The revised `src/canvas.js` snapshot/live-value routing, active source readout, and note-gated motion work on this Move installation. Earlier hardware animation failures are now resolved **for these tested scenarios**.

### 2. Spectral-page graphics: 3 PASS, 1 NOT TESTED
- [PASS] OSC1 spectral page shows waveform on regular Wavetable 30 and displays W030.
- [PASS] OSC1 Shift/Fold/Scramble sweep affects audio and graphics.
- [NOT TESTED] OSC2 spectral page waveform visibility and W030 label for Wavetable 30.
- [PASS] OSC2 spectral effects affect audio and graphics.

**Remaining question:** Verify OSC2 Spectral has the expected waveform and W030 label; the passing OSC2 effects do **not** establish that this separate check passed.

### 3. Curated redesign: 3/3 PASS
- [PASS] Curated 8–16 have distinct timbral identities with Filter Cutoff 100.
- [PASS] Curated 8–16 remain distinguishable at Cutoff 80.
- [PASS] Curated 9, 13 and 16 pass the user's C5/C6 high-register quality check.

**What this validates:** The sound-character path in `src/dsp.c` is musically acceptable in the tested comparison, unlike the previous filtered-Metallic impression. No calibrated spectrum/alias measurement was taken.

### 4. Stability/presets: 2 PASS, 1 NOT TESTED
- [PASS] Eight-voice stress with rapid spectral controls: no reported crash, stuck notes or dropout.
- [PASS] Curated patch save/reload restores selection, position and spectral parameters.
- [NOT TESTED] Regular Wavetable patch save/reload restores active bank and settings.

**Remaining question:** Save a Wavetable 30 patch after switching from Curated 8, change banks/parameters, and reload it. Ensure the active source is W030, not the stored Curated 8, and its audio, Position, Shift/Fold/Scramble values are correctly restored.

## Root-cause decision

There are **no confirmed failures in this report**, therefore do not apply speculative fixes. Previous defects involving Curated source readouts, animation, spectral control visibility, sound-identity diversity and eight-voice stability are hardware-passed within tested scope.

Two small acceptance checks remain unverified, not failed:

1. OSC2 Spectral: Wavetable 30 waveform and W030 indicator.
2. Legacy/Wavetable active-source preset recall.

Both are narrow, high-information tests and should precede any merge. No additional broad testing batch is required if both pass.

## Recommended development path

- **Immediate:** Freeze build `77f6633e` as a *provisional hardware-success baseline* (not final release or main merge).
- **Next:** Complete only the two outstanding acceptance checks.
- **If both PASS:** Establish a hardware-accepted branch checkpoint; then choose the next creative feature/performance milestone. Keep `main` unchanged until explicit authorization.
- **If OSC2 graphic FAILS:** Inspect the osc2_spectral canvas/source data routing and test the fix in a separate build.
- **If regular Wavetable preset FAILS:** Repair the `osc2_source_curated`/`osc1_source_curated` active-source serialization and preset restore path; test without changing unrelated DSP.
- **Do not:** Claim numerical CPU use or every pitch/filter configuration is validated. Do not treat a NOT TESTED as a failure or PASS.

## Reproduction for final two checks

**OSC2 spectral visual:** OSC1 Volume 0, OSC2 Volume 100. On OSC2 Spectral select regular Wavetable 30 (which should activate regular bank without erasing saved Curated selection). Check waveform visible, label `W030`, and changing Wavetable 30→31 redraws correctly. Mark PASS/FAIL.

**Regular Wavetable preset:** Choose Curated 8, change OSC1 Wavetable to 30 (Curated 8 should remain remembered, but W030 must be active). Set Position 35, Shift 45, Fold 20, Scramble 65; save preset. Change to Curated 13 and alter parameters. Reload saved preset. PASS only if W030 is active and audio/values restored, with saved Curated 8 still retained as an inactive selection. Optionally repeat with OSC2.

## Evidence and caveat

This checkpoint documents **user-reported hardware observations**; it does not pretend the assistant ran physical hardware or measured signal/CPU performance. The referenced GitHub CI run independently establishes build/test success. The original 14 responses are the evidence record.

**Merge policy:** No merge into `main` without separate explicit approval.
