# Synth_esis 77f6633e: engineering change report and Move acceptance plan

**Branch:** `development-phase10-11`  
**Build SHA:** `77f6633ec82ac9addd94f63a35d5aa698a9c5c7f`  
**GitHub Actions:** https://github.com/chutneyrebel/synth_esis/actions/runs/44943304854  
**CI conclusion:** success  
**Status:** implementation and CI validated; **not hardware-accepted**, **not merged to main**

## Why this iteration exists

Move hardware testing of build `87de9b3d` confirmed that the module loaded, the page layout was usable, both oscillators and all six spectral audio controls worked, curated Position worked, eight voices were stable, and live encoder sweeps did not click. The same test showed **ten failed face-visual checks** (curated changes, note-gated motion and spectral effect graphics across two oscillator faces) and **five failed sound-diversity checks** (curated 8–16 sounded similar, including at cutoff 80). The user also requested the waveform on **OSC1 Spectral** and **OSC2 Spectral** while using legacy Wavetables. Preset recall was not tested.

Passing audio controls should be preserved. CI success is not evidence of improved musical distinctiveness on Move.

## Change-to-root-cause mapping

### P1: Curated waveform selection did not redraw reliably

**Symptom:** OSC1/OSC2 faces did not track Curated 1–16 or Curated 8 → 9 → 0.

**Cause found:** Canvas depended on `face_snapshot`, which is read separately from the encoder's live value. Some extra-key reads can arrive later than the currently touched encoder. Earlier selection code could use a stale value, especially when switching to/from spectral pages. Graphical tables were also an approximation rather than the physical audio signal.

**Changed:** `src/canvas.js` merges snapshot and live values, retaining snapshot fields for comparison. Its active-source selection distinguishes a knob currently present on the page from a slower off-page extra-key read. The displayed `Cnn` or `Wnnn` identifier reveals which source the preview believes is active.

**Verification:** JavaScript tests simulate conflicting snapshots, live curated encoder values, zero selection and off-page stale values. CI passes. **Device outcome still unknown.**

### P1: No visible note-gated motion

**Symptom:** The waveform stayed static while notes were held; no visible transition after release.

**Cause found:** A visual motion path depended on selected depth/oscillator and the activity data could arrive out of order; the previous implementation did not give all sources visible note-gated phase movement.

**Changed:** `src/canvas.js` adds a bounded visual phase drift during active voices, including regular Wavetables. When direct `voice_activity` and the snapshot disagree, the face uses the active count from either source. Both reads reaching zero end the animated state.

**Verification:** Tests assert a change between rendering timestamps with active notes and no change while idle. **Limitation:** this is a *parameter-derived illustration*, not a true audio oscilloscope. Host redraw cadence remains a hardware dependency. A stale active count can make the graphic stop slightly late.

### P1: No waveform on OSC1/OSC2 spectral pages

**Symptom:** The waveform was visible on OSC1/OSC2 but absent when adjusting Shift, Fold, Scramble or regular Wavetable on the spectral pages.

**Cause found:** The spectral hierarchy entries had no canvas page.

**Changed:** Both `osc1_spectral` and `osc2_spectral` now reference the existing `face_osc1` and `face_osc2` overlays in `src/module.json` and `src/ui_metadata.h`. They keep their own four encoder bindings (Shift, Fold, Scramble, Wavetable). Display now includes source ID and, when recognized as a spectral page, S/F/X depth meters. `scripts/generate_metadata.py` accepts Schwung's default `canvas.js` script when omitted, needed to stay under the host's 8,192-byte metadata limit.

**Verification:** The real descriptor is passed through a Schwung page-planner smoke test, checking canvas presence and mapping on both pages. A hardware page-by-page visual test remains essential. If the host exposes both its standard knob grid and a separate canvas page, **do not modify Schwung host without first measuring behavior**.

### P1: Spectral controls did not visually affect regular Wavetables

**Symptom:** User could hear effects on standard Wavetable 30 but not see them on the oscillator trace.

**Cause found:** The prior preview applied modeled spectral operators only for IDs 108–123, rather than to standard 0–107 sources.

**Changed:** A lightweight, explicitly illustrative harmonic model now applies visible Shift, Fold and Scramble to regular and curated sources. Its curves are *not a measured FFT*; audio still comes from precomputed spectral tables.

**Verification:** JS tests compare 0% versus 100% changes to each of the three effects for both oscillator overlays, and verify held-note redraws.

### P2: Curated 9–16 did not have unique enough sonic behavior

**Symptom:** Glass, Vocal, Organic, Resonant, Bell Partials, Spectral Sweep, Fractal and Noise-like sounded like filtered Metallic.

**Cause found:** Moving harmonic weight curves by themselves provided insufficient differentiated time-domain/physical character. Similar resonant curves can converge under low-pass filtering. The prior numeric CI comparisons did not test a musician's perceived timbre.

