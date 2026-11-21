# Synth_esis Phase 12D: Spectral Articulation (experimental)

**Branch:** `development-phase12d-spectral-articulation`
**Parent:** Phase 12C `9944edc6c522fd0d17de88a0c67a2f787259d29e`
**Target:** isolated DSP prototype, NOT approved for installation until CI and compatibility checks pass.
**Merge rule:** No merges to `main` or Phase 12C without explicit approval.

## Goal and design decisions

Existing Phase 12A/B adds continuous global spectral LFO motion. Phase 12C
adds note-velocity-responsive spectral Shift. Phase 12D adds *voice-local
time evolution* for Fold and Scramble so that different notes in a chord
have their own spectral attack/decay contours.

This first implementation deliberately reuses the 12C `vel_spec` knob to
avoid exceeding Schwung's near-full metadata budget, changing old preset
semantics, or adding another settings page. No new saved parameter or
modulation matrix destination is introduced. Fixed envelope timing is
temporary; adjustable timing belongs in a separate design decision.

## What / How / Why

| What | How | Why |
|---|---|---|
| Per-voice spectral contour | Add `spectral_artic` and `spectral_artic_stage` to `Voice`; reset them at MIDI note-on and on voice stealing | Every key gets its own articulation life cycle instead of sharing a global timer |
| Fast attack | 12 ms linear ramp from 0 to 1; evaluated inside render for each active voice | Avoid abrupt spectral jumps at note-on while still allowing a transient |
| Smooth decay | Approximate 420 ms exponential falloff after peak, truncated below 0.0001 | Makes spectral color gradually return to the held-note tone |
| Velocity Fold | `clamp(global_fold + vel_delta * contour,0,1)` | Harder notes have a different transient fold intensity |
| Velocity Scramble | `clamp(global_scramble + 0.65 * vel_delta * contour,0,1)` | Adds a related but less aggressive timbral articulation |
| Phase 12C Shift preserved | Continue applying preexisting per-voice `shift1/shift2` without envelope | No change to Phase12C Shift response |
| Opt-in backwards compatibility | If `vel_spec=0`, `vel_delta=0` and Fold/Scramble are exactly the pre-12D effective values | All Phase12A/B states remain audibly neutral |
| Older metadata regression | Curated integration test now uses `.get("default",0)` and asserts DSP zero-initialization | Phase 12C intentionally omitted optional zero-default metadata to fit the 8192-byte host limit; this avoids a false test failure without changing code or old preset IDs |
| CI trigger | Add branch pattern `development-phase12d-*` | Run DSP, ABI, compatibility and ARM64 pipeline for this isolated branch |

## DSP architecture

At each MIDI note-on:
- Zero and initialize new voice's articulation state.
- Latched MIDI velocity `v->vel` remains in `[0,1]`.

At each output sample per active voice:
1. Compute existing velocity delta `((127*velocity_normalized-64)/63)*0.35*(vel_spec/100)`.
2. Keep Phase12C `shift1/shift2` exactly as before.
3. Raise spectral articulation from 0 to 1 over ~12ms.
4. Decay it multiplicatively by `(1-1/(0.42*44100))` each sample to almost zero (~420ms time constant).
5. Use `fold_delta=vel_delta*articulation`, `scramble_delta=0.65*fold_delta`.
6. Add these offsets to the effective Phase12A/B smoothed Fold/Scramble for *both* oscillators, separately for each voice, and clamp to [0,1].
7. Feed the effective six voice-specific depths to the existing bandlimited spectral lookup/trilinear morph; no new FFT, table rebuild, allocation or clock.

No new control page, API change, saved parameter, matrix index, wavetable ID,
preset format, voice count or host dependency. CPU cost grows by lightweight
per-voice arithmetic only, but actual Move cost is unmeasured.

## Preset compatibility

- New articulation state is ephemeral `Voice` data and **never serialized**.
- The only user control remains Phase12C's existing `vel_spec`, default 0.
- Older states without `vel_spec` continue to clear the control to 0.
- New `vel_spec` states roundtrip unchanged.
- Phase12A/B matrix IDs 0-17 remain untouched; existing spectral graph
  continues to display global effective values, not every active note.
- The strict 8192-byte module descriptor is unchanged by Phase12D.
- Root/OSC encoder page order remains unchanged.

## CI and acceptance

The first Phase12D candidate must clear all workflow steps, especially:

1. `python3 tests/test_plugin.py` (Schwung ABI, host DSP build, parameter contract).
2. `python3 -m unittest discover -s tests -p 'test_curated_integration.py'`
3. `python3 -m unittest discover -s tests -p 'test_spectral_audio_integration.py'`
4. `node tests/test_canvas.cjs`
5. `bash scripts/build.sh`, package integrity and exact ARM64 archive check.

Added Phase12D tests:
- With Shift saturated at 100, show early audible Fold/Scramble difference
  and lower late difference after the contour decays.
- Velocity 64 exact neutrality at maximum sensitivity.
- Staggered notes remain audible during polyphonic articulation.
- Existing Phase12C tests still cover opt-in Shift, old preset recall,
  12A/B matrix routes and oscillator separation.

**CI results must be reported only after reading the actual workflow run.**
A successful compile is not proof of acceptable timbre or CPU headroom.

## Hardware decision

**Not recommended yet.** Phase12A/B itself awaits Move signoff and Phase12C
Build #483 failed a metadata regression test. Finish Phase12D CI first, then
conduct one combined Phase12A/B/C/D acceptance session rather than four
separate hardware tests.

Suggested combined hardware exercise after CI is green:

1. Load an existing Phase12A/B preset: `vel_spec=0`, old sound, no new transient.
2. On OSC1, select curated 8; set Shift=100, Fold=40, Scramble=40,
   `vel_spec=100`, amp sustain long. Compare velocity ~64 to ~120.
   Expect a harmonically changing note-on that relaxes toward the held tone.
3. Set `vel_spec=0`: the per-note Fold/Scramble transient disappears.
4. Repeat OSC2 with OSC1 muted.
5. Play simultaneous soft and hard notes; then trigger another after ~300ms.
   Confirm each note keeps its own contour without restarting old notes.
6. Enable LFO1/LFO2 spectral destinations in the existing matrix and
   ensure their slower global motion continues under the note transients.
7. Test 8-note chords, rapid retriggers, release tails and scene/preset recall.
8. Confirm all canvas pages, encoder labels, wavetable IDs and voice activity.
9. Listen for clicks, clipping, unexpected level differences, stuck notes,
   CPU overload or dropouts; record PASS/FAIL/SKIP.

## Known risks / limitations

- The contour has fixed times (12ms attack and ~420ms decay time constant).
  If too short/long musically, parameterize in a future branch.
- `vel_spec` currently controls Shift and the Fold/Scramble contour together;
  independent amounts are a future option.
- Shift/Fold/Scramble clamp to 0..1, so extreme starting values can mask
  changes in one polarity.
- The native visual canvas reflects global modulation; per-note articulation
  in chords is not visualized separately.
- Host patch compatibility and true Move resource use remain unverified.
- Phase12C's implicit zero-default metadata still requires hardware-host
  acceptance despite the corrected test.

## Next choices

A. Recommended: repair any Phase12D CI failures, capture ARM64 artifact and
   prepare combined hardware acceptance for 12A/B/C/D.
B. Extend note-on articulation with independently controllable Fold and
   Scramble depths, after verifying metadata strategy.
C. Build an envelope-shaping experiment (attack/decay curvature, optional
   note-off release) on another branch after a sound-quality checkpoint.
