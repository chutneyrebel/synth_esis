# Synth_esis Phase 12E — Independent Velocity Intensity Controls

**Branch:** `development-phase12e-independent-velocity`
**Baseline:** Phase 12D `a8317dbf63995aa7012be4389ab492c14641d35f`
**Status:** experimental / CI and Ableton Move acceptance required
**Merge policy:** DO NOT MERGE to Phase12D, Phase12C, Phase12A/B or main.

## Design / intended performance

Separate the original velocity-to-Shift behavior from the note-on spectral
Fold and Scramble envelopes. A producer can set each intensity independently
while maintaining eight-note polyphony and the existing modulation matrix.

| Axis | Persistent control | Default | Response |
|---|---|---:|---|
| Shift | `vel_spec` (existing Phase 12C key) | 0 | Constant per-note signed Shift amount; no temporal envelope |
| Fold | `vel_f` (new) | 0 | Velocity-scaled 12ms attack / 420ms decay spectral contour |
| Scramble | `vel_s` (new) | 0 | Velocity-scaled 12ms attack / 420ms decay contour, scaled by 0.65 |

All three controls use 0–100. The normalized velocity offset is
`((velocity - 64) / 63) * 0.35`, then multiplied by the chosen control
percentage. 64 is neutral; positive and negative changes are clamped to the
legal spectral depth interval [0,1].

Each voice maintains its own envelope. OSC1 and OSC2 both read the same
three control amounts but calculate them independently per sounding note.
Separate per-oscillator velocity controls are **not** part of this phase.

## What / How / Why

| What | How | Why |
|---|---|---|
| Independent Shift/Fold/Scramble | Keep existing `vel_spec` for Shift; add `vel_f` and `vel_s` to DSP and two native Schwung spectral levels | Each effect can be expressed or silenced independently |
| No new DSP oscillator/clock | Reuse existing voice-local note velocity, spectral envelope and trilinear spectral lookup | Avoid extra table builds, FFT, scheduling and instability |
| Phase12D patch migration | During `state` load, initialize all new amounts to zero, then let missing Fold/Scramble inherit the saved legacy `vel_spec` | A Phase12D preset where one control drove all three axes must sound the same after upgrade |
| New preset format | Serialize `vel_spec`, `vel_f`, `vel_s` as named values; the state parser accepts old names | Retains old keys and numeric matrix route IDs 0–17 |
| Factory patch migration | Add explicit `migrate_legacy_patch` that fills only known new velocity fields, keeping strict `validate_patch` for all other omissions and unknowns | Fixes Phase12D Build #487 without weakening validation |
| Schwung metadata budget | Preserve all historical parameter keys/IDs; omit optional zero-default metadata for nonlegacy fields whose DSP defaults are zero; keep both spectral pages under eight encoders | Loader rejects descriptors >=8192 bytes |
| CI | Add Phase12E pattern to workflow, extend DSP audio tests and preset regression suite | Verify code with actual host ABI and ARM64 output without merging |

## Metadata implementation and caveats

The compact parameter keys are intentional because the metadata budget is
almost fully exhausted. On both OSC1 and OSC2 spectral levels:
- `vel_spec` = velocity Shift
- `vel_f` = velocity Fold
- `vel_s` = velocity Scramble

Seven knobs per spectral level, no new page. Native Schwung may show these
compact names until a verified labeling solution is available. Total
`module.json` size is 8180 bytes (<8192), leaving only 12 bytes headroom.
DO NOT add unreviewed metadata.

Legacy parameter fields enumerated in `tests/preset_abi_baseline.json` remain
unchanged. Omitted optional defaults on nonlegacy zero-initialized fields
must be checked against live Schwung host behavior at hardware acceptance.

## State compatibility policy

1. Pre-12C patch: no velocity keys -> Shift/Fold/Scramble all zero.
2. Phase12C/12D patch: `vel_spec=75`, no `vel_f` or `vel_s` ->
   Shift/Fold/Scramble each inherit 75.
3. Phase12E patch: all three keys saved independently -> all exact values
   restored; nothing else gets inferred.
4. Loading a legacy patch after a Phase12E patch clears previous velocity
   amounts and does not retain hidden modulation.
5. All original modulation matrix IDs and waveform/preset source IDs remain.

For JSON factory patches, `migrate_legacy_patch` performs the equivalent
explicit upgrade. `validate_patch` remains strict, so unexpected missing
or unknown parameters cannot be quietly accepted.

## CI and automated tests

Phase12E CI is expected to execute:
- Host ABI build: `python3 tests/test_plugin.py`
- Preset migration: `python3 -m unittest discover -s tests -p 'test_preset_*.py'`
- Spectral audio: `python3 -m unittest discover -s tests -p 'test_spectral_audio_integration.py'`
- Canvas graphics: `node tests/test_canvas.cjs`
- ARM64 host package: `bash scripts/build.sh` and `python3 tests/check_package.py`

New tests cover independent velocity axes on both oscillators, old Phase12D
state migration, separate new-state roundtrips, null velocity neutrality,
old factory-library migration and strict unknown-parameter rejection.

**CI passes must be verified from actual completed GitHub Actions runs,
not inferred from committed source or draft PR status.**

## Hardware test decision

No individual hardware test is warranted while Phase12E CI is pending.
After one green ARM64 build, conduct a **combined Phase12A/B/C/D/E** test
instead of testing small fixes separately.

Focused Phase12E part of consolidated checklist:
1. Confirm an old patch has all velocity controls neutral by default.
2. Curated 8, OSC1 only, Shift/Fold/Scramble manually ~35–50, soft vs
   hard notes. Set all three velocity controls to zero; compare.
3. Set only `vel_spec=100`: Shift changes, not transient Fold/Scramble.
4. Set only `vel_f=100`: Fold makes a transient (attack/decay).
5. Set only `vel_s=100`: Scramble makes a different transient.
6. Repeat with OSC2 only; check mute, pan, chord voices and headroom.
7. Load a Phase12D preset with nonzero `vel_spec` and verify old
   combined sonic behavior is restored by inheritance.
8. Save/reload a new preset with unequal values for all three controls.
9. Test eight-voice rapid chords, global LFO spectral routes and full
   preset/wavetable source recall. Record PASS/FAIL/SKIP.

## Remaining risks

- Metadata headroom is only 12 bytes; new features need redesign or host
  architecture changes, not more descriptor fields.
- The visual graph shows global spectral motion, not each note's private
  velocity articulation.
- CPU/voice load has not been measured on Move. Sound audibility and
  musical quality require listening.
- Omitted default fields require host-side verification.
- Phase12A/B and downstream stages have not yet been hardware accepted.

## Next steps

A. Recommended: inspect Phase12E CI, fix every regression to green, capture
   ARM64 archive, prepare one consolidated hardware acceptance checklist.
B. Before hardware test, improve native knob label clarity without growing
   metadata or changing existing ABI; needs host compatibility analysis.
C. Freeze Phase12E; prototype independent per-oscillator velocity scaling on
   a separate subsequent branch only after A.
