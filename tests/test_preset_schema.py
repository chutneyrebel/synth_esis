#!/usr/bin/env python3
"""Host-side Phase 10A patch interchange regression tests."""
import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from preset_schema import default_patch, parse_patch, serialize_patch, validate_patch, parameter_specs, migrate_legacy_patch

class PresetSchemaTests(unittest.TestCase):
    def setUp(self):
        self.patch = default_patch("Test texture")

    def test_factory_library(self):
        library = json.loads((Path(__file__).resolve().parents[1] / "presets/factory.json").read_text())
        self.assertEqual(library["schema"], 1)
        self.assertEqual(library["library"], "Synth_esis Factory")
        self.assertEqual(len(library["presets"]), 16)
        self.assertEqual(len({p["id"] for p in library["presets"]}), 16)
        self.assertEqual(len({p["patch"]["name"] for p in library["presets"]}), 16)
        self.assertEqual(
            {p["category"] for p in library["presets"]},
            {"Bass", "Lead", "Pad", "Drone", "Texture", "Rhythmic"})
        for entry in library["presets"]:
            self.assertTrue(entry["description"].strip())
            upgraded = migrate_legacy_patch(entry["patch"])
            self.assertEqual(parse_patch(serialize_patch(upgraded)), upgraded)
            self.assertNotIn("vel_f", entry["patch"]["parameters"])

    def test_legacy_velocity_migration_is_neutral_and_strict(self):
        old = copy.deepcopy(self.patch)
        for key in ("vel_spec","vel_f","vel_s"):
            old["parameters"].pop(key)
        upgraded = migrate_legacy_patch(old)
        self.assertEqual([upgraded["parameters"][k] for k in
                          ("vel_spec","vel_f","vel_s")],[0,0,0])
        # Phase 12D's single velocity amount drove all three axes.
        old["parameters"]["vel_spec"] = 71
        upgraded = migrate_legacy_patch(old)
        self.assertEqual([upgraded["parameters"][k] for k in
                          ("vel_spec","vel_f","vel_s")],[71,71,71])
        old["parameters"].pop("cutoff")
        with self.assertRaises(ValueError):
            migrate_legacy_patch(old)
        old["parameters"]["cutoff"] = 78
        old["parameters"]["bogus"] = 2
        with self.assertRaises(ValueError):
            migrate_legacy_patch(old)

    def test_roundtrip(self):
        self.assertEqual(parse_patch(serialize_patch(self.patch)), self.patch)

    def test_complete_writable_parameters(self):
        self.assertEqual(set(self.patch["parameters"]), set(parameter_specs()))
        self.assertNotIn("face_snapshot", self.patch["parameters"])
        self.assertNotIn("voice_activity", self.patch["parameters"])

    def test_missing_and_unknown_parameters(self):
        for operation in ("missing", "unknown"):
            patch = copy.deepcopy(self.patch)
            if operation == "missing":
                patch["parameters"].pop(next(iter(patch["parameters"])))
            else:
                patch["parameters"]["unknown"] = 10
            with self.assertRaises(ValueError):
                validate_patch(patch)

    def test_invalid_values(self):
        for key, spec in parameter_specs().items():
            for bad in (float("nan"), float("inf"), True, "50"):
                patch = copy.deepcopy(self.patch)
                patch["parameters"][key] = bad
                with self.assertRaises(ValueError):
                    validate_patch(patch)
            patch = copy.deepcopy(self.patch)
            patch["parameters"][key] = 1000000
            with self.assertRaises(ValueError):
                validate_patch(patch)

    def test_identity_and_schema(self):
        for field, value in (("module_id", "sprig-wt"), ("schema", 99), ("name", "")):
            patch = copy.deepcopy(self.patch)
            patch[field] = value
            with self.assertRaises(ValueError):
                validate_patch(patch)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):
            parse_patch('{"schema":1,"schema":1}')

    def test_json_size_limit(self):
        with self.assertRaises(ValueError):
            parse_patch(" " * 65537)

if __name__ == "__main__":
    unittest.main()
