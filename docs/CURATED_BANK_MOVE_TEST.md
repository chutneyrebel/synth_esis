# Synth_esis curated bank: Move hardware test

**Test only the CI artifact built from the latest passing development commit.** This is a development module, not a release. Back up saved sets/presets before installing. Do not merge to main.

## Installation prerequisites

- Schwung host version known to support Synth_esis's canvas pages and the existing host canvas-only patch.
- Download `synth_esis-targz-download` from the successful GitHub Actions run; GitHub wraps the `.tar.gz` in a ZIP. Extract the ZIP first.
- Use the same known-good Schwung module installation/rollback procedure already used for Synth_esis. Never overwrite a running `dsp.so` in place.
- Do not install if any build/package/host compatibility step failed.

## Expected controls

- OSC1 FACE encoder 1: `curated_osc1`, 0 = old table, 1..16 = curated Sine through Noise-like.
- OSC2 FACE encoder 1: `curated_osc2`, same mapping, independent of OSC1.
- Existing `wavetable` and `osc2_wavetable` parameters remain in the parameter API and page params; old IDs 0..107 unchanged.
- Both selectors default to 0, so legacy sounds must be unchanged.
- OSC1 and OSC2 position still scan four frames; their octave, warp, detune, pan and volume controls remain.

## Hardware checklist

1. Load existing known-good preset; confirm same sound with both curated selectors at 0.
2. Set OSC1 volume 100, OSC2 volume 0. Sweep OSC1 curated 1..16 and position 0..100. Check each sounds distinct and no silence/clicks.
3. Set OSC1 volume 0, OSC2 volume 100. Sweep OSC2 curated 1..16 and its position independently.
4. Mix both oscillators; test pan, detune, octave, warp and both independent envelopes.
5. Hold chords and rapidly retrigger; check voice stealing, no stuck notes, clipping or glitches.
6. Save a patch with both curated selectors nonzero, change patches, reload and restart; confirm both selections persist.
7. Run four Move slots with typical drums/bass/synth usage; listen for dropouts and monitor performance if available.
8. Restore selectors to 0 and confirm the original wavetable controls still select old sounds through their parameter entries.

## Report back

- PASS/FAIL for OSC1, OSC2, position morph, envelopes, preset save/restore and four-slot CPU.
- Any clipping, clicks, UI mislabeling, page navigation regressions or silence.
- Exact GitHub Actions run and installed commit.

Known limitation: this checkpoint does **not** implement oscillator interaction, macros, unison, effects or on-device harmonic editing. Those remain gated by Schwung hardware/API and performance validation.