**Changed:** `src/dsp.c` adds per-voice/per-oscillator **curated character phase** and a temporal color path for IDs 9–16, including noninteger modulation ratios, different phase offsets and bounded gain evolution. The character path does not activate for regular Wavetables 0–107 or curated 1–8. Upper-note bands taper the phase effects to reduce aliasing risk. No FFT, heap allocation or threading was added to the sample callback.

**Verification:** Host DSP regression tests check distinctions from Metallic, muted-oscillator isolation and eight-voice sustained notes. CI also provides **18 WAV files** rendered with the real DSP at C3/C4 with identical control settings; these are an A/B listening reference, not proof that the sound is musically satisfactory.

**Limitation:** Modulation of a single-cycle carrier is not the same as a full inharmonic/modal/noise synthesis engine. Audible sound diversity and high-register aliasing must be evaluated on Move. No claim of a measured hardware CPU budget.

## What has NOT been fixed or proven

- The user's **hardware** animation failures are not yet confirmed fixed.
- Curated 8–16 distinctness under different pitches and filters is a **listening hypothesis**, not accepted.
- Preset saving/loading, especially active-source memory, remains **not tested on hardware**.
- Actual Move CPU/memory overhead, redraw rate, and possible high-note aliasing remain unmeasured.
- The graphic is an **illustration** with DSP-derived controls, not real-time audio capture.
- Old page navigation/real encoder assignments and existing spectral audio effects must remain regression requirements.
- Nothing has been merged to `main`.

## Artifact installation

1. Open https://github.com/chutneyrebel/synth_esis/actions/runs/44943304854 (GitHub login may be required).
2. Download artifact `synth_esis-targz-download`, unzip GitHub's artifact wrapper, and locate `synth_esis-module.tar.gz`.
3. Keep a copy of the previously working `87de9b3d` module to roll back.
4. Install through your already functioning Schwung module installation procedure. Do **not** flash or update the Schwung host just to test this module.
5. Start with volume down. If it crashes or causes sustained glitches, roll back.
6. Download `synth_esis-curated-audio-AB` only when comparing the sound-design variants offline. The clips aren't a separate module.

## Short hardware acceptance gate: ~10–15 focused minutes, then decide

Use the checklist rather than retesting every passing feature.

| # | Action | PASS criterion | Failure severity |
| --- | --- | --- | --- |
| 1 | On OSC1, Curated 8 → 9 → 16 → 0 | C source readout and oscillator waveform change immediately; switching to 0 indicates legacy | Blocker |
| 2 | Repeat on OSC2 | Same behavior independent of OSC1 | Blocker |
| 3 | Hold C3 or C4 with OSC1 then release | Waveform visibly moves while held and stops after release; slight display lag acceptable | High |
| 4 | Repeat held/released note on OSC2 | Independent behavior | High |
| 5 | On OSC1 Spectral choose Wavetable 30; sweep S/F/X individually | Waveform visible, source label is W030, controls affect sound *and* graphic | Blocker |
| 6 | Repeat on OSC2 Spectral | As above | Blocker |
| 7 | Curated 8 vs 9–16, spectral 0, Cutoff 100 then 80 | Distinct **musical identities**, not merely filtered/brightened versions | High, subjective |
| 8 | Hold eight notes, sweep spectral knobs, release | No crash, sustained clicks, stuck notes or abnormal lag | Blocker |
| 9 | Save/reload one curated sound then one legacy Wavetable sound | Sound, active source, position and spectral values restored | High |
| 10 | Play C5/C6 with upper curated modes 9, 13, 16 | No obviously excessive aliasing or level jumps | High |

**Test isolation:** set Resonance 0, Drive 0, Shift/Fold/Scramble 0 initially, and one oscillator volume to 0 while testing the other. Set Cutoff 100 for first round. Do not confuse a moving *graphic* with measured audio spectral data.

Report PASS/FAIL/SKIP and a sentence on each failure. For sound similarity, describe which pairs sound alike and under what notes/cutoff.

## Development options

**A: Hardware gate now (recommended).** Install this green, isolated development module; check only the ten items above. This is a high-information test because the remaining problems depend on actual Schwung redraw behavior and musical perception. Fix failed gates in a new development commit batch.

**B: Offline sound-design study before installing.** Listen to the 18 real-DSP WAV previews, compare C3/C4 and identify which curated identities overlap. Tweak synthesis after those findings. Hardware graphics would remain unverified.

**C: Continue automation-only DSP/UI development.** Build more host-side tests/visual capture and optimize memory/performance, without a Move test. This is possible, but CI cannot confirm actual display animation or user-perceived sound; risks repeating the failure loop.

**D: Split graphics and sound-design branches.** Freeze a graphics-only candidate and an audio-only candidate, hardware-test each independently, then combine after both pass. This is slower to install but better for pinpointing regressions.

### Decision rule

Choose **A** unless installation is inconvenient. Do not merge to `main` until at least visual gates 1–6, stability gate 8 and preset gate 9 pass, and the sound direction in gate 7 is accepted (or explicitly deferred by the user). A failure on A1/A2/A5/A6 should prioritize canvas/host data flow before any more sound-design changes.
