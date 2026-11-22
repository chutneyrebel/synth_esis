# Synth_esis Phase 12A–12G — consolidated Ableton Move acceptance

**Test subject:** GitHub Actions [Build #515](https://github.com/chutneyrebel/synth_esis/actions/runs/44952349913)
**Build commit:** `00aa639ac7a99d5a2d6a192623718ad5404a4fb9`
**Branch:** `development-phase12g-external-ui-assets`
**GitHub artifact:** `synth_esis-targz-download` (a GitHub ZIP containing `synth_esis-module.tar.gz`)
**Known hardware-approved baseline:** `77f6633ec82ac9addd94f63a35d5aa698a9c5c7f`
**Merge status:** NO MERGE TO MAIN or to any Phase 12 branch.
**CI:** Build #515 completed successfully, including desktop ABI/audio, spectral integration, preset factory export, canvas, Schwung planner/navigation, AArch64 packaging and archive validation. **Hardware acceptance is not implied.**

## Report header (fill before beginning)

- Tester:
- Test date and timezone:
- Ableton Move firmware version:
- Schwung host/version/commit (if available):
- Schwung Manager version (if available):
- Install method: Manager tarball / other:
- Installed module shown as:
- Baseline saved archive location (private; do not share personal paths):
- Tested output: headphones / interface / speakers:
- Input: Move pads / external MIDI (state which):
- Browser/device for Remote UI:
- Initial state and patches used:
- Known issues already present before the test:

**Status codes:** `PASS` = observed exactly the expected behavior; `FAIL` = observed mismatch or breakage; `SKIP` = not performed or equipment unavailable. Mark every row and record observed result. A required SKIP does *not* count as acceptance.

**Severity:** S0 = installation failure, data corruption, stuck audio/unsafe level, crash or host failure: STOP and roll back. S1 = missing/broken sound, preset regression, page/control mismatch or persistent clicks/dropouts: STOP further feature acceptance; preserve evidence, roll back if needed. S2 = misleading label, minor display or browser-only regression: isolate, potentially continue sound tests if safe but DO NOT mark full acceptance. S3 = cosmetic issue or preference: record for refinement.

## 0. Preparation, verified download and rollback prerequisites

1. **Back up before overwriting:** Keep a local copy of the *currently installed working module* and important saved presets/sets. The Git commit `77f6633e` is the last recorded hardware-approved source baseline, but **a commit alone is not an installable backup**. Ensure you actually possess the corresponding working `.tar.gz` or a restorable copy of the existing installed module. If not, pause installation until you have a recoverable backup.
2. Open [successful Build #515](https://github.com/chutneyrebel/synth_esis/actions/runs/44952349913), download artifact **`synth_esis-targz-download`**, and unpack the outer GitHub ZIP **once**. Keep the nested **`synth_esis-module.tar.gz`** intact. Do not upload the ZIP itself.
3. Optional macOS archive inspection: `tar -tzf synth_esis-module.tar.gz`. Expect `synth_esis/module.json`, `synth_esis/dsp.so`, `synth_esis/web_ui.html`, `synth_esis/canvas.js`, `synth_esis/wavetable_catalog.json`, and `synth_esis/assets/ui_reference.js`. Reject unknown executable paths or mismatched archive.
4. Confirm Schwung is already working and note host/Manager version. No host upgrade or custom host patch is part of this exercise.
5. On your Mac, open Schwung Manager at your configured Move address; upstream default Remote UI URL is `http://move.local:7700/remote-ui`. Under **Modules**, expand custom installation, select **From Tarball**, browse to the **`.tar.gz`**, and select **Install from File**. Use the Manager's displayed success/failure result and any requested restart/reload. The host's [modules.html](https://github.com/charlesvestal/schwung/blob/main/schwung-manager/templates/modules.html) has this supported form.
6. Use an empty test set on Move; reduce monitoring volume for initial tests. Avoid unintentional loud jumps with high Fold/Scramble or resonance.

**Installation gate:**

| ID | Check and expected result | Status | Observation |
|---|---|---|---|
| I01 | Known-good archive and presets are safely backed up and restorable | ____ | ____ |
| I02 | Downloaded artifact belongs to Build #515 / commit `00aa639a`; archive payload passes inspection | ____ | ____ |
| I03 | Tarball installation succeeds via Schwung Manager and Synth_esis can be selected | ____ | ____ |
| I04 | Notes sound normally at safe volume; no crash, stuck notes or persistent silence | ____ | ____ |

**STOP if I01, I03 or I04 is FAIL.** Do not continue with musical tests until the system is recoverable.

## 1. Navigation, canvas and baseline controls (Phase 12A/B/F/G compatibility)

Root FACE is declared once using chain_params, with a compact string reference in the hierarchy. Check it *on device*; source/planner CI is insufficient.

**Expected root FACE eight encoders in order:** motion rate `lfo_rate`, motion depth `lfo_depth`, LFO filter depth `lfo_filter`, cutoff, resonance, master pan, output level, OSC2 volume. The root page can be entered before the child levels.

**Expected child order from root hierarchy:** OSC1, OSC1 spectral, OSC2, OSC2 spectral, FILTER, MOTION, MATRIX, OSC1 AMP, OSC2 AMP, OSC MIX (plus any established host-managed preset/module pages). Do not assume a new separate velocity page exists.

**Expected spectral-page seven encoders each:** oscillator Shift, Fold, Scramble, osc wavetable, `Vel Shift`, `Vel Fold`, `Vel Scram`. Two separate oscillator spectral faces must be present; the three velocity amounts are shared parameters shown on each.

| ID | Check and expected result | Status | Observation |
|---|---|---|---|
| N01 | FACE is first; no duplicate redundant MAIN; established MY PRESETS / MODULE pages remain accessible | ____ | ____ |
| N02 | Root FACE has exactly eight correct encoder mappings and changing each affects its target | ____ | ____ |
| N03 | Complete child order and navigation match the existing hardware-approved flow; no missing/inaccessible pages | ____ | ____ |
| N04 | OSC1 and OSC2 faces each show their own active spectral illustration and source readout (Wnnn / Cnn as appropriate) | ____ | ____ |
| N05 | FILTER face, MOTION, MATRIX, OSC1 AMP, OSC2 AMP and OSC MIX controls remain editable and correct | ____ | ____ |
| N06 | OSC1/OSC2 spectral pages have seven correctly ordered encoders and distinct `Vel Shift` / `Vel Fold` / `Vel Scram` labels | ____ | ____ |
| N07 | Animated spectral displays respond on the established redraw cadence when manual parameters or LFO routes change | ____ | ____ |
| N08 | Changing a control on one page retains its value when leaving and returning; no silent resetting | ____ | ____ |

Note: spectral canvas is a model-driven approximation, **not** an FFT/audio waveform reader. It shows global effective spectral depths, not individual MIDI note velocity offsets.

## 2. Oscillator independence and audio foundations

Use a single held note C3 or C4, low resonance, ordinary amp sustain, modest monitor gain, and no spectral LFO routes (matrix depth 50). Use both curated and conventional wavetable sources at least once.

| ID | Check and expected result | Status | Observation |
|---|---|---|---|
| A01 | OSC1 solo (OSC2 volume 0) makes sound and responds to OSC1 WT position, Shift, Fold, Scramble | ____ | ____ |
| A02 | OSC2 solo (OSC1 volume 0) makes sound and responds to OSC2 WT position, Shift, Fold, Scramble | ____ | ____ |
| A03 | Both oscillators active: pan, octave, detune, oscillator volume, mix balance behave as expected | ____ | ____ |
| A04 | Cutoff, resonance, filter mode, drive, envelopes and global output controls remain effective | ____ | ____ |
| A05 | Curated source 8 and a regular WT around 30 can each be selected on both oscillators; no stuck tone or unexpected silence | ____ | ____ |
| A06 | Sweep spectral amounts gently from 0 to 100, monitoring for clicks, abnormal level jumps and artifacts beyond intentional coloration | ____ | ____ |

## 3. Global spectral modulation (12A/B)

Preparation: disable velocity response (`vel_spec=vel_f=vel_s=0`); OSC1 solo; curated source 8 **or** regular WT 30; OSC1 Shift 50, Fold 0, Scramble 0. Set LFO1 waveform Sine; select **MATRIX** source LFO1, destination **O1 Shift** (numeric ID 12), depth 100. Hold C3.

- At depth **100**, expect audible cyclic timbral motion and matching global S/F/X movement where rendered.
- At depth **50**, modulation stops (neutral); manual Shift remains.
- At depth **0**, inverse-polarity motion relative to 100, subject to clipping at parameter bounds.
- Repeat O1 Fold (ID 13) and O1 Scram (ID 14), then OSC2 solo with O2 Shift/Fold/Scram (IDs 15/16/17).
- Repeat at least one route with **LFO2**, its S&H and Smooth waveforms, and clock sync 1/4 and 1/8. Avoid expecting exact BPM timing unless a supported clock/sync source is available.

| ID | Check and expected result | Status | Observation |
|---|---|---|---|
| M01 | LFO1→O1 Shift, depth 100: audible motion with static manual encoder and global graphical motion | ____ | ____ |
| M02 | Depth 50 is neutral; depth 0 reverses polarity/response relative to 100 | ____ | ____ |
| M03 | LFO1 can address O1 Fold and O1 Scram independently; unrelated muted OSC2 stays quiet | ____ | ____ |
| M04 | LFO1 can address O2 Shift/Fold/Scram with OSC2 solo; muted OSC1 stays quiet | ____ | ____ |
| M05 | LFO2 S&H yields stepped timbral changes; Smooth yields gradual movement | ____ | ____ |
| M06 | Available synced 1/4 and 1/8 modes and free timing behave sensibly without host freeze or stuck notes | ____ | ____ |
| M07 | Matrix routes 0–11 preserve their historical destinations; 12–17 are appended and visibly accessible | ____ | ____ |

## 4. Velocity response (12C), articulation (12D), isolation (12E)

**Important:** Move pad velocity is expressive but not a calibrated MIDI numeric reference. For an exact velocity-64 neutrality check, use a *verified MIDI source capable of fixed velocity* if available; otherwise mark the exact numeric subtest SKIP and compare clearly soft vs hard pad strikes. Velocity affects volume already, so compare **timbre**, not loudness alone. Use the same note and headroom-safe output.

Setup for spectral Shift: solo OSC1, curated 8, manual Shift 50, Fold 0, Scram 0, LFO spectral matrix neutral. Compare `vel_spec=0` and `vel_spec=100` at soft and firm strikes. Repeat OSC2 solo.

Setup for Fold/Scram: manual Shift 100 (to clamp Shift, isolating other axes), Fold 35–45, Scram 35–45, `vel_spec=0`, both `vel_f=vel_s=0` initially. Then test **one amount at a time**:
- `vel_f=100, vel_s=0`: listen for velocity-dependent Fold transient with ~12 ms attack and decay time constant ~420 ms.
- `vel_s=100, vel_f=0`: independently audible Scramble transient with the same timing and reduced intensity scaling.
- `vel_spec=100, vel_f=vel_s=0`: sustained Shift responds to velocity but should not add Fold/Scramble articulation.
- Trigger a soft note, hold it, and ~300 ms later trigger a hard note. New note's transient must not retrigger/erase the first note.

| ID | Check and expected result | Status | Observation |
|---|---|---|---|
| V01 | OSC1 Shift: `vel_spec=100` produces velocity-dependent timbre, disabled at 0 | ____ | ____ |
| V02 | OSC2 Shift: same with OSC1 muted | ____ | ____ |
| V03 | `vel_f=100` alone produces an attack/decay Fold transient; changing `vel_s` from 0 is not required | ____ | ____ |
| V04 | `vel_s=100` alone produces a distinct Scramble transient; changing `vel_f` from 0 is not required | ____ | ____ |
| V05 | `vel_spec=100` with `vel_f=vel_s=0` changes Shift but does not start the Fold/Scramble envelope | ____ | ____ |
| V06 | Velocity 64 mathematically neutral using calibrated MIDI input, if available | ____ | ____ |
| V07 | Staggered soft/hard held notes coexist, each with its own articulation; no voice reset | ____ | ____ |
| V08 | OSC2-only Fold/Scram articulation and simultaneous two-oscillator response behave correctly | ____ | ____ |
| V09 | With global spectral LFO modulation enabled, per-note velocity expression layers on top rather than disabling LFO movement | ____ | ____ |

## 5. Preset and backward compatibility

**Use copies of old patches**, not the only saved originals. A factory export passing CI does not prove that *your* historical patches survive.

- Before 12C: absent velocity keys must restore all velocity amounts to 0 and absent new matrix routes to depth 50.
- **12D** state with `vel_spec=75` but absent `vel_f`, `vel_s`: the new keys must inherit 75 to preserve the Phase12D combined velocity behavior.
- **12C** state with nonzero `vel_spec`: this historically affected **Shift only**. The current 12E/G migration uses the same key to inherit Fold/Scramble for any old state missing both new keys. Without a saved schema/version marker the loader cannot distinguish 12C from 12D. **This is a known potential backward-sound regression: test it explicitly and mark FAIL if the previously Shift-only timbre changes. Do not claim universal backward sound compatibility until resolved.**
- 12E/G saved state: three independent amounts must roundtrip without silently changing one another.
- Curated source IDs and regular 0–107 WT selections must not change.

| ID | Check and expected result | Status | Observation |
|---|---|---|---|
| P01 | Historical regular WT patch loads, sounds as before, and has neutral new spectral routing/velocity controls | ____ | ____ |
| P02 | Historical curated WT patch loads with correct curated source, level and envelopes | ____ | ____ |
| P03 | Phase12D patch with nonzero `vel_spec` loads and Fold/Scram inheritance matches previous combined response | ____ | ____ |
| P04 | Save Phase12E/G patch with distinct Shift/Fold/Scram velocity values (e.g. 20/70/10), change values, then recall; all three restore | ____ | ____ |
| P05 | Load an old patch after a new patch: no lingering newer velocity amounts, matrix offsets or changes to old defaults | ____ | ____ |
| P06 | Save/recall with both oscillators, curated/regular sources, independent envelopes, filter settings and matrix destinations | ____ | ____ |
| P07 | Existing user presets, MY PRESETS and module controls remain accessible; no corrupted or missing saved content | ____ | ____ |
| P08 | Phase12C Shift-only patch with nonzero `vel_spec` must retain its original Shift-only timbre; if Fold/Scram articulation appears, mark FAIL (known migration ambiguity) | ____ | ____ |

## 6. Polyphony, stress and signal quality

Monitor at a safe level. Use natural performance and repeated notes across C2–C5.

| ID | Check and expected result | Status | Observation |
|---|---|---|---|
| S01 | Eight-note chords with both oscillators and nonzero spectral LFO modulation play without persistent note loss | ____ | ____ |
| S02 | Rapid retriggers, varied velocities, octave changes and note release do not create stuck notes | ____ | ____ |
| S03 | Sweeping spectral Fold/Scram extremes does not crash, silence the instrument or produce unmanageable levels | ____ | ____ |
| S04 | Playing with global motion + velocity articulation remains responsive; no repeatable crackling/dropouts at normal output levels | ____ | ____ |
| S05 | After leaving/reopening pages and reloading test patch, no unexpected state reset or hanging voice persists | ____ | ____ |

## 7. Schwung Remote UI (Phase12F/G presentation)

Browser/device on same accessible network as Move. Open [Remote UI](http://move.local:7700/remote-ui) or the configured Move address, select the slot containing Synth_esis. In the custom synth panel, inspect the `05 / Spectral Expression` section and three sliders. The 12G panel uses `assets/ui_reference.js` for detailed help and labels.

Use the **Interface: Default** toggle to compare generated host controls with the custom panel. Test moving a slider on Remote UI then reading the parameter on Move; repeat in the other direction where the live update/refresh is supported. No control change should target another slot.

| ID | Check and expected result | Status | Observation |
|---|---|---|---|
| R01 | Remote UI opens and recognizes Synth_esis, no blank browser panel or failed asset load | ____ | ____ |
| R02 | Custom browser header says Synth_esis and section `05 / Spectral Expression` exists | ____ | ____ |
| R03 | Velocity Shift/Fold/Scramble labels and distinct descriptions load from the sidecar asset | ____ | ____ |
| R04 | All three Remote UI sliders write the correct DSP parameter in the selected synth slot | ____ | ____ |
| R05 | Other slot(s) are unchanged by the tested remote slider writes | ____ | ____ |
| R06 | Switching to Default Interface exposes normal generated controls; returning to custom panel preserves actual parameter state | ____ | ____ |
| R07 | Native Move FACE/OSC pages and audio still work while browser UI is open, closed and reloaded | ____ | ____ |
| R08 | Browser refresh/network hiccup does not crash sound engine or corrupt a saved patch | ____ | ____ |

If local hostname does not resolve, use the device's configured network address rather than making a host software change just for this test.

## 8. Abort and rollback procedure

**Immediate stop triggers:** install failure; missing/corrupted preset state; missing native FACE/control page; repeated silence or stuck notes; uncontrollable output; crash or repeatable severe dropouts. Lower output first.

1. **Record** failing test ID, expected versus observed, exact patch, parameters, Schwung host version, and any available photo/audio (avoid including personal data).
2. Stop sounding notes and leave the test set. Save only non-destructive diagnostic notes; do **not** overwrite your last working presets with experimental versions.
3. Open Schwung Manager, use **Modules → From Tarball → Install from File** to reinstall the backed-up known-good `synth_esis-module.tar.gz`, then follow the host's reload/restart prompts. Do not assume that changing a Git branch on your Mac rolls back what is installed on Move.
4. If you do not have a known-good archive, do not blindly uninstall/delete. Recover a verified previously accepted module backup first. Keep user patches backed up separately.
5. Load the original test patch, confirm FACE, OSC1, OSC2, one held note, and MY PRESETS. Record rollback outcome.
6. Preserve CI #515 and the FAIL evidence; no merge and no new features until S0/S1 findings are addressed.

## 9. Reporting form

Use one row per failed/skipped check and short summaries for passes.

```text
Synth_esis 12A–12G hardware report
Build: #515 / 00aa639a
Firmware: ______  Schwung: ______  Manager: ______
Output: ______  MIDI input: ______  Browser: ______
Backup verified: PASS / FAIL

I01–I04: __ / __ / __ / __
N01–N08: __ / __ / __ / __ / __ / __ / __ / __
A01–A06: __ / __ / __ / __ / __ / __
M01–M07: __ / __ / __ / __ / __ / __ / __
V01–V09: __ / __ / __ / __ / __ / __ / __ / __ / __
P01–P08: __ / __ / __ / __ / __ / __ / __ / __
S01–S05: __ / __ / __ / __ / __
R01–R08: __ / __ / __ / __ / __ / __ / __ / __

For each FAIL:
ID: ___ / severity: S0,S1,S2,S3
Settings and steps: ______
Expected: ______
Observed: ______
Reproducible: Yes / No
Audio/photo/log reference: ______

For each SKIP:
ID: ___ / reason: ______ / retest requirement: ______

Rollback attempted: YES / NO
Rollback outcome: ______
Final decision: ACCEPT / CONDITIONAL (noncritical remaining) / REJECT / INCOMPLETE
Tester notes: ______
```

## 10. Final Go/No-Go

- **ACCEPT:** All mandatory I/N/A/M/V/P/S/R tests pass (including P08 if a historical Phase12C nonzero-velocity patch is available); any numeric precision-only V06 may be SKIP when a calibrated velocity source is unavailable *if* soft/hard playability tests pass, but document that limitation. No S0/S1/S2 defect remains unexplained; full Native+Remote UI acceptance requires R checks.
- **CONDITIONAL / INCOMPLETE:** Phase12C nonzero-velocity compatibility (P08) untested or browser-only R checks unavailable or optional precision checks skipped; continue working but do not call Phase12A–G fully hardware accepted.
- **REJECT / ROLLBACK:** Any S0/S1 regression, data loss, unsafe level, missing controls, or reproducible unacceptable performance.
- **NO MERGE:** Even PASS is an acceptance report, not authorization to merge. The user must explicitly approve a merge in a separate action.

## Appendix: What / How / Why of this acceptance document

**What:** One repeatable hardware + browser UI gate covering Phase12A–G and the correct Build #515 binary, with installation, rollback and structured results.

**How:** The checklist is derived from the actual Phase12 docs, current `module.json` page/encoder assignments, GitHub Actions artifacts and upstream Schwung's documented tarball installer and Remote UI.

**Why:** Avoid treating CI green as device acceptance or repeating small ad hoc tests without controlled settings. It also provides a precise failure report for later development, while protecting last working patches and `main`.
