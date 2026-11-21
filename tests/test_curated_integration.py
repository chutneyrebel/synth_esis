#!/usr/bin/env python3
"""Curated bank integration guard: IDs reserved, old presets unaffected."""
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]

class CuratedIntegrationTests(unittest.TestCase):
    def test_curated_lookup_is_compile_guarded(self):
        dsp=(ROOT/"src/dsp.c").read_text()
        build=(ROOT/"scripts/build.sh").read_text()
        self.assertIn("#ifdef SYNTH_ESIS_ENABLE_CURATED",dsp)
        self.assertIn("curated_table_at(t-108,p0,band,phase)",dsp)
        self.assertIn("curated_table_at(t-108,p1,band,phase)",dsp)
        self.assertIn("int t=clampi(table,0,107)",dsp)
        self.assertIn("int t=clampi(table,0,123)",dsp)
        self.assertIn("-DSYNTH_ESIS_ENABLE_CURATED -Ibuild",build)
    def test_existing_user_parameters_stay_legacy_bounded(self):
        params=json.loads((ROOT/"src/module.json").read_text())["capabilities"]["chain_params"]
        by_key={p["key"]:p for p in params}
        self.assertEqual(by_key["wavetable"]["max"],107)
        self.assertEqual(by_key["osc2_wavetable"]["max"],107)
        self.assertEqual(by_key["wt_bank"]["options"],["Legacy","Expanded"])
        self.assertEqual(by_key["curated_osc1"].get("default",0),0)
        self.assertEqual(by_key["curated_osc2"].get("default",0),0)
        self.assertEqual(by_key["curated_osc1"]["max"],16)
        self.assertEqual(by_key["curated_osc2"]["max"],16)
        # The descriptor may omit a zero default to meet Schwung's hard
        # metadata limit; DSP defaults() is authoritative for both slots.
        dsp=(ROOT/"src/dsp.c").read_text()
        self.assertIn("wipe(s,sizeof(*s));",dsp)
        self.assertIn("int source1=(s->osc1_source_curated&&s->curated_osc1)?107+s->curated_osc1:t0",dsp)
        self.assertIn("float original=table_at(index,position,band,phase)",dsp)
        self.assertIn("if(total<=0.f)return original",dsp)
        self.assertIn("int source2=(s->osc2_source_curated&&s->curated_osc2)?107+s->curated_osc2:s->osc2_wavetable",dsp)
        self.assertIn("float second=spectral_morph_at(source2,pos2,v->band,p2",dsp)
        levels=json.loads((ROOT/"src/module.json").read_text())["capabilities"]["ui_hierarchy"]["levels"]
        self.assertEqual(levels["osc1"]["knobs"][0],"curated_osc1")
        self.assertEqual(levels["osc2"]["knobs"][0],"curated_osc2")
if __name__=="__main__":
    unittest.main()
