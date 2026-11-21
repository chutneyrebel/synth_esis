# Synth_esis Phase 12A/B: Expressive Spectral Motion

**Development branch:** `development-phase12-spectral-motion`  
**Starting point:** hardware-accepted commit `77f6633ec82ac9addd94f63a35d5aa698a9c5c7f`  
**Merge:** explicitly prohibited until separately approved  
**Scope:** new spectral modulation destinations using existing LFOs, controls and spectral tables; no new synthesizer pages

## The problem

The hardware-accepted Phase 10/11 engine has six effective spectral sound controls (Shift, Fold and Scramble on OSC1 and OSC2), but they only change by turning encoders. The global modulation matrix contains 12 destinations for WT position/filter/warp/pan/volume/tune, none of which address these six axes. This prevents an independent moving spectral timbre while holding a note.

## Why these fixes were chosen

1. **Preserve the known-good sound engine.** Keep the existing audio rendering, curated bank, 0–107 Wavetables, precomputed spectral corners and oscillator pages. New modulation offsets are neutral by default.
2. **Append matrix destinations.** IDs 0–11 must remain unchanged because existing patches save numeric destination identifiers and 24 matrix depths.
3. **Reuse musical timing already present.** LFO1 and LFO2 offer Free, 1/4, 1/8, 1/16, 1/4T and 1/8T sync as well as Sine, Tri, Saw, Square, S&H and Smooth waveforms; the proposed sounds do not need a third oscillator, FFT, scheduler or independent automation clock.
4. **Keep DSP real time.** The new computation consists of two additional matrix channels with six bounded depth targets and one-pole smoothing before oscillator voices render. No allocations or new table builds in the audio callback.
5. **Match graphics to what is heard.** The read-only `face_snapshot` appends six *effective* spectral depths after its historical 41 fields. Both OSC canvas renderers and S/F/X indicators consume the effective values instead of assuming the base encoder positions equal the moving sound.

## Implementation notes

### 12A — Matrix and audio modulation

**Affected files:** `src/dsp.c`, `src/module.json`, `src/ui_metadata.h`

**New destinations (append-only):**

| ID | Display label | Target |
|---:|---|---|
| 12 | O1 Shift | OSC1 spectral Shift |
| 13 | O1 Fold | OSC1 spectral Fold |
| 14 | O1 Scram | OSC1 spectral Scramble |
| 15 | O2 Shift | OSC2 spectral Shift |
| 16 | O2 Fold | OSC2 spectral Fold |
| 17 | O2 Scram | OSC2 spectral Scramble |

Each destination can receive LFO1 or LFO2. `matrix_depth=50` is neutral; 0 and 100 apply opposing polarity. Effective signal is `clamp(base/100 + 0.5*(LFO1_bipolar_depth*LFO1 + LFO2_bipolar_depth*LFO2), 0, 1)`, passed through a 0.004 per-sample one-pole smoother. Both oscillator voices read the independent effective depth for that sample.

**Preset compatibility:** State generation stores `mx0_0..mx0_17` and `mx1_0..mx1_17`. When a Phase 10/11 state lacks destination IDs 12–17, loading it explicitly resets those six targets on both LFO sources to 50; old slots 0–11 retain their historical semantics. Full state serialization must fit the existing 2,048-byte parser limit.

**Metadata budget:** Native Schwung metadata is limited to 8,192 bytes. The redundant explicit default canvas script and three enum-default hints were omitted; the DSP still initializes their values with the same defaults and the host convention uses `canvas.js` when omitted. The compact descriptor must be checked by CI.

### 12B — Musical motion and waveform graphics

**Affected files:** `src/dsp.c`, `src/canvas.js`, host graphic tests

Existing `lfo1_waveform`, `lfo2_waveform`, `lfo1_sync`, `lfo2_sync` and `sync_bpm` control musical cyclic / stepped / smoothed movement. No new mode selector is introduced. The six visual snapshot fields `effective_osc1_spectral_{shift,fold,scramble}` and `effective_osc2_spectral_{shift,fold,scramble}` reflect the audio-side smoothed depths (0–100), while original saved encoder positions remain unchanged. Legacy 26/29/35/41-field snapshots are accepted by the canvas for compatibility.

**Important:** These are still parameter-derived illustrated waveforms, not FFT oscilloscope capture. OSC page frames must receive updated snapshots at host redraw cadence.

## CI requirements

- Existing 77f6633e DSP/audio regression suite remains green.
- Old matrix destinations have unchanged numeric IDs and labels.
- New modulation routing changes the appropriate oscillator audio and leaves unrelated muted oscillators silent.
- LFO1/LFO2 can independently address each spectral destination; both bipolar sides work.
- `matrix_depth=50` and old presets reproduce the baseline sound path.
- New-state full roundtrip including all 36 matrix depths works; old-state partial restore resets new destinations to neutral.
- Both OSC canvas previews track effective values, not only base knobs.
- Eight-voice notes, large spectral sweeps and notes across registers remain bounded.
- ARM64 module archive generated and its payload verified.
- No `main` merge.

## When a Move hardware test becomes useful

**One focused hardware test is appropriate after the combined 12A+12B build is green.** It is not necessary after every test or commit. Use these acceptance checks:

1. Set Curated OSC1 8 or regular Wavetable 30. Set Shift=50, Fold=0, Scramble=0. Assign matrix LFO1 → O1 Shift with depth=100 and an easily audible LFO rate. Hold a note. The timbre should move with no encoder movement; the oscillator face should reflect it.
2. Set depth=50 (neutral): motion stops without changing the manual Shift=50 sound.
3. Set depth=0 (negative): the movement's polarity reverses relative to 100.
4. Repeat on OSC2 with OSC1 volume=0 using O2 Fold or O2 Scram.
5. Select LFO2 as source, use S&H then Smooth and synced 1/4 or 1/8. Expect stepped vs continuous motion. Depth 50 remains neutral.
6. Reload a pre-Phase12 curated patch and a regular Wavetable patch; verify no unexpected spectral motion and saved parameters/active source remain correct.
7. Play eight voices and rapidly change spectral modulation destinations. Listen for clicks, dropouts, stuck notes or high-note artifacts.
8. Confirm spectral-page Wnnn/Cnn source readouts and S/F/X meters still update when automated; navigation has not gained redundant pages.

**Go/no-go:** If any route is inaudible, no visual motion is seen, or preset recall changes old sounds, stop adding features and isolate the exact failing route. Otherwise archive the tested Phase12 build as the next known-good checkpoint. Further velocity-based spectral response is a separate 12C design decision, not bundled into this acceptance candidate.

## Outstanding risks

- CPU load from existing trilinear spectral lookups may be more significant than the six added modulation calculations; host CI does not quantify Move CPU/RAM use.
- Host redraw rate can make slow spectral changes visually discrete even when audio modulation is smooth.
- Modulating multiple effects at 100% may create strong amplitudes or timbres; assess headroom and fast-envelope behavior on Move.
- Not every original preset or host version is fully covered by regression tests.
- This branch is **experimental**. Only `77f6633e` remains the accepted baseline until a new Move hardware report closes Phase12.
