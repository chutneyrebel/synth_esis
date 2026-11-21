"""Phase12F regression: semantic source -> strict packed descriptor."""
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from pack_metadata import pack, SOURCE, TARGET, MAX_BYTES


class MetadataPackTests(unittest.TestCase):
    def test_packed_descriptor_is_current_and_bounded(self):
        self.assertEqual(pack(),TARGET.read_text())
        self.assertLess(len(pack().encode()),MAX_BYTES)

    def test_only_duplicate_face_structure_is_compacted(self):
        source=json.loads(SOURCE.read_text())
        packed=json.loads(TARGET.read_text())
        self.assertEqual(packed["capabilities"]["ui_hierarchy"]["levels"]
                         ["root"]["params"][0],"face")
        packed["capabilities"]["ui_hierarchy"]["levels"]["root"]["params"][0]={
            "key":"face","type":"canvas","as_page":True,"page_first":True
        }
        self.assertEqual(packed,source)

    def test_velocity_names_do_not_change_keys_or_saved_parameters(self):
        from preset_schema import parameter_specs
        packed=json.loads(TARGET.read_text())
        params={p["key"]:p for p in packed["capabilities"]["chain_params"]}
        for key,label in (("vel_spec","Vel Shift"),("vel_f","Vel Fold"),
                          ("vel_s","Vel Scram")):
            self.assertEqual(params[key]["name"],label)
            self.assertEqual((params[key]["min"],params[key]["max"]),(0,100))
            self.assertIn(key,parameter_specs())
        levels=packed["capabilities"]["ui_hierarchy"]["levels"]
        for osc in ("osc1_spectral","osc2_spectral"):
            self.assertLessEqual(len(levels[osc]["knobs"]),8)
            self.assertEqual(levels[osc]["knobs"][-3:],["vel_spec","vel_f","vel_s"])


if __name__=="__main__":
    unittest.main()
