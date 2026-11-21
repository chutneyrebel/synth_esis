"""Regression guards for Phase 10B.3 spectral integration."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SpectralIntegrationTests(unittest.TestCase):
    def test_shape_samples_processed_spectrum(self):
        dsp = (ROOT / "src/dsp.c").read_text()
        self.assertIn("float left=spectral_morph_at(shape_table", dsp)
        self.assertIn("float right=spectral_morph_at(shape_table", dsp)
        self.assertIn("float avg=.5f*(left+right);", dsp)
        self.assertNotIn("float avg=.5f*(table_at(shape_table", dsp)

    def test_spectral_controls_have_neutral_dsp_defaults(self):
        dsp = (ROOT / "src/dsp.c").read_text()
        for osc in ("osc1", "osc2"):
            for mode in ("shift", "fold", "scramble"):
                key = f"{osc}_spectral_{mode}"
                self.assertIn(f"P({key},100)", dsp)

    def test_six_spectral_controls_are_reachable_and_neutral(self):
        meta = json.loads((ROOT / "src/module.json").read_text())
        caps = meta["capabilities"]
        params = {p["key"]: p for p in caps["chain_params"]}
        levels = caps["ui_hierarchy"]["levels"]
        root_links = [p.get("level") for p in levels["root"]["params"] if isinstance(p, dict)]
        for osc in ("osc1", "osc2"):
            page = f"{osc}_spectral"
            self.assertIn(page, root_links)
            expected = [f"{osc}_spectral_{mode}" for mode in ("shift", "fold", "scramble")]
            self.assertEqual(levels[page]["knobs"][:3], expected)
            self.assertEqual(levels[page]["knobs"][3], "wavetable" if osc == "osc1" else "osc2_wavetable")
            for key in expected:
                self.assertEqual({k: params[key][k] for k in ("type", "min", "max", "default")},
                                 {"type": "int", "min": 0, "max": 100, "default": 0})

    def test_metadata_limit_and_future_spectral_page_contract(self):
        raw = (ROOT / "src/module.json").read_bytes()
        self.assertLess(len(raw), 8192)
        meta = json.loads(raw)
        levels = meta["capabilities"]["ui_hierarchy"]["levels"]
        for level in levels.values():
            self.assertLessEqual(len(level.get("knobs", [])), 8)


if __name__ == "__main__":
    unittest.main()
