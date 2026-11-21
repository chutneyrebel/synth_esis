# Synth_esis standalone advanced synthesizer roadmap

Decision: all sound design, performance, macro assignment, wavetable editing, and preset operations must work directly on Ableton Move. A web editor is **not** part of the product roadmap. Inspired by TinyHouse's synthesis depth and resource safeguards, not its browser workflow. No TinyHouse or GPL Vital code copied.

Branch: `development-phase10-11`; draft PR #33. This document is a plan, not proof of runtime support. Do not merge without explicit user approval.

## Baseline verified from Synth_esis source

- Schwung API v2 sound generator, ARM64 freestanding `dsp.so`, 128x64 native canvas pages.
- Eight synth voices per instance; eight static instance slots; voice stealing already implemented.
- Two oscillators, per-oscillator envelopes, 8 existing warp modes, modulation and filter pages.
- 108 historical wavetable IDs (0–107) must remain stable. Curated IDs 108–123 are compiled behind a guard but not selectable in current metadata; new bank is **not yet playable through UI**.
- `module.json` currently exposes many chain params; metadata and state-size budgets require measurement before expansion.
- DSP build is freestanding: no libc, no dynamic dependencies; real-time render must remain bounded, allocation-free and free of disk I/O.
- Canvas `as_page` rendering works; **editing gestures, encoder click/shift combos, file save/load, dynamic parameter binding and jog-wheel navigation must be verified in upstream Schwung** before committing to a UI interaction.

## Feasibility gates (before implementation)

| Gate | Verification | Stop condition |
| --- | --- | --- |
| H1 host navigation | Inspect Schwung native page ordering, canvas overlay input/encoder bindings, button/shift handling; prototype one reversible editor gesture on Move | No supported hardware gesture for safe editing |
| H2 host state/presets | Measure serialized `state` and chain params, verify host persistence and reset/rollback; test saved set across reboot | Exceeds host buffer or corrupts existing set |
| H3 DSP budget | Record worst-case ARM64 audio-block time, stack/RAM, `dsp.so` size for 1 and 4 active slots | Glitches or unacceptable latency at normal settings |
| H4 preset compatibility | Capture and compare representative legacy patches, IDs, page navigation and state round-trips | Unintended sound/state changes |
| H5 input/edit safety | Determine whether Move exposes text entry, file browsing and user storage APIs; design encoder-only alternatives | Feature requires browser or unsafe host modifications |
| H6 release hygiene | Run CI, on-device load test, backup and rollback installation path | No reliable recovery procedure |

Do not assume TinyHouse's internal host extensions are upstream Schwung APIs. Confirm compatibility against `charlesvestal/schwung` and actual Move firmware/Schwung version.

## Revised development sequence

### Phase 10: Finish curated bank and compatibility
- Make 16 curated tables selectable on OSC1 and OSC2 without changing legacy IDs 0–107 or default sounds.
- Correct band-limited interpolation, normalization and level matching; compare old preset output.
- Acceptance: CI, ARM64 load, oscillator independence, wavetable scan, preset and CPU hardware tests.

### Phase 11: Oscillator interaction
- Dedicated OSC INTERACTION page with mode, source, depth, ratio, feedback, phase, mix and output (provisional labels).
- Incremental algorithms: ring/AM first, then phase distortion and FM; zero-depth must bypass exactly.
- Use bounded per-voice processing, avoid runaway feedback and aliasing; retain old patches unchanged.
- Acceptance: measured level/aliasing, stress tests and audible distinctiveness.

### Phase 12: Eight on-device performance macros
- Eight macros, each mapped to multiple destinations with bipolar amounts and optional inversion.
- Map/unmap, rename or choose concise labels, adjust depth and inspect destinations using Move hardware only.
- First gate: validate host hardware input model. If arbitrary naming is not possible, use built-in label vocabulary.
- Acceptance: no accidental edits, deterministic mapping, saved-set persistence, zero unintended sound change on assignment.

### Phase 13: Unison and voice management
- Per-oscillator unison count, detune and stereo spread, global polyphony cap, deterministic voice stealing.
- CPU-safe caps and conservative defaults; test four simultaneous Move slots and worst-case envelopes.
- Acceptance: no stuck notes, predictable output level and bounded block time.

### Phase 14: Modulation depth
- Expand matrix destinations, LFO shapes/sync, envelope routes and mod-to-mod relationships.
- Avoid overwhelming page navigation; display source, destination and signed depth clearly.
- Acceptance: parameter smoothing, bounded rates, persistence and hardware navigation tests.

### Phase 15: Native effects
- Start with efficient drive/saturation and modulation FX, then tempo-aware delay/reverb only if H3 budget permits.
- Bypass and wet/dry must preserve old patch levels; no third-party GPL code without explicit licensing decision.
- Acceptance: block-time, clipping/headroom and multitrack tests.

### Phase 16: On-device wavetable editing
- Native editor modes: select frame, harmonic/bin, level, phase, transform, audition, undo/redo.
- No browser requirement. Compute/prepare spectral changes outside real-time audio callback; swap precomputed tables safely.
- Gate on actual host gestures, memory, save APIs and 128x64 legibility.
- Acceptance: editing a custom table and saving/reloading it entirely from Move.

### Phase 17: Presets and banks on Move
- Native save/rename/select/duplicate/delete workflow, versioned state, migration and backup.
- Avoid relying on file APIs unavailable to a Schwung module; verify first.
- Acceptance: persistence through restart, corrupt-file handling, rollback and no silent overwrite.

### Phase 18: Release hardening
- Full polyphony/CPU/RAM stress, aliasing/headroom, 128x64 UI, all encoder mappings, saved-state regression.
- Separate development PR; only merge with explicit approval after on-device sign-off.

## UI principles

- Eight encoders should always have legible, context-sensitive destinations.
- Prefer one clear page per function; no redundant MAIN pages.
- A visual page is not an editor unless there is a proven hardware gesture for edit mode, selection and confirmation.
- Fast audition and performance controls remain accessible without entering editing modes.
- Every destructive action must be reversible or confirmed on-device.
- The hardware remains fully functional without browser/network access after installation.

## Immediate next checkpoint

1. Verify upstream Schwung APIs for native encoder/button events, canvas overlays, saved state and file access.
2. Measure current Synth_esis metadata and state serialization limits.
3. Complete selectable 16-table DSP integration on existing development branch, with compatibility tests.
4. Do not install until CI and package checks pass; no merge to main.
