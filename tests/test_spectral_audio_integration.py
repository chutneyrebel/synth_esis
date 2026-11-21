"""Host audio integration tests for baked compositional spectra.

Requires build/dsp-host.so from tests/test_plugin.py (the preceding CI step).
The numbers are output comparisons, not claims about Move CPU performance.
"""
import ctypes as C
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


CREATE = C.CFUNCTYPE(C.c_void_p, C.c_char_p, C.c_char_p)
DESTROY = C.CFUNCTYPE(None, C.c_void_p)
MIDI = C.CFUNCTYPE(None, C.c_void_p, C.POINTER(C.c_uint8), C.c_int, C.c_int)
SET = C.CFUNCTYPE(None, C.c_void_p, C.c_char_p, C.c_char_p)
GET = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_char_p, C.c_char_p, C.c_int)
RENDER = C.CFUNCTYPE(None, C.c_void_p, C.POINTER(C.c_int16), C.c_int)


class Plugin(C.Structure):
    _fields_ = [("api_version", C.c_uint32), ("create", CREATE),
                ("destroy", DESTROY), ("midi", MIDI), ("set", SET),
                ("get", GET), ("error", GET), ("render", RENDER)]


def rms(values):
    return math.sqrt(sum(x * x for x in values) / max(1, len(values)))


class SpectralAudioIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lib = ROOT / "build/dsp-host.so"
        if not lib.exists():
            raise RuntimeError("Run tests/test_plugin.py to compile the host plugin first")
        loaded = C.CDLL(str(lib))
        loaded.move_plugin_init_v2.restype = C.POINTER(Plugin)
        loaded.move_plugin_init_v2.argtypes = [C.c_void_p]
        cls.api = loaded.move_plugin_init_v2(None).contents
        assert cls.api.api_version == 2

    def setp(self, handle, key, value):
        self.api.set(handle, key.encode(), str(value).encode())

    def getp(self, handle, key):
        buffer = C.create_string_buffer(8192)
        n = self.api.get(handle, key.encode(), buffer, 8192)
        self.assertGreaterEqual(n, 0, key)
        return buffer.value.decode()

    def render(self, handle, blocks):
        result = []
        buf = (C.c_int16 * 256)()
        for _ in range(blocks):
            self.api.render(handle, buf, 128)
            result.extend(buf[::2])
        return result

    def note(self, handle, number=60, velocity=110):
        data = (C.c_uint8 * 3)(0x90, number, velocity)
        self.api.midi(handle, data, 3, 0)

    def patch_audio(self, changes, note=60):
        synth = self.api.create(b".", None)
        self.assertTrue(synth)
        try:
            for k, v in {"attack":1, "decay":1, "sustain":100, "cutoff":100,
                         "resonance":0, "shape":50, "position":50,
                         "curated_osc1":8, "curated_osc2":8,
                         "osc1_volume":100, "osc2_volume":0}.items():
                self.setp(synth, k, v)
            for key, value in changes.items():
                self.setp(synth, key, value)
            self.render(synth, 100)  # depth and wavetable smoothing settle
            self.note(synth, note)
            audio = self.render(synth, 18)
            return audio[3 * 128:]
        finally:
            self.api.destroy(synth)

    def test_phase12c_velocity_shift_is_opt_in_and_voice_local(self):
        """Velocity changes spectral Shift only when the new control is enabled.
        The MIDI velocity amplifier still works normally when disabled."""
        def sound(velocity, intensity, oscillator):
            synth = self.api.create(b".", None)
            self.assertTrue(synth)
            try:
                for k, v in {"attack":1, "decay":1, "sustain":100,
                             "cutoff":100, "resonance":0, "shape":50,
                             "position":50, "curated_osc1":8,
                             "curated_osc2":8, "osc1_spectral_shift":50,
                             "osc2_spectral_shift":50, "osc1_volume":100 if oscillator==1 else 0,
                             "osc2_volume":100 if oscillator==2 else 0,
                             "vel_spec":intensity}.items():
                    self.setp(synth, k, v)
                self.render(synth, 100)
                self.note(synth, 60, velocity)
                return self.render(synth, 18)[3*128:]
            finally:
                self.api.destroy(synth)
        for osc in (1, 2):
            for velocity in (20, 64, 120):
                off = sound(velocity, 0, osc)
                default = sound(velocity, 0, osc)
                self.assertEqual(off, default)
                wet = sound(velocity, 100, osc)
                delta = rms([x-y for x, y in zip(off, wet)])
                if velocity == 64:
                    self.assertEqual(off, wet, "center velocity must be exact neutral")
                else:
                    self.assertGreater(delta, 20, (osc, velocity, delta))
            # Both ends must produce a different timbre, not just one-sided response.
            low = sound(20, 100, osc)
            high = sound(120, 100, osc)
            self.assertGreater(rms(low), 20)
            self.assertGreater(rms(high), 20)

    def test_phase12c_old_preset_resets_velocity_and_new_state_roundtrips(self):
        a = self.api.create(b".", None)
        b = self.api.create(b".", None)
        self.assertTrue(a and b)
        try:
            self.assertEqual(self.getp(a, "vel_spec"), "0")
            self.setp(a, "vel_spec", 73)
            state = self.getp(a, "state")
            self.assertIn("vel_spec=73", state)
            self.assertLess(len(state), 2048)
            self.api.set(b, b"state", state.encode())
            self.assertEqual(self.getp(b, "vel_spec"), "73")
            self.api.set(b, b"state", b"curated_osc1=8,osc1_spectral_shift=50,mx0_12=50")
            self.assertEqual(self.getp(b, "vel_spec"), "0")
            self.assertEqual(self.getp(b, "matrix_depth"), "50")
        finally:
            self.api.destroy(a)
            self.api.destroy(b)

    def test_phase12_spectral_routes_are_independent_and_audible(self):
        """Every added matrix route must change its own OSC and spectral
        effect under an LFO, without changing any neutral pre-Phase12 sound."""
        for oscillator in (1,2):
            for axis,base in enumerate(("shift","fold","scramble")):
                route=12+(oscillator-1)*3+axis
                patch={"curated_osc1":8,"curated_osc2":8,
                       "osc1_volume":100 if oscillator==1 else 0,
                       "osc2_volume":100 if oscillator==2 else 0,
                       "osc1_spectral_shift":35,"osc1_spectral_fold":35,
                       "osc1_spectral_scramble":35,
                       "osc2_spectral_shift":35,"osc2_spectral_fold":35,
                       "osc2_spectral_scramble":35,
                       "lfo1_waveform":0,"lfo_rate":80}
                baseline=self.patch_audio(patch)
                neutral=self.patch_audio({**patch,"matrix_source":0,
                                          "matrix_destination":route,
                                          "matrix_depth":50})
                self.assertEqual(baseline,neutral,
                    f"neutral route {route} must not change the Phase 10/11 sound")
                wet=self.patch_audio({**patch,"matrix_source":0,
                                      "matrix_destination":route,
                                      "matrix_depth":100})
                change=rms([a-b for a,b in zip(baseline,wet)])
                self.assertGreater(change,max(20,.04*rms(baseline)),
                    ("spectral route inaudible",oscillator,base,route,change))

    def test_phase12_matrix_state_roundtrip_and_old_state_neutrality(self):
        synth=self.api.create(b".",None)
        other=self.api.create(b".",None)
        self.assertTrue(synth and other)
        try:
            self.setp(synth,"matrix_source",0)
            self.setp(synth,"matrix_destination",12)
            self.setp(synth,"matrix_depth",81)
            self.setp(synth,"matrix_source",1)
            self.setp(synth,"matrix_destination",17)
            self.setp(synth,"matrix_depth",14)
            state=self.getp(synth,"state")
            self.assertIn("mx0_12=81",state)
            self.assertIn("mx1_17=14",state)
            self.assertLess(len(state),2048)
            self.api.set(other,b"state",state.encode())
            restored=self.getp(other,"state")
            self.assertEqual(restored,state)
            # Simulate loading a Phase 10/11 preset after editing Phase 12:
            # neither new route is serialized, so both must reset to neutral.
            old="curated_osc1=8,osc1_spectral_shift=50,level=70,mx0_0=75"
            self.api.set(other,b"state",old.encode())
            for source,route in ((0,12),(1,17)):
                self.setp(other,"matrix_source",source)
                self.setp(other,"matrix_destination",route)
                self.assertEqual(self.getp(other,"matrix_depth"),"50")
            self.setp(other,"matrix_source",0)
            self.setp(other,"matrix_destination",0)
            self.assertEqual(self.getp(other,"matrix_depth"),"75")
        finally:
            self.api.destroy(synth)
            self.api.destroy(other)

    def test_phase12_lfo2_stepped_and_smooth_spectral_motion(self):
        patch={"curated_osc1":8,"osc1_volume":100,"osc2_volume":0,
               "osc1_spectral_shift":50,"osc1_spectral_fold":0,
               "osc1_spectral_scramble":0,
               "matrix_source":1,"matrix_destination":12,"matrix_depth":100,
               "lfo2_sync":2,"sync_bpm":120,"lfo2_rate":35}
        neutral=self.patch_audio({**patch,"matrix_depth":50})
        for waveform in (0,3,4,5):  # sine, square, sample/hold, smooth
            sound=self.patch_audio({**patch,"lfo2_waveform":waveform})
            difference=rms([a-b for a,b in zip(neutral,sound)])
            self.assertGreater(difference,20,(waveform,difference))
            self.assertGreater(rms(sound),50)

    def test_shift_fold_scramble_and_compound_are_audible(self):
        dry = self.patch_audio({})
        self.assertGreater(rms(dry), 100)
        shift = self.patch_audio({"osc1_spectral_shift":100})
        fold = self.patch_audio({"osc1_spectral_fold":100})
        scramble = self.patch_audio({"osc1_spectral_scramble":100})
        composed = self.patch_audio({"osc1_spectral_shift":100,
                                     "osc1_spectral_fold":100,
                                     "osc1_spectral_scramble":100})
        for name, audio in [("Shift",shift), ("Fold",fold),
                            ("Scramble",scramble), ("Compound",composed)]:
            self.assertGreater(rms([a-b for a,b in zip(dry,audio)]), 15,
                               name + " sounded identical to bypass")
        naive = [(a+b+c)/3 for a,b,c in zip(shift,fold,scramble)]
        self.assertGreater(rms([a-b for a,b in zip(composed,naive)]), 15)

    def test_muted_oscillator_cannot_change_other_oscillator(self):
        baseline = self.patch_audio({"osc2_volume":0})
        osc2_only_changes = self.patch_audio(
            {"osc2_volume":0, "osc2_spectral_shift":100,
             "osc2_spectral_fold":100, "osc2_spectral_scramble":100,
             "osc2_position":91, "curated_osc2":13})
        self.assertEqual(baseline,osc2_only_changes)
        baseline_osc2 = self.patch_audio({"osc1_volume":0,"osc2_volume":100})
        osc1_only_changes = self.patch_audio(
            {"osc1_volume":0, "osc2_volume":100,
             "osc1_spectral_shift":100, "osc1_spectral_fold":100,
             "osc1_spectral_scramble":100,"curated_osc1":10})
        self.assertEqual(baseline_osc2,osc1_only_changes)

    def test_legacy_state_resets_spectral_depth_and_full_state_roundtrips(self):
        synth = self.api.create(b".",None)
        self.assertTrue(synth)
        try:
            controls = ("osc1_spectral_shift", "osc1_spectral_fold",
                        "osc1_spectral_scramble", "osc2_spectral_shift",
                        "osc2_spectral_fold", "osc2_spectral_scramble")
            for i,key in enumerate(controls):
                self.setp(synth,key,10+i*10)
            state = self.getp(synth,"state")
            self.assertTrue(all(f"{key}={10+i*10}" in state for i,key in enumerate(controls)))
            self.api.set(synth,b"state",b"curated_osc1=8,curated_osc2=8,level=70")
            self.assertTrue(all(self.getp(synth,key)=="0" for key in controls))
            self.api.set(synth,b"state",state.encode())
            self.assertTrue(all(self.getp(synth,key)==str(10+i*10)
                                for i,key in enumerate(controls)))
        finally:
            self.api.destroy(synth)


    def test_eight_voice_inharmonic_curated_long_note(self):
        synth=self.api.create(b".",None)
        self.assertTrue(synth)
        try:
            for key,value in {"curated_osc1":13,"curated_osc2":16,
                              "osc1_volume":50,"osc2_volume":50,
                              "cutoff":90,"resonance":0,"drive":0,"level":40,
                              "attack":1,"sustain":95,"release":75}.items():
                self.setp(synth,key,value)
            self.render(synth,60)
            notes=(48,52,55,60,64,67,71,74)
            for note in notes:self.note(synth,note)
            self.assertEqual(self.getp(synth,"voice_activity"),"8")
            energy=0
            for tick in range(40):
                if tick%8==0:
                    self.setp(synth,"curated_osc1",9+(tick//8)%8)
                    self.setp(synth,"curated_osc2",16-(tick//8)%8)
                audio=self.render(synth,5)
                self.assertTrue(all(-32768<=v<=32767 for v in audio))
                energy+=sum(v*v for v in audio)
            self.assertGreater(energy,1000000)
            for note in notes:
                off=(C.c_uint8*3)(0x80,note,0)
                self.api.midi(synth,off,3,0)
            self.render(synth,300)
            self.assertEqual(self.getp(synth,"voice_activity"),"0")
        finally:
            self.api.destroy(synth)

    def test_curated_9_to_16_have_distinct_character_on_both_oscillators(self):
        # A changed wavetable index is not enough: output should not merely
        # reproduce the previous Metallic carrier at the same pitch.
        for osc in (1, 2):
            patch={"osc1_volume":100 if osc==1 else 0,
                   "osc2_volume":100 if osc==2 else 0,
                   "position":50,"osc2_position":50,
                   "cutoff":80, "resonance":0, "drive":0}
            metal=self.patch_audio({**patch,f"curated_osc{osc}":8},note=60)
            for index in range(9,17):
                other=self.patch_audio({**patch,f"curated_osc{osc}":index},note=60)
                diff=rms([a-b for a,b in zip(metal,other)])
                self.assertGreater(diff,max(80,.2*rms(metal)),
                    ("Curated indistinguishable from Metallic",osc,index,diff))
                self.assertGreater(rms(other),50,("curated sound silent",osc,index))

    def test_curated_color_is_independent_of_muted_oscillator(self):
        for solo in (1,2):
            change={"osc1_volume":100 if solo==1 else 0,
                    "osc2_volume":100 if solo==2 else 0,
                    f"curated_osc{solo}":13,
                    f"curated_osc{3-solo}":8}
            original=self.patch_audio(change)
            changed=self.patch_audio({**change,f"curated_osc{3-solo}":16})
            self.assertEqual(original,changed,
                "Curated color on a muted oscillator must not leak into audible sound")

    def test_eight_voice_dual_oscillator_rapid_depth_sweeps(self):
        synth = self.api.create(b".", None)
        self.assertTrue(synth)
        try:
            for key, value in {"curated_osc1":8, "curated_osc2":8,
                               "osc1_volume":50, "osc2_volume":50,
                               "cutoff":80, "level":35,
                               "attack":5, "decay":100, "sustain":85}.items():
                self.setp(synth, key, value)
            self.render(synth, 40)
            notes = (48, 52, 55, 60, 64, 67, 71, 74)
            for number in notes:
                self.note(synth, number)
            self.assertEqual(self.getp(synth, "voice_activity"), "8")
            energy = 0
            for step in range(16):
                for osc in (1, 2):
                    for axis, val in (("shift",step * 7 % 101),
                                      ("fold",100 - step * 6),
                                      ("scramble",(step * 23) % 101)):
                        self.setp(synth, f"osc{osc}_spectral_{axis}", val)
                samples = self.render(synth, 4)
                energy += sum(x*x for x in samples)
                self.assertTrue(all(-32768 <= sample <= 32767 for sample in samples))
            self.assertGreater(energy, 1000000)
            for number in notes:
                off = (C.c_uint8 * 3)(0x80, number, 0)
                self.api.midi(synth, off, 3, 0)
            self.render(synth, 200)
            self.assertEqual(self.getp(synth, "voice_activity"), "0")
        finally:
            self.api.destroy(synth)


    def test_curated_metallic_position_moves_both_oscillators_with_spectral_zero(self):
        for oscillator in (1, 2):
            params = {"curated_osc1":8, "curated_osc2":8,
                      "osc1_volume":100 if oscillator == 1 else 0,
                      "osc2_volume":100 if oscillator == 2 else 0}
            position = "position" if oscillator == 1 else "osc2_position"
            low = self.patch_audio({**params, position:0})
            mid = self.patch_audio({**params, position:50})
            high = self.patch_audio({**params, position:100})
            scale = max(rms(low), rms(mid), rms(high), 1)
            self.assertGreater(rms([a-b for a,b in zip(low,mid)])/scale, .2,
                               f"OSC{oscillator} POS 0->50 is weak")
            self.assertGreater(rms([a-b for a,b in zip(mid,high)])/scale, .2,
                               f"OSC{oscillator} POS 50->100 is weak")

    def test_curated_fold_is_audible_on_both_oscillators(self):
        for oscillator in (1, 2):
            settings = {"position":65, "osc2_position":65,
                        "curated_osc1":8, "curated_osc2":8,
                        "osc1_volume":100 if oscillator == 1 else 0,
                        "osc2_volume":100 if oscillator == 2 else 0}
            prefix = f"osc{oscillator}_spectral_fold"
            original = self.patch_audio(settings)
            folded = self.patch_audio({**settings, prefix:100})
            scale = max(1, rms(original), rms(folded))
            self.assertGreater(rms([a-b for a,b in zip(original,folded)])/scale,
                               .2, f"OSC{oscillator} Fold made no meaningful difference")

    def test_spectral_effects_are_audible_on_regular_wavetables(self):
        """Regression for the Move report: Shift/Fold/Scramble stopped working
        after adjusting Wavetable on either oscillator."""
        for osc in (1, 2):
            for wave in (0, 37, 106):
                base = {"curated_osc1":0, "curated_osc2":0,
                        "osc1_volume":100 if osc == 1 else 0,
                        "osc2_volume":100 if osc == 2 else 0,
                        "wavetable":wave, "osc2_wavetable":wave,
                        "position":50, "osc2_position":50}
                dry = self.patch_audio(base)
                self.assertGreater(rms(dry), 50, ("silent baseline", osc, wave))
                for effect in ("shift", "fold", "scramble"):
                    wet = self.patch_audio({**base, f"osc{osc}_spectral_{effect}":100})
                    diff = rms([a - b for a, b in zip(dry, wet)])
                    # Absolute and normalized thresholds catch barely visible
                    # waveform differences as well as silent controls.
                    self.assertGreater(diff, max(35, .08 * rms(dry)),
                        (osc, wave, effect, "effect sounds identical", diff))

    def test_legacy_wavetable_selection_switches_active_source(self):
        synth = self.api.create(b".",None)
        self.assertTrue(synth)
        try:
            for oscillator in (1, 2):
                curated=f"curated_osc{oscillator}"
                legacy="wavetable" if oscillator==1 else "osc2_wavetable"
                snapshot_idx=0 if oscillator==1 else 7
                self.setp(synth, curated,8)
                self.assertEqual(int(self.getp(synth,"face_snapshot").split(",")[snapshot_idx]),115)
                self.setp(synth,legacy,27)
                # The active bank switches to Wavetable, but the curated
                # index is remembered rather than being wiped to zero.
                self.assertEqual(self.getp(synth,curated),"8")
                self.assertEqual(self.getp(synth,f"osc{oscillator}_source_curated"),"0")
                self.assertEqual(int(self.getp(synth,"face_snapshot").split(",")[snapshot_idx]),27)
                state=self.getp(synth,"state")
                self.api.set(synth,b"state",state.encode())
                self.assertEqual(self.getp(synth,curated),"8")
                self.assertEqual(self.getp(synth,f"osc{oscillator}_source_curated"),"0")
                self.assertEqual(int(self.getp(synth,"face_snapshot").split(",")[snapshot_idx]),27)
                self.setp(synth,curated,9)
                self.assertEqual(self.getp(synth,f"osc{oscillator}_source_curated"),"1")
                self.assertEqual(int(self.getp(synth,"face_snapshot").split(",")[snapshot_idx]),116)
        finally:
            self.api.destroy(synth)


if __name__ == "__main__":
    unittest.main()
