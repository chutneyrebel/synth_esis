# Synth_esis Phase 10C: first compositional spectral hardware check

**Target:** Ableton Move running a compatible Schwung host, module built from
`development-phase10-11` after the green ARM64/package CI run.

This is a manual sign-off, **not** a claim that GitHub CI proves hardware audio.

## Before installing
- Keep a copy of your currently working Synth_esis module to roll back.
- Download the successful run's `synth_esis-targz-download` artifact.
  GitHub wraps the actual `synth_esis-module.tar.gz` in a ZIP. Extract once.
- Check the artifact's commit against the target branch before installing.
- Use your existing working Schwung installation procedure.
- Test with the Move volume low initially; some compound spectra are brighter.
- Leave the current `main` branch unchanged.

## Audible tests
1. **Bypass identity:** choose a curated OSC1 wavetable such as Metallic
   (curated ID 8), leave OSC1 Shift/Fold/Scramble at 0, and play a long note.
   The dry baseline should remain stable and retain the previous pitch.
2. **Shift alone:** OSC1 spectral page, sweep Shift 0 → 100 → 0.
   Expect the upper harmonic emphasis to move without changing the played note.
3. **Fold alone:** reset Shift, then sweep Fold. Listen for changes to the
   harmonic envelope, with stable bass/fundamental.
4. **Scramble alone:** reset Fold, then sweep Scramble. Look for a distinct,
   non-random-on-repeated-playback timbre and no level explosion.
5. **Compound:** set all three to 50, then to 100. Compare against each
   single-operator setting. Their interaction should sound distinct from
   simply stacking the old precomputed effect blend.
6. **OSC isolation:** mute OSC2; change OSC2 spectral values and wavetable.
   OSC1 must not change. Reverse with OSC1 muted and OSC2 active.
7. **Live encoder sweeps:** hold notes while moving each spectral encoder
   quickly, including 0 ↔ 100 jumps. Listen for zipper noise, clicks,
   unexpected silence, or stuck notes.
8. **Pitch/bandlimit:** play C2, C4, C6 and the highest usable notes with
   both oscillators, first with Scramble only and then full compound. Note
   harsh aliasing or unexpectedly silent high notes.
9. **Polyphony:** hold eight notes, change spectral parameters rapidly,
   switch between oscillator pages, and release. Confirm stable tails and
   no dropouts or stuck voices.
10. **Presets:** save a new spectral patch, recall it, then load an older
    preset without spectral keys. Older presets should restore six spectral
    settings to 0 rather than inheriting them.
11. **Multiple instances:** if your Schwung setup supports it, compare
    one versus two Synth_esis instances and watch Schwung's CPU diagnostics
    (if available) for increased load.
12. **Soak:** play/sweep for 10–15 minutes; note changes in stability,
    temperature warnings, or responsiveness.

## What to report back
- Overall: PASS / FAIL.
- OSC1 Shift, Fold, Scramble: each audible? Y/N.
- OSC2 Shift, Fold, Scramble: each audible? Y/N.
- All-three-compound sound different from singles? Y/N.
- Clicks or zipper noise during changes? Y/N.
- High-register aliasing / dropouts? Y/N.
- Eight-voice stress stable? Y/N.
- Preset and page navigation correct? Y/N.
- CPU diagnostics (if available): idle, 1 voice, 8 voices, two instances.
- Notes or a short recording illustrating any problem.

If the module causes instability, revert to your retained known-good module;
do not repeatedly load the experimental version until the failure is diagnosed.

## Engineering boundaries
- Offline 2x2x2 spectral corners approximate continuous operator depths via
  trilinear interpolation. True mathematical composition is guaranteed at
  the seven full-depth vertices, **not** at every intermediate depth.
- A single-cycle wavetable produces harmonic partials; no true inharmonic
  frequencies are claimed.
- CI's host benchmark is not a device-level performance measurement.
