"""Regression guard for the Synth_esis hardware page navigation contract."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_LEVELS = [
    "osc1", "osc1_spectral", "osc2", "osc2_spectral", "filter", "motion", "matrix",
    "osc1_amp", "osc2_amp", "osc_mix",
]
EXPECTED_FACE_KNOBS = [
    "lfo_rate", "lfo_depth", "lfo_filter", "cutoff",
    "resonance", "master_pan", "level", "osc2_volume",
]


class NavigationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = json.loads((ROOT / "src/module.json").read_text())

    def test_face_precedes_all_child_levels(self):
        root = self.module["capabilities"]["ui_hierarchy"]["levels"]["root"]
        first, *remaining = root["params"]
        self.assertEqual(first["key"], "face")
        self.assertEqual(first["type"], "canvas")
        self.assertIs(first["as_page"], True)
        self.assertIs(first["page_first"], True)
        self.assertEqual([p["level"] for p in remaining], EXPECTED_LEVELS)

    def test_face_encoder_bindings_preserved(self):
        root = self.module["capabilities"]["ui_hierarchy"]["levels"]["root"]
        self.assertEqual(root["knobs"], EXPECTED_FACE_KNOBS)
        self.assertEqual(len(root["knobs"]), 8)

    def test_all_child_levels_resolve(self):
        levels = self.module["capabilities"]["ui_hierarchy"]["levels"]
        for key in EXPECTED_LEVELS:
            with self.subTest(level=key):
                self.assertIn(key, levels)

    def test_both_spectral_pages_render_oscillator_faces(self):
        levels=self.module["capabilities"]["ui_hierarchy"]["levels"]
        params={p["key"]:p for p in self.module["capabilities"]["chain_params"]}
        for osc in (1,2):
            face=f"face_osc{osc}"
            level=f"osc{osc}_spectral"
            self.assertEqual(levels[level]["params"],[face])
            self.assertEqual(levels[level]["knobs"][:3],
                             [f"osc{osc}_spectral_{effect}" for effect in ("shift","fold","scramble")])
            self.assertEqual(params[face]["canvas_overlay"],f"sprig_osc{osc}")
            self.assertEqual(params[face]["extra_keys"],
                             ["face_snapshot","voice_activity",f"curated_osc{osc}"])
            self.assertEqual(levels[f"osc{osc}"]["params"],[face])

    def test_no_unsupported_grid_suppression_flag(self):
        # Schwung 1.9.3 has not verified an opt-in grid-suppression
        # contract. Don't silently add an invented flag to module.json.
        root = self.module["capabilities"]["ui_hierarchy"]["levels"]["root"]
        self.assertNotIn("hide_grid", root)
        self.assertNotIn("canvas_replaces_grid", root)


if __name__ == "__main__":
    unittest.main()
