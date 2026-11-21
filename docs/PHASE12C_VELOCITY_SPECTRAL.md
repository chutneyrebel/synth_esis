# Synth_esis Phase 12C — Voice-local velocity-to-spectral Shift

Status: development candidate, hardware NOT accepted.
Branch: `development-phase12c-velocity-spectral`
Parent: Phase 12A/B `c36bc8131cc1aa89479f14604e32e53a5876f628`
Do not merge into main without explicit approval.

## Goal

Make the touch of a note change its timbre, not just its loudness. This stage
adds velocity-responsive spectral *Shift* to each active voice, while leaving
the existing global LFO modulation matrix, eight-voice engine and stored
parameter IDs undisturbed. This is a deliberately limited Phase 12C batch:
Fold/Scramble velocity response and multi-stage per-note articulation remain
future options.

## What / How / Why

| What | How | Why |
| --- | --- | --- |
| New `vel_spec` parameter (0–100), default 0 | Appended to chain metadata, registered with DSP param table, exposed as an encoder on both OSC spectral parameter levels | Musicians can opt into key-velocity timbre response on either spectral page |
| Per-voice spectral Shift | Use the `Voice.vel` already latched by `note_on` and compute one clamped shift per oscillator per active voice | Soft and hard notes in a chord should sound different without resetting the global spectral motion |
| Note-specific timbre layered over 12A/B | `effective_shift = clamp(global_smooth_shift + ((velocity-64)/63) * 0.35 * vel_spec/100,0,1)` | Preserves the previous LFO matrix and manual Shift while adding controllable expressive detail |
| Old preset neutrality | Before parsing a saved state, reset `vel_spec=0`; existing full states serialize `vel_spec` as a new named key | Loading pre-12C patches must never inherit sensitivity from an edited patch |
| Schwung metadata budget | Omit redundant explicit zero defaults for six spectral axes and two curated selection fields, preserving actual zero initialization in DSP | Existing metadata was only 6 bytes below the strict 8192-byte loader limit |
| CI branch coverage | Add `development-phase12c-*` to build workflow branch triggers | The isolated branch must build without touching main |

### Velocity behavior

- Velocity 64 is mathematically neutral. Velocity 127 pushes Shift up by up to
  0.35 at `vel_spec=100`; low velocities lower it by up to about 0.35.
- `vel_spec=0` gives exactly the old Phase 12A/B Shift signal, even with
  velocity 1, 64, or 127. Existing velocity-to-volume scaling is unchanged.
- The offset applies independently to OSC1 and OSC2, but uses one shared
  intensity knob. Both OSC spectral levels expose the same parameter.
- It modulates Shift only, not Fold/Scramble, pitch, filter, envelope, or LFO
  routes; existing numeric matrix IDs 0–17 remain unchanged.
- The canvas visualizes global effective LFO spectral Shift, not per-note
  velocity-specific shifts: a single graph cannot faithfully display eight
  different timbres without a separate design.

### Preset / host compatibility

- No changes to module ID (`synth_esis`), API version (2), old keys,
  saved numeric matrix destinations, sound bank mappings or page ordering.
- New states contain `vel_spec`; old saved states omit it and restore to 0.
- Metadata stays under 8192 bytes. Default omission in metadata is valid for
  zero-initialized DSP fields, but actual Schwung host behavior must still
  be checked before hardware acceptance.
- Full state remains constrained by the existing 2048-byte state parser.
- Phase 12A/B must still pass its own pending Move acceptance checks.
- No changes to `main`, no merges.

## Automated acceptance and evidence

Run on CI:

1. `python3 scripts/generate_metadata.py --check`
2. `python3 tests/test_plugin.py` (build desktop host DSP and validate ABI)
3. `python3 -m unittest discover -s tests -p test_spectral_audio_integration.py`
4. `node tests/test_canvas.cjs`
5. `bash scripts/build.sh`
6. `python3 tests/check_package.py`
7. Check archive is the ARM64 Schwung module and the installed metadata is < 8192 bytes.

New integration cases assert note velocities 20, 64 and 120, `vel_spec`
0 versus 100, both oscillators, neutral-center identity, roundtrip,
and pre-12C state load resets.

**CI verdict:** Only mark GREEN when the actual run is completed successfully.
A pushed commit or available test definition is not CI evidence.

## Hardware decision

**Do not request a separate hardware test for this small change yet.**
First confirm CI and consolidate the Phase 12A/B and 12C checks into one
test candidate. Then evaluate on Ableton Move, including:

1. Load old curated and regular WT presets. Confirm no changed sound at
   `vel_spec=0`.
2. On OSC1 spectral page choose curated 8, set Shift=50, Fold/Scramble=0,
   `vel_spec=100`. Play same note softly and firmly and compare to
   `vel_spec=0`, keeping other settings unchanged.
3. Repeat with OSC1 muted and OSC2 audible.
4. Hold a soft note while triggering a harder note. Ensure both timbres
   coexist without unexpected retriggering or note loss.
5. With LFO spectral Shift routed at nonneutral depth, verify velocity
   adds character without making the 12A/B motion disappear.
6. Save and recall a Phase 12C patch; then load a Phase 12A/B patch.
   `vel_spec` should return to 0 for the older state.
7. Run eight notes with both oscillators, high spectral Shift modulation,
   and varied velocities. Listen for clicks, clipping and dropped voices.

### Outstanding risks

- Current voice-global image shows LFO-derived spectral depth, not velocity
  of individual sounding voices. This is documented behavior.
- Extreme velocities and fully modulated Shift may clamp at 0 or 1, reducing
  audible response at the endpoints.
- A host metadata field with omitted `default:0` must use DSP initialization
  as expected; hardware integration is not yet established.
- CPU, memory, and signal level impact require actual Move testing.
- CI may find host regressions missed by source review.

## Follow-on options

A. **Recommended:** verify CI, repair any failures and prepare one combined
   Phase 12A/B/C hardware acceptance checklist.
B. Expand Phase 12C with independent velocity amount per oscillator, only
   after the shared-intensity implementation has passed CI and listening tests.
C. Explore velocity-to-Fold / velocity-to-Scramble and per-note evolving
   spectral envelopes as a separate Phase 12D prototype.
