#!/usr/bin/env python3
"""Render reproducible Synth_esis Curated 8-16 A/B WAV previews from host DSP.

These are actual synthesized audio, NOT merely offline wavetable FFT charts.
All clips use identical filter/envelope/volume/position settings. Intended to
expose timbral similarity before another hardware-test round; not a substitute
for the Move's real-time CPU and speaker response.
"""
import argparse
import ctypes as C
from pathlib import Path
import wave

ROOT=Path(__file__).resolve().parents[1]
SR=44100
BLOCK=128
NAMES=("Metallic","Glass","Vocal","Organic","Resonant","Bell","Sweep","Fractal","Noise")
CREATE=C.CFUNCTYPE(C.c_void_p,C.c_char_p,C.c_char_p)
DESTROY=C.CFUNCTYPE(None,C.c_void_p)
MIDI=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(C.c_uint8),C.c_int,C.c_int)
SET=C.CFUNCTYPE(None,C.c_void_p,C.c_char_p,C.c_char_p)
GET=C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_char_p,C.c_char_p,C.c_int)
RENDER=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(C.c_int16),C.c_int)

class Plugin(C.Structure):
    _fields_=[("api_version",C.c_uint32),("create",CREATE),
              ("destroy",DESTROY),("midi",MIDI),("set",SET),
              ("get",GET),("error",GET),("render",RENDER)]

def produce(library,output_dir):
    library=Path(library)
    if not library.exists():
        raise FileNotFoundError("Host DSP must be compiled first: "+str(library))
    dsp=C.CDLL(str(library))
    dsp.move_plugin_init_v2.restype=C.POINTER(Plugin)
    dsp.move_plugin_init_v2.argtypes=[C.c_void_p]
    api=dsp.move_plugin_init_v2(None).contents
    if api.api_version!=2:
        raise ValueError("unsupported synth ABI")
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    for index,name in enumerate(NAMES,8):
        for note,notation in ((48,"C3"),(60,"C4")):
            synth=api.create(b".",None)
            if not synth:raise RuntimeError("Synth_esis DSP instance limit")
            try:
                for key,value in {"cutoff":100,"resonance":0,"drive":0,
                                  "level":50,"shape":50,
                                  "attack":1,"decay":1,"sustain":100,"release":80,
                                  "osc1_volume":100,"osc2_volume":0,
                                  "position":50,"curated_osc1":index,
                                  "osc1_spectral_shift":0,"osc1_spectral_fold":0,
                                  "osc1_spectral_scramble":0}.items():
                    api.set(synth,key.encode(),str(value).encode())
                # Allow smoothed parameters to reach their targets without
                # triggering notes or writing silence to the final clip.
                buffer=(C.c_int16*(BLOCK*2))()
                for _ in range(80):api.render(synth,buffer,BLOCK)
                on=(C.c_uint8*3)(0x90,note,110)
                api.midi(synth,on,3,0)
                filename=output_dir/f"C{index:02d}-{name}-{notation}.wav"
                with wave.open(str(filename),"wb") as output:
                    output.setnchannels(2)
                    output.setsampwidth(2)
                    output.setframerate(SR)
                    for _ in range(430):
                        api.render(synth,buffer,BLOCK)
                        output.writeframesraw(bytes(buffer))
                    off=(C.c_uint8*3)(0x80,note,0)
                    api.midi(synth,off,3,0)
                    for _ in range(35):
                        api.render(synth,buffer,BLOCK)
                        output.writeframesraw(bytes(buffer))
                if filename.stat().st_size<100000:
                    raise AssertionError("preview unexpectedly small: "+str(filename))
            finally:
                api.destroy(synth)
    return len(NAMES)*2

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--dsp",default=str(ROOT/"build/dsp-host.so"))
    parser.add_argument("--output-dir",required=True)
    args=parser.parse_args()
    print("Rendered",produce(args.dsp,args.output_dir),"actual DSP audio clips")
