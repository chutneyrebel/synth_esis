#!/usr/bin/env python3
"""Phase 10 integration guard: verify that lookup consolidation keeps all historical rows.
This is a static contract test; audible/hardware validation is tracked separately.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

class WavetableBoundaryTests(unittest.TestCase):
    def test_lookup_boundary(self):
        header = (ROOT / "src/wavetable_engine.h").read_text()
        dsp = (ROOT / "src/dsp.c").read_text()
        self.assertIn('#include "expanded_tables.h"', header)
        self.assertIn("sprig_table_lookup_legacy", header)
        self.assertIn("sprig_table_lookup_expanded", header)
        self.assertNotIn("static float expanded_lookup(", dsp)
        self.assertIn("sprig_table_lookup_expanded(t-4,p0,band,phase)", dsp)
        self.assertIn("sprig_table_lookup_expanded(t-4,p1,band,phase)", dsp)
        self.assertIn("int t=clampi(table,0,107)", dsp)
        self.assertIn("if(t>=100)pt=pt*pt*(3.f-2.f*pt)", dsp)

    def test_lookup_math_remains_identical(self):
        header = (ROOT / "src/wavetable_engine.h").read_text()
        fn = header.split("static inline float sprig_table_lookup_expanded(",1)[1].split("\n}",1)[0]
        for statement in (
            "int i=(int)phase & 255;",
            "float t=phase-(float)((int)phase);",
            "const float *row=sprig_expanded_tables[table][frame][band];",
            "return row[i]+(row[(i+1)&255]-row[i])*t;",
        ):
            self.assertIn(statement, fn)

if __name__ == "__main__":
    unittest.main()
