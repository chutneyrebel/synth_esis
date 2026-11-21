# Synth_esis Phase 12F: Readable Velocity Labels and Metadata Packing

**Development branch:** `development-phase12f-metadata-labels`
**Parent:** `development-phase12e-independent-velocity`
**Merge status:** DRAFT ONLY; never merge without explicit approval
**Hardware status:** NOT ACCEPTED

## Verified host research

Schwung's shared `param_pages/param_meta.mjs` resolves display text from
`meta.label || meta.name || key.replace(/_/g," ")`. For chain_params, the
supported display field is `name`. The stable `key` is what control, DSP and
presets use; renaming it would break preset compatibility.

The shared page planner accepts parameter references by key from
`ui_hierarchy.levels.*.params`. The root FACE was declared twice: as an
object in the root hierarchy and as an as_page/page_first canvas in
chain_params. The new packaged descriptor references the existing FACE
record with the string `"face"` instead of duplicating its type and page
flags. This change requires CI/planner and eventually Move validation.

Host references:
- https://github.com/charlesvestal/schwung/blob/main/src/shared/param_pages/param_meta.mjs
- https://github.com/charlesvestal/schwung/blob/main/src/shared/param_pages/page_plan.mjs
- https://github.com/charlesvestal/schwung/blob/main/docs/MODULES.md

## WHAT / HOW / WHY

| WHAT | HOW | WHY |
|---|---|---|
| Clearer on-device labels | Add `name` to only the three velocity chain params: `Vel Shift`, `Vel Fold`, `Vel Scram` | Make a parameter's purpose understandable without changing the MIDI/DSP key |
| Stable IDs | Keep `vel_spec`, `vel_f`, `vel_s` unchanged, with the same type/min/max/default behavior | Old 12C/D/E presets and automation must continue working |
| Canonical authoring source | Add `src/module.source.json` containing the richer metadata with its uncompressed FACE declaration | Editing readable source is safer than manually trimming the production JSON |
| Deterministic 8 KiB packer | `scripts/pack_metadata.py` converts only the duplicate FACE object to a string reference in `src/module.json`, fails if source shape or size changes | Save bytes without stripping nonzero defaults, changing DSP semantics or inventing host flags |
| Synchronize native and package metadata | `scripts/generate_metadata.py --check` verifies C metadata matches the packed module descriptor | Move and remote UI receive the same labels and parameters |
| Gate stale files in CI | `pack_metadata.py --check` and `generate_metadata.py --check` run before audio tests and during the ARM64 build | Prevent a source/packaging divergence |
| Document page contract | Update navigation test to resolve FACE's string reference against chain_params | Test semantic page order and behavior instead of relying on duplicate JSON syntax |

The generated production descriptor is **8,180 bytes**, below Schwung's
strict 8,192-byte loader ceiling. This phase gains labeling but not meaningful
headroom for arbitrary additional parameters: only 12 bytes remain. Further
metadata growth should trigger a reviewed redesign, not untested removal of
defaults or abbreviations of parameter IDs.

## Design boundaries

- No changes to `src/dsp.c`, modulation destinations 0–17, stored preset keys,
  wavetable mapping, eight-voice logic, old default values, or note articulation.
- Both oscillator spectral levels retain seven encoder assignments, in the
  same order.
- No new page and no host patch is required for the labels.
- The native FACE page still requires validation that Schwung resolves its
  string hierarchy reference exactly as expected.
- The metadata packer only changes one duplicated FACE declaration. It does
  not compress arbitrary names/defaults, and fails closed on unexpected
  source structure.
- Continue treating old implicit zero-default host behavior inherited from
  Phase12E as a separate unresolved hardware acceptance concern.

## Verification plan / exact commands

```sh
python3 scripts/pack_metadata.py --check
python3 scripts/generate_metadata.py --check
python3 -m unittest discover -s tests -p 'test_metadata_pack.py'
python3 -m unittest discover -s tests -p 'test_navigation_contract.py'
python3 tests/test_plugin.py
python3 -m unittest discover -s tests -p 'test_preset_*.py'
node tests/test_canvas.cjs
bash scripts/build.sh
python3 tests/check_package.py
```

GitHub Actions runs the corresponding workflow. Source commits and successful
Python syntax are not substitutes for completed CI results. Confirm the actual
run conclusion and uploaded ARM64 archive before installing.

## Hardware test decision

**Not yet.** Do not introduce an extra Move session just to inspect labels.
After a green complete build, combine Phase 12F label/page verification with
the already deferred Phase 12A/B/C/D/E audio and preset acceptance plan.

On Move after CI:
1. Visit OSC1 and OSC2 spectral parameter pages and confirm
   `Vel Shift`, `Vel Fold` and `Vel Scram` display with distinct names.
2. Confirm the same three knobs change exactly the same parameters as 12E
   and the sound remains unchanged with all values zero.
3. Confirm FACE is still first and its eight encoders/animation work,
   no redundant MAIN, no missing/extra pages.
4. Reload older curated, regular wavetable and Phase12D/E patches.
5. Verify Move-specific CPU and UI navigation do not regress.

## Risks / remaining work

- Only 12 bytes of production metadata capacity remain.
- The full hierarchical page planner and actual hardware loader must confirm
  the compact FACE reference.
- Host changes could affect label resolution; testing against a pinned
  Schwung revision is preferable to assuming latest is always compatible.
- Existing Phase12E preset/migration and audio CI failures must also be
  repaired before claiming this branch is hardware ready.
- No changes should reach main without explicit user authorization.

## Next choices

A. Recommended: resolve CI failures and prepare a single consolidated hardware
   test for 12A/B/C/D/E/F.
B. Prototype a future metadata architecture which moves additional interface
   descriptions out of module.json into host-supported UI files, separately.
C. Pause features and review UI naming, encoder layout and screen visual
   consistency before any next DSP phase.
