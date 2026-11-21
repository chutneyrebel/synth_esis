#!/usr/bin/env python3
import json
import hashlib
import struct
import subprocess
import tarfile
from pathlib import Path
p=Path(__file__).resolve().parents[1]
archive=p/'dist/synth_esis-module.tar.gz'
assert archive.is_file()
meta=json.loads((p/'src/module.json').read_text())
assert meta['capabilities']['component_type']=='sound_generator'
assert meta['api_version']==2
assert len((p/'src/module.json').read_bytes()) < 8192
with tarfile.open(archive,'r:gz') as tar:
    names=tar.getnames()
    assert 'synth_esis/module.json' in names and 'synth_esis/dsp.so' in names and 'synth_esis/web_ui.html' in names and 'synth_esis/canvas.js' in names
    for member in tar.getmembers():
        assert member.name.startswith('synth_esis/') or member.name=='synth_esis', member.name
        assert member.isfile() or member.isdir(),member.name
    # Verify that the distributable contains exactly the intended runtime files,
    # and that every nonbinary asset matches the tested source byte-for-byte.
    expected={'dsp.so','module.json','web_ui.html','canvas.js','wavetable_catalog.json','assets/ui_reference.js'}
    actual={m.name.removeprefix('synth_esis/') for m in tar.getmembers() if m.isfile()}
    assert actual==expected,('unexpected or missing runtime assets',actual^expected)
    for asset in expected-{'dsp.so'}:
        packaged=tar.extractfile('synth_esis/'+asset).read()
        source=(p/'src'/asset).read_bytes()
        assert hashlib.sha256(packaged).digest()==hashlib.sha256(source).digest(),('stale packaged asset',asset)
    binary=tar.extractfile('synth_esis/dsp.so').read()
    assert hashlib.sha256(binary).digest()==hashlib.sha256((p/'build/dsp.so').read_bytes()).digest(),'packaged DSP differs from tested ARM64 build'
assert binary[:4]==b'\x7fELF'
assert binary[4]==2 and binary[5]==1
assert struct.unpack_from('<H',binary,18)[0]==183 # EM_AARCH64
symbol=subprocess.check_output(['nm','-D',str(p/'build/dsp.so')],text=True)
assert 'move_plugin_init_v2' in symbol
unresolved=subprocess.check_output(['readelf','-Ws',str(p/'build/dsp.so')],text=True)
assert not any(' UND ' in line and 'NOTYPE' not in line for line in unresolved.splitlines())
needed=subprocess.check_output(['readelf','-d',str(p/'build/dsp.so')],text=True)
assert 'NEEDED' not in needed
print('PASS: valid ARM64 ELF, exact ABI export, no external dynamic dependencies, archive layout and exact source asset integrity')
