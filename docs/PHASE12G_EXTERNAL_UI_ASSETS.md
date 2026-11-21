# Synth_esis Phase 12G: Host-Supported External UI Assets

Branch: `development-phase12g-external-ui-assets`
Parent: `development-phase12f-metadata-labels`
Status: experimental; CI and Move acceptance pending.
Integration: draft PR into Phase12F development ONLY. No merge to main.

## Architecture decision: findings from upstream Schwung

A critical host constraint prevents the proposed simplistic "put all
metadata in a file" strategy:

1. **Sound generators must serve `ui_hierarchy` from
   `get_param("ui_hierarchy")`.** Native chain host does not read their
   `module.json` hierarchy as a substitute. It also needs DSP-exposed
   `chain_params`. Removing or relocating these would hide native pages.
2. Schwung Manager **does** support `web_ui.html` and sibling assets at
   `/api/remote-ui/module-assets/<module-id>/<path>`, including JavaScript
   and CSS. Remote UI custom panels can drive existing controls through
   `schwungRemote.setParam(component + ":" + key, value)`.
3. Native `canvas.js` remains the documented host canvas graphics
   implementation. External web UI assets are **not** loaded into the
   native Move control hierarchy. `ui_chain.js` is not a supported
   replacement for a synth that currently serves its hierarchy.
4. Schwung `module.json` still has an 8 KiB loader limit. External
   browser descriptions avoid adding bytes to that file but do **not**
   increase the native chain parameter budget.

Upstream documentation:
- https://github.com/charlesvestal/schwung/blob/main/docs/MODULES.md
  (Remote UI Custom HTML, File Layout, Shadow UI Parameter Hierarchy)
- https://github.com/charlesvestal/schwung/blob/main/src/shared/param_pages/param_meta.mjs
- https://github.com/charlesvestal/schwung/blob/main/src/shared/param_pages/page_plan.mjs

## WHAT / HOW / WHY

| WHAT | HOW | WHY |
|---|---|---|
| External browser-only UI descriptions | `src/assets/ui_reference.js` exports frozen metadata for velocity Shift/Fold/Scramble and six spectral depths | Allow future detailed label/help metadata to grow without consuming the native 8192-byte module descriptor |
| Browser spectral-expression section | `web_ui.html` adds a fifth section and reads three velocity controls from the sidecar | Make new expressive controls discoverable in the Schwung Remote UI |
| Contextual descriptions | `control()` renders the optional help string under mapped sliders | Explain the distinction between sustained Shift and Fold/Scramble attack/decay |
| Artist identity cleanup | Browser header changes deprecated "SPRIG WT" to "Synth_esis" | Align Remote UI with the actual module name |
| Exact archive contents | `scripts/build.sh` includes `src/assets/`; `tests/check_package.py` checks the required asset hash | Ensure browser preview and packaged module cannot silently diverge |
| New independent regression | Node VM tests sidecar contents against real `module.json` keys, validates script/section and component-prefixed writes | Catch invalid keys and missing assets before hardware work |
| Inherited Phase12F regression | `tests/test_plugin.py` now resolves compact FACE by key from `chain_params` | Fix Build #508's overly literal expectation of a duplicated FACE object without changing audio or page order |
| Isolated CI | Add Phase12G branch trigger and new UI asset test | Produce evidence without touching main |

## Exactly what does NOT change

- No `src/dsp.c` modifications.
- No DSP ABI, `get_param`/ `set_param` behavior, state serialization,
  parameter keys, numerical modulation IDs, wavetable selections, presets,
  factory sound definitions, or eight-voice audio path.
- No changes to `module.json`, its size/loader limits or generated
  `ui_metadata.h`.
- No changes to native `canvas.js`, the on-device FACE/OSC navigation, or
  the fixed encoder hierarchy.
- No `ui_chain.js` host override or unsupported file-based hierarchy.

## Source layout and extension instructions

```
src/
  module.source.json       canonical authoring source (Phase12F)
  module.json              compact native descriptor (Phase12F)
  ui_metadata.h            DSP embedded hierarchy/parameters
  web_ui.html              Remote UI HTML entry point
  canvas.js                native Move graphics
  assets/
    ui_reference.js        browser-only labels and descriptions (Phase12G)
```

To add explanations for an **existing** DSP parameter:
1. Add a record to `src/assets/ui_reference.js` containing the
   stable `key`, short `label`, and plain-language `help`.
2. Reference the section in `web_ui.html` if it is a new visible control.
   The remote panel already uses the component-qualified Schwung API;
   do not hardcode a slot or add raw MIDI commands.
3. Run `node tests/test_external_ui_assets.cjs`. It will reject unknown
   parameter keys, duplicates and unsupported ranges.
4. Run complete GitHub CI. The archive must contain
   `assets/ui_reference.js` identical to the tested source.

To add a genuinely **new native Move encoder** requires adding the key to
DSP parameter registration, state schema, native `chain_params` and
`ui_hierarchy`, then satisfying the 8 KiB metadata limit. Browser sidecar
metadata alone does not create native controls.

## CI validation

Required:
- `node tests/test_external_ui_assets.cjs`
- `python3 scripts/pack_metadata.py --check`
- `python3 scripts/generate_metadata.py --check`
- `python3 tests/test_plugin.py`
- Preset/velocity spectral integration and native canvas regression suites
- `python3 -m unittest discover -s tests -p 'test_navigation_contract.py'`
- `node tests/test_schwung_canvas_only.mjs <host-checkout>`
- `bash scripts/build.sh`
- `python3 tests/check_package.py`

The package exact-file test now expects the new asset and checks its SHA256
against the source file.

## Hardware test recommendation

**Do not hardware-test yet** while CI is unverified. The browser-only UI is
a suitable follow-up check after the combined Phase12A/B/C/D/E/F acceptance
candidate is green. Then open Schwung Remote UI, load Synth_esis on Move,
open its custom synth panel and confirm the spectral-expression section and
labels work; use the Default Interface toggle if needed.

Check native pages separately and verify they look and behave exactly as in
Phase12F. External UI metadata must never determine whether the DSP runs.

## Known risks

- Asset URL routing depends on Schwung Manager's documented custom module
  path; this code has not been smoke-tested in a connected browser.
- A missing asset intentionally leaves the optional spectral-expression
  group empty, rather than breaking the entire existing Remote UI.
- The host 8 KiB native descriptor cap remains an architectural bottleneck.
- The underlying Phase12A–F branches are not yet hardware accepted.
- This is a **scalable browser presentation architecture**, not a native
  parameter metadata migration. Conflating those would break this synth.

## Next choices

A. Recommended: stabilize current CI/ARM64 archive and perform a consolidated
   hardware plus Remote UI acceptance session.
B. Develop additional browser-only sound design documentation, presets
   browser and LFO route descriptions from this sidecar, without DSP changes.
C. Research a genuine native metadata extension in upstream Schwung on a
   *separate host fork* and test compatibility before changing Synth_esis.
