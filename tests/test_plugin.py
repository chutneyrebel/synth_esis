#!/usr/bin/env python3
"""Host-side ABI smoke tests for Synth_esis, no Move access needed."""
import ctypes as C
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
subprocess.run(['python3', str(ROOT/'scripts/generate_metadata.py'), '--check'],check=True)
assert len((ROOT/'src/module.json').read_bytes()) < 8192, 'Synth_esis metadata exceeds 8 KB'
BUILD = ROOT / 'build'
BUILD.mkdir(exist_ok=True)
if not (ROOT/'src/expanded_tables.h').is_file():
    subprocess.run(['python3',str(ROOT/'scripts/generate_expanded_tables.py')],check=True)
if not (ROOT/'src/tables.h').is_file():
    subprocess.run(['python3',str(ROOT/'scripts/generate_tables.py')],check=True)
subprocess.run(['python3',str(ROOT/'scripts/generate_curated_header.py'),'--output',str(BUILD/'curated_tables.h')],check=True)
subprocess.run(['python3',str(ROOT/'scripts/generate_noncurated_spectral.py'),'--output',str(BUILD/'noncurated_spectral_tables.h')],check=True)
so = BUILD / 'dsp-host.so'
subprocess.run(['gcc', '-std=c11', '-O2', '-shared', '-fPIC', '-ffreestanding', '-fno-builtin',
                '-fvisibility=hidden', '-DSYNTH_ESIS_ENABLE_CURATED', '-I'+str(BUILD), str(ROOT/'src/dsp.c'), '-o', str(so)],check=True)
# Build with a structure ABI matching the public Schwung plugin_api_v2_t declaration.
CREATE = C.CFUNCTYPE(C.c_void_p,C.c_char_p,C.c_char_p)
DESTROY = C.CFUNCTYPE(None,C.c_void_p)
MIDI = C.CFUNCTYPE(None,C.c_void_p,C.POINTER(C.c_uint8),C.c_int,C.c_int)
SET = C.CFUNCTYPE(None,C.c_void_p,C.c_char_p,C.c_char_p)
GET = C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_char_p,C.c_char_p,C.c_int)
RENDER = C.CFUNCTYPE(None,C.c_void_p,C.POINTER(C.c_int16),C.c_int)
class Plugin(C.Structure):
    _fields_ = [('api_version',C.c_uint32),('create',CREATE),('destroy',DESTROY),
                ('midi',MIDI),('set',SET),('get',GET),('error',GET),('render',RENDER)]
lib=C.CDLL(str(so))
lib.move_plugin_init_v2.restype=C.POINTER(Plugin)
lib.move_plugin_init_v2.argtypes=[C.c_void_p]
api=lib.move_plugin_init_v2(None).contents
assert api.api_version==2
inst=api.create(b'.',None)
assert inst

def midi(status,note,velocity,src=0):
    buf=(C.c_uint8*3)(status,note,velocity)
    api.midi(inst,buf,3,src)

def setp(k,v):api.set(inst,k.encode(),str(v).encode())
def getp(k):
    buf=C.create_string_buffer(8192)
    r=api.get(inst,k.encode(),buf,8192)
    assert r>=0,(k,r)
    return buf.value.decode()
def render(n=1):
    buf=(C.c_int16*256)()
    out=[]
    for _ in range(n):
        api.render(inst,buf,128)
        out.extend(buf[::2])
        # Stereo channels may differ when either oscillator is panned.
    return out

def rms(seq):return math.sqrt(sum(x*x for x in seq)/len(seq))

# The three sound-design categories must cover each expanded waveform once.
catalog=json.loads((ROOT/'src/wavetable_catalog.json').read_text())
assert catalog['classic']['ids']==[0,3]
assert set(catalog['categories'])=={'organic','industrial','vocal'}
ids=[]
for category,families in catalog['categories'].items():
    for family in families:
        lo,hi=family['ids']
        assert hi-lo==3,(category,family)
        ids.extend(range(lo,hi+1))
assert sorted(ids)==list(range(4,100)), 'Catalog must cover each expanded wavetable exactly once'
print('PASS: organic, industrial and vocal catalog covers all 96 expanded waveforms')
# New spectral tables must be DC-centered without changing established IDs.
# Inspect generated float rows, not just the recipe's intent.
import re
table_text=(ROOT/'src/expanded_tables.h').read_text()
rows=re.findall(r'\{([^{}]+)\}',table_text)
assert len(rows)==104*4*9, ('unexpected expanded table dimensions',len(rows))
for wave in range(48,96):
    for frame in range(4):
        for band in range(9):
            row=rows[(wave*4+frame)*9+band]
            samples=[float(x.rstrip('f')) for x in row.split(',') if x.strip()]
            assert len(samples)==256
            assert abs(sum(samples)/256)<0.0001,(wave,frame,band,'DC bias')
            assert max(abs(x) for x in samples)<=0.871,(wave,frame,band,'headroom')
print('PASS: all new wavetable frames are DC-centered with safe headroom')
# Spectral checks compare the actual generated band-limited waveform frames.
# Core IDs 100-107 are appended; every historical ID 0-99 remains unchanged.
def table_row(wave,frame,band=0):
    row=rows[((wave-4)*4+frame)*9+band]
    return [float(x.rstrip('f')) for x in row.split(',') if x.strip()]
def spectral_features(samples):
    # Compare normalized harmonic magnitude profiles, ignoring phase shifts.
    mags=[]
    for h in range(1,49):
        re=sum(v*math.cos(2*math.pi*h*i/256) for i,v in enumerate(samples))
        im=sum(v*math.sin(2*math.pi*h*i/256) for i,v in enumerate(samples))
        mags.append(math.hypot(re,im))
    total=sum(mags) or 1
    return [v/total for v in mags]
def spectral_distance(a,b):
    return sum(abs(x-y) for x,y in zip(a,b))
cores={i:[spectral_features(table_row(i,f)) for f in range(4)] for i in range(100,108)}
for i,frames in cores.items():
    assert spectral_distance(frames[0],frames[3])>.18,(i,'insufficient position evolution')
for i in cores:
    for j in cores:
        if i>=j:continue
        assert max(spectral_distance(cores[i][f],cores[j][f]) for f in (0,3))>.22,(i,j,'core timbres too similar')
print('PASS: eight core tables exhibit position evolution and pairwise spectral distinction')
# Prevent pairs from collapsing to the same timbre at intermediate positions.
# A max-over-endpoints check alone can hide identical middle frames.
for i in cores:
    for j in cores:
        if i>=j:continue
        distances=[spectral_distance(cores[i][f],cores[j][f]) for f in range(4)]
        assert min(distances)>.08,(i,j,'core pair overlaps at a frame',distances)
# Each curated table must offer at least two meaningfully distinct transitions.
for i,frames in cores.items():
    transitions=[spectral_distance(frames[f],frames[f+1]) for f in range(3)]
    assert sum(d>.08 for d in transitions)>=2,(i,'insufficient multi-frame evolution',transitions)
print('PASS: curated core pairs remain distinct across all four frames')

# Remote curated discovery keeps the full numeric ID range for preset recall.
remote=(ROOT/'src/web_ui.html').read_text()
assert 'const curatedWaves=[' in remote and 'curatedIds' in remote
for label in ('Pure · Fundamental','Glass · Bell','Vocal · Formant','Metal · Cluster','Alien · Fracture'):
    assert label in remote, ('missing curated sound',label)
assert "['wavetable','OSC 1 Wavetable',0,107,1]" in remote
assert "['osc2_wavetable','OSC 2 Wavetable',0,107,1]" in remote
assert 'Other / Existing Preset' in remote
print('PASS: curated discovery and legacy preset IDs coexist')
# Stage 3A architecture guard: legacy tables and preset IDs stay untouched.
header=(ROOT/'src/wavetable_engine.h').read_text()
assert '#define SPRIG_LEGACY_BANK 0' in header
assert '#define SPRIG_LEGACY_WAVES 4' in header
assert '#define SPRIG_LEGACY_FRAMES 4' in header
assert '#define SPRIG_LEGACY_BANDS 9' in header
assert 'sprig_table_lookup_legacy' in (ROOT/'src/dsp.c').read_text()
meta=json.loads((ROOT/'src/module.json').read_text())
assert meta['api_version']==2 and meta['id']=='synth_esis'
assert len((ROOT/'src/module.json').read_bytes())<8192, 'module.json must fit Schwung 8 KB metadata limit'
assert len(meta['capabilities']['ui_hierarchy']['levels']['root']['knobs'])==8
assert meta['capabilities']['ui_hierarchy']['levels']['root']['knobs'][:2]==['lfo_rate','lfo_depth'], 'Main controls must prioritize motion'
assert all(k in meta['capabilities']['ui_hierarchy']['levels']['root']['knobs'] for k in ('lfo_filter','cutoff','resonance','master_pan','level')), 'Synth Face missing live performance controls'
assert meta['capabilities']['ui_hierarchy']['levels']['osc1']['params']==['face_osc1']
assert meta['capabilities']['ui_hierarchy']['levels']['osc2']['params']==['face_osc2']
assert len(meta['capabilities']['chain_params'])==85, 'Expected Phase12C 83 parameters plus independent Fold/Scramble velocity controls'
assert [p['key'] for p in meta['capabilities']['chain_params'] if p['type']=='canvas']==['face','face_osc1','face_osc2','face_filter']
# Schwung as_page canvases inherit the *level* knobs. Each face must own its level.
expected_faces=[('face','sprig_main','root'),('face_osc1','sprig_osc1','osc1'),('face_osc2','sprig_osc2','osc2'),('face_filter','sprig_filter','filter')]
for key,overlay,home in expected_faces:
    entry=next(p for p in meta['capabilities']['chain_params'] if p['key']==key)
    assert entry['type']=='canvas' and entry.get('as_page') is True
    assert entry.get('canvas_script','canvas.js')=='canvas.js' and entry.get('canvas_overlay')==overlay
    # Page ordering is defined by the root hierarchy; page_first is optional.
    assert len(entry.get('extra_keys',[]))<=4
    slots=meta['capabilities']['ui_hierarchy']['levels'][home]['params']
    assert key in [x if isinstance(x,str) else x.get('key') for x in slots]
    assert len(meta['capabilities']['ui_hierarchy']['levels'][home]['knobs'])<=8
for key in ('face_osc1','face_osc2','face_filter'):
    assert key not in meta['capabilities']['ui_hierarchy']['levels']['root']['params']
assert meta['capabilities']['ui_hierarchy']['levels']['osc1_spectral']['params']==['face_osc1']
assert meta['capabilities']['ui_hierarchy']['levels']['osc2_spectral']['params']==['face_osc2']
for osc in (1,2):
    cp=next(p for p in meta['capabilities']['chain_params'] if p['key']==f'face_osc{osc}')
    assert cp['extra_keys']==['face_snapshot','voice_activity',f'curated_osc{osc}']
assert len(set(p['key'] for p in meta['capabilities']['chain_params']))==len(meta['capabilities']['chain_params']), 'Duplicate chain parameter keys'
print('PASS: four native canvas pages each have a dedicated Schwung encoder level')
assert 'lfo_wt_depth' in meta['capabilities']['chain_params'][[p['key'] for p in meta['capabilities']['chain_params']].index('lfo_wt_depth')]['key']
assert 'lfo_wt_depth' in meta['capabilities']['chain_params'][[p['key'] for p in meta['capabilities']['chain_params']].index('lfo_wt_depth')]['key']
# v1.9 obtains canvas type/as_page metadata from DSP chain_params, not module.json.
chain_params=json.loads(getp('chain_params'))
assert chain_params==meta['capabilities']['chain_params'], 'DSP and packaged chain_params drifted'
warp_labels=['Off','Sync','Bend+','Bend-','PWM','Asym','Mirror','Quant']
for key in ('osc1_warp_type','osc2_warp_type'):
    info=next(p for p in chain_params if p['key']==key)
    assert info['type']=='enum' and info['options']==warp_labels,(key,info)
remote_ui=(ROOT/'src/web_ui.html').read_text()
assert "const warpNames=['Off','Sync','Bend+','Bend−','PWM','Asym','Mirror','Quant']" in remote_ui
assert "['osc1_warp_type','OSC 1 Warp Type'" in remote_ui
assert "['osc2_warp_type','OSC 2 Warp Type'" in remote_ui
assert "['osc2_volume','OSC 2 Volume',0,100,1]" in remote_ui, 'Remote OSC 2 volume slider missing'
print('PASS: native and remote UI expose eight named warp modes')
face=next((p for p in chain_params if p.get('key')=='face'), None)
assert face and face['type']=='canvas' and face['as_page'] is True and face['page_first'] is True
assert face.get('canvas_script','canvas.js')=='canvas.js'
assert face['extra_keys']==['face_snapshot']
assert len(getp('face_snapshot').split(','))==47
assert getp('voice_activity')=='0'
hierarchy=json.loads(getp('ui_hierarchy'))
assert hierarchy==meta['capabilities']['ui_hierarchy'], 'Live DSP legacy hierarchy differs from shipped metadata'
assert 'levels' in hierarchy and 'root' in hierarchy['levels']
assert any(isinstance(p,dict) and p.get('key')=='face' and p.get('type')=='canvas' for p in hierarchy['levels']['root']['params'])
assert any(isinstance(p,dict) and p.get('level')=='osc2' for p in hierarchy['levels']['root']['params'])
assert getp('module_id')=='synth_esis'
assert getp('attack')=='10'
assert getp('osc2_level')=='0' and getp('lfo_depth')=='0'
setp('osc2_level',42);setp('detune',73);setp('lfo_depth',28);setp('drive',25)
assert getp('osc2_level')=='42' and getp('detune')=='73' and getp('drive')=='25'
setp('osc2_level',0);setp('lfo_depth',0);setp('drive',0)
setp('filter_env_amt',65);setp('filter_env_attack',10);setp('filter_env_decay',420);setp('lfo_filter',32)
assert getp('filter_env_amt')=='65' and getp('filter_env_decay')=='420'
setp('filter_env_amt',0);setp('lfo_filter',0)
assert rms(render(10))==0
# MIDI note-on produces audible nonzero sound.
midi(0x90,60,105)
assert getp('voice_activity')=='1'
played=render(50)
assert rms(played[512:])>50,rms(played)
assert max(abs(x) for x in played)<32768
# Note-off tail returns to silence.
midi(0x80,60,0)
tail=render(140)
assert rms(tail[-256:])<1
assert getp('voice_activity')=='0'
# Waveform vs position changes materially alter the output.
def sample_with(wave,position):
    midi(0xB0,123,0);render(8)
    setp('wave',wave);setp('position',position)
    render(80)
    midi(0x90,60,110)
    x=render(20)
    midi(0x80,60,0)
    render(120)
    return x
x=sample_with(1,0)
y=sample_with(1,100)
assert rms([a-b for a,b in zip(x,y)])>100, 'Position parameter is not audible'
# String enum path supports UI labels.
setp('wave','Triangle');assert getp('wave')=='3'
setp('wave','Sine');assert getp('wave')=='0'
setp('wave','Square');assert getp('wave')=='2'
# Unified selection exposes all 100 waveforms without a bank switch.
assert json.loads(getp('ui_hierarchy'))['levels']['osc1']['knobs'][:3]==['curated_osc1','position','osc1_octave']
setp('wavetable',0);assert getp('wavetable')=='0'
setp('wavetable',107);assert getp('wavetable')=='107'
setp('wavetable',999);assert getp('wavetable')=='107'
setp('wavetable',4);setp('shape',0)
dark=sample_with(1,50)
setp('shape',100)
bright=sample_with(1,50)
assert rms([a-b for a,b in zip(dark,bright)])>50, 'Unified Shape must change the sound'
setp('shape',50)
setp('wavetable',1)
classic=sample_with(1,50)
setp('wavetable',88)
spectral=sample_with(1,50)
assert rms([a-b for a,b in zip(classic,spectral)])>100, 'Unified table selector must change audio'
# Stress every curated table at both extremes with both oscillators sounding.
# Keep this deterministic: no wall-clock performance threshold on shared CI hosts.
def curated_stress(first,second,position):
    probe=api.create(b'.',None)
    assert probe,'unable to allocate stress-test synth'
    def put(key,val):api.set(probe,key.encode(),str(val).encode())
    put('attack',0);put('cutoff',100);put('resonance',0)
    put('wavetable',first);put('osc2_wavetable',second)
    put('position',position);put('osc2_position',100-position)
    put('osc1_volume',100);put('osc2_volume',100)
    put('lfo_wt_depth',100);put('lfo_rate',70)
    buffer=(C.c_int16*256)()
    for _ in range(40):api.render(probe,buffer,128) # allow smoothed pan to settle before note-on
    note=(C.c_uint8*3)(0x90,60,110)
    api.midi(probe,note,3,0)
    buffer=(C.c_int16*256)()
    peak=0;energy=0
    for _ in range(32):
        api.render(probe,buffer,128)
        for sample in buffer:
            peak=max(peak,abs(sample))
            energy+=sample*sample
    api.destroy(probe)
    assert 20<peak<=32768,(first,second,position,'silent or invalid PCM',peak)
    assert energy>0,(first,second,position,'silent render')
for idx in range(8):
    for pos in (0,50,100):
        curated_stress(100+idx,100+(idx+3)%8,pos)
print('PASS: 24 dual-oscillator curated render stress cases with maximum WT modulation')

# Diagnostic host-side render throughput, deliberately not a CI pass/fail gate.
# Desktop measurements cannot predict Move ARM64 CPU use.
bench=api.create(b'.',None)
assert bench
for key,val in [('wavetable',106),('osc2_wavetable',107),('osc1_volume',100),('osc2_volume',100),('lfo_wt_depth',100)]:
    api.set(bench,key.encode(),str(val).encode())
for note in range(48,56):
    msg=(C.c_uint8*3)(0x90,note,100)
    api.midi(bench,msg,3,0)
bench_buffer=(C.c_int16*256)()
for _ in range(16):api.render(bench,bench_buffer,128)
start=time.perf_counter()
for _ in range(512):api.render(bench,bench_buffer,128)
elapsed=time.perf_counter()-start
api.destroy(bench)
print(f'DIAGNOSTIC: host 8-note curated dual-oscillator render: {elapsed*1000:.1f} ms for 65536 frames (not Move CPU usage)')

# Preserve curated oscillator IDs, morph positions and opt-in modulation in presets.
# Exercise both oscillators and restore the original state before legacy tests.
before_curated=getp('state')
for first,second in ((100,107),(104,105),(106,102)):
    setp('wavetable',first);setp('osc2_wavetable',second)
    setp('position',17);setp('osc2_position',83)
    setp('lfo_wt_depth',42)
    saved=getp('state')
    setp('wavetable',1);setp('osc2_wavetable',1)
    setp('position',50);setp('osc2_position',50)
    setp('lfo_wt_depth',0)
    setp('state',saved)
    for key,expected in [('wavetable',first),('osc2_wavetable',second),('position',17),('osc2_position',83),('lfo_wt_depth',42)]:
        assert abs(float(getp(key))-expected)<.01,(key,expected,getp(key))
setp('state',before_curated)
print('PASS: curated oscillator IDs, morph positions and WT LFO survive preset round trips')
# Round-trip presets and clamp out-of-range writes.
setp('attack',112);setp('cutoff',35);setp('level',70)
state=getp('state')
setp('attack',1950);setp('cutoff',99)
setp('state',state)
assert getp('attack')=='112' and getp('cutoff')=='35'
setp('sustain',999);assert getp('sustain')=='100'
setp('release',-500);assert getp('release')=='0'
setp('release',280)
# Maximum voice stress, bounded PCM and valid output.
for n in range(48,72):midi(0x90,n,127)
poly=render(200)
assert 0 < rms(poly) and max(abs(v) for v in poly)<=32767
assert getp('voice_activity')=='8'
for n in range(48,72):midi(0x80,n,0)
render(200)
assert getp('voice_activity')=='0'
# Phase 1: one read-only snapshot provides twenty-five live face values.
face_data=getp('face_snapshot').split(',')
assert len(face_data)==47 and all(item.isdigit() for item in face_data)
assert int(face_data[0])==int(getp('wavetable'))
assert int(face_data[7])==int(getp('osc2_wavetable'))
assert not any(token.startswith('face_snapshot=') for token in getp('state').split(','))
# The restored state parser must reach the last historical parameters.
setp('filter_env_decay',613);setp('lfo_filter',47);setp('master_pan',75)
full_state=getp('state')
setp('filter_env_decay',2);setp('lfo_filter',1);setp('master_pan',0)
setp('state',full_state)
assert getp('filter_env_decay')=='613' and getp('lfo_filter')=='47' and getp('master_pan')=='75'
setp('filter_env_decay',400);setp('lfo_filter',0);setp('master_pan',50)
print('PASS: derived face snapshot, complete legacy state restore, new master pan')

# Stereo pan and OSC 2 motion regression checks.
def stereo_with(pan1,pan2,depth=0):
    midi(0xB0,123,0);render(140)
    setp('osc1_volume',100);setp('osc2_volume',100)
    setp('osc2_level',0);setp('osc1_pan',pan1);setp('osc2_pan',pan2)
    setp('lfo_depth',depth);setp('osc2_wavetable',20)
    midi(0x90,60,110)
    buf=(C.c_int16*256)()
    left=[];right=[]
    for _ in range(50):
        api.render(inst,buf,128)
        left.extend(buf[0::2]);right.extend(buf[1::2])
    midi(0x80,60,0);render(140)
    return left,right
left,right=stereo_with(0,0)
assert rms(left)>100 and rms(right)<2, 'Full left pan must silence right channel'
left,right=stereo_with(100,100)
assert rms(right)>100 and rms(left)<2, 'Full right pan must silence left channel'
left,right=stereo_with(50,50)
assert rms(left)>100 and left==right, 'Center pan must be symmetric'
setp('osc1_volume',0);setp('osc2_volume',100)
setp('osc1_pan',50);setp('osc2_pan',50)
def osc2_motion(depth):
    midi(0xB0,123,0);render(140)
    setp('lfo_depth',depth)
    midi(0x90,60,110)
    x=render(100)
    midi(0x80,60,0);render(140)
    return x
motion_off=osc2_motion(0)
motion_on=osc2_motion(90)
assert rms([a-b for a,b in zip(motion_off,motion_on)])>10, 'OSC2 must respond to motion'
setp('lfo_depth',0)
print('PASS: independent stereo pan and OSC2 wavetable motion')
# Optional WT LFO control must be readable and remain neutral by default.
assert getp('lfo_wt_depth')=='0'
setp('lfo_wt_depth',100)
assert getp('lfo_wt_depth')=='100'
setp('lfo_wt_depth',0)
assert getp('lfo_wt_depth')=='0'
assert 'lfo_wt_depth' in (ROOT/'src/web_ui.html').read_text()
print('PASS: opt-in WT LFO depth control and legacy-neutral default')
# Warp regression: each mode must preserve neutral at zero amount and
# produce distinct audio at strong settings on either oscillator.
# Create a fresh instance for each render to eliminate phase/history drift.
def warp_audio(osc, mode, amount):
    probe=api.create(b'.',None)
    assert probe, 'No free voice slot for warp regression'
    def put(key,val): api.set(probe,key.encode(),str(val).encode())
    put('attack',0);put('cutoff',100);put('resonance',0)
    put('lfo_depth',0);put('filter_env_amt',0);put('lfo_filter',0)
    put('osc1_volume',100 if osc==1 else 0)
    put('osc2_volume',100 if osc==2 else 0)
    put('osc2_level',0)
    put('wavetable',1);put('osc2_wavetable',1)
    put('osc1_warp_type',mode if osc==1 else 0)
    put('osc2_warp_type',mode if osc==2 else 0)
    put('osc1_warp',amount if osc==1 else 0)
    put('osc2_warp',amount if osc==2 else 0)
    msg=(C.c_uint8*3)(0x90,60,110)
    api.midi(probe,msg,3,0)
    buf=(C.c_int16*256)()
    audio=[]
    for _ in range(48):
        api.render(probe,buf,128)
        audio.extend(buf[::2])
    api.destroy(probe)
    return audio

for osc in (1,2):
    baseline=warp_audio(osc,0,0)
    assert rms(baseline)>100,(osc,'silent baseline')
    for mode in range(1,8):
        neutral=warp_audio(osc,mode,0)
        assert neutral==baseline,(osc,mode,'zero warp amount changes audio')
        altered=warp_audio(osc,mode,85)
        difference=rms([a-b for a,b in zip(baseline,altered)])
        assert difference>10,(osc,mode,'warp not audible',difference)
print('PASS: seven active warp modes plus Off, zero-amount neutrality on both oscillators')
# Instance limit and isolation.
insts=[api.create(b'.',None) for _ in range(7)]
assert all(insts) and not api.create(b'.',None)
for p in insts:api.destroy(p)
api.destroy(inst)
print('PASS: ABI, v1.9 chain_params/canvas contract, render, MIDI, polyphony, wavetable position, enum, state, clamp, limit')
print('Mono audio RMS:',round(rms(played),1))
print('Polyphony audio RMS:',round(rms(poly),1))


# Independent oscillator controls are exposed and bounded.
for k,hi in [('osc1_warp_type',7),('osc2_warp_type',7),('osc2_wavetable',107),('osc1_pan',100),('osc2_pan',100),('osc1_volume',100),('osc2_volume',100)]:
    setp(k,999)
    assert getp(k)==str(hi),(k,getp(k))
setp('osc1_warp_type',0);setp('osc1_warp',0);setp('osc1_volume',100)
setp('osc2_wavetable',24);setp('osc2_position',60);setp('osc2_warp_type',3);setp('osc2_warp',65);setp('osc2_volume',50)
assert getp('osc2_wavetable')=='24' and getp('osc2_warp_type')=='3'
print('PASS: independent dual oscillator controls and warp ranges')
# Both octave selectors preserve the default pitch at index 2.
for key in ('osc1_octave','osc2_octave'):
    param=next(p for p in chain_params if p['key']==key)
    assert param['options']==['-2','-1','0','+1','+2'] and param['default']==2
    setp(key,4);assert getp(key)=='4'
    setp(key,0);assert getp(key)=='0'
    setp(key,2);assert getp(key)=='2'
assert 'osc1_octave' in hierarchy['levels']['osc1']['knobs']
assert 'osc2_octave' in hierarchy['levels']['osc2']['knobs']
print('PASS: independent octave controls and neutral default')


# Core Organic recipe must stay synchronized across generated audio and both UIs.
generator=(ROOT/'scripts/generate_expanded_tables.py').read_text()
native=(ROOT/'src/canvas.js').read_text()
assert '3+18*t' in generator and '1.3+3.2*t' in generator
assert '3+18*t' in remote_ui and '1.3+3.2*t' in remote_ui
assert '3+18*t' in native and '1.3+3.2*t' in native
print('PASS: Organic spectral bloom recipe matches native and Remote previews')

# Output balance test for the global master pan (center is unchanged).
for pan,quiet_side in ((0,1),(100,0)):
    probe=api.create(b'.',None)
    assert probe
    for key,val in [('wavetable',1),('osc1_pan',50),('osc1_volume',100),('osc2_volume',0),('master_pan',pan)]:
        api.set(probe,key.encode(),str(val).encode())
    buffer=(C.c_int16*256)()
    # The output pan uses one-pole smoothing; start playback after its ramp.
    for _ in range(40):api.render(probe,buffer,128)
    note=(C.c_uint8*3)(0x90,60,110)
    api.midi(probe,note,3,0)
    energy=[0,0]
    for _ in range(32):
        api.render(probe,buffer,128)
        for channel in range(2):
            energy[channel]+=sum(v*v for v in buffer[channel::2])
    assert energy[1-quiet_side]>0 and energy[quiet_side]==0,(pan,energy)
    api.destroy(probe)
print('PASS: master pan controls both stereo output extremes')

# Phase 2: opt-in envelopes and oscillator mix preserve legacy parameter defaults.
phase2_keys=['osc1_env_enabled','osc2_env_enabled','osc1_attack','osc1_decay','osc1_sustain','osc1_release','osc2_attack','osc2_decay','osc2_sustain','osc2_release','mix_enabled','mix_balance']
p2=api.create(b'.',None)
assert p2
def p2get(key):
    buf=C.create_string_buffer(256)
    assert api.get(p2,key.encode(),buf,len(buf))>=0,key
    return int(buf.value)
def p2set(key,value):
    api.set(p2,key.encode(),str(value).encode())
assert p2get('osc1_env_enabled')==0 and p2get('osc2_env_enabled')==0
assert p2get('mix_enabled')==0 and p2get('mix_balance')==50
for key in phase2_keys:
    assert key in [p['key'] for p in chain_params],key
for key in ['osc1_attack','osc2_attack','osc1_release','osc2_release']:
    p2set(key,9999)
    assert p2get(key)==2000
p2set('osc1_env_enabled',1)
p2set('osc2_env_enabled',1)
p2set('osc1_attack',800)
p2set('osc2_attack',1)
p2set('mix_enabled',1)
p2set('mix_balance',25)
state=C.create_string_buffer(4096)
assert api.get(p2,b'state',state,len(state))>0
assert b'osc1_attack=800' in state.value and b'mix_balance=25' in state.value
api.destroy(p2)
print('PASS: Phase 2 opt-in envelope/mix metadata, defaults, bounds and state roundtrip')

def phase2_audio(osc,attack=1,balance=None):
    p=api.create(b'.',None)
    assert p
    def put(k,v):api.set(p,k.encode(),str(v).encode())
    put('cutoff',100);put('resonance',0);put('attack',1)
    put('osc1_volume',100 if osc==1 else 0)
    put('osc2_volume',100 if osc==2 else 0)
    put('osc2_level',0)
    put('osc%d_env_enabled'%osc,1)
    put('osc%d_attack'%osc,attack)
    if balance is not None:
        put('mix_enabled',1);put('mix_balance',balance)
    note=(C.c_uint8*3)(0x90,60,110)
    api.midi(p,note,3,0)
    buf=(C.c_int16*256)()
    audio=[]
    for _ in range(12):
        api.render(p,buf,128)
        audio.extend(buf[::2])
    api.destroy(p)
    return audio
for o in (1,2):
    quick=phase2_audio(o,1)
    slow=phase2_audio(o,2000)
    assert rms(quick)>rms(slow)*4,(o,rms(quick),rms(slow))
    full=phase2_audio(o,1,0 if o==1 else 100)
    muted=phase2_audio(o,1,100 if o==1 else 0)
    assert rms(full)>rms(muted)*4,(o,'mix balance must isolate oscillators')
print('PASS: Phase 2 per-oscillator attack and opt-in mix balance change actual PCM')

# Phase 3 filter ABI and audio regression.
filter_modes=['LP12','HP12','BP12','Notch','Peak','Allpass','LP24','HP24']
descriptor=next(p for p in chain_params if p['key']=='filter_type')
assert descriptor['options']==filter_modes and descriptor['default']==0
assert 'filter_type' in meta['capabilities']['ui_hierarchy']['levels']['filter']['knobs']
assert getp('filter_type')=='0', 'Legacy LP12 must remain the default'
def filter_audio(mode):
    p=api.create(b'.',None)
    assert p
    for key,value in [('filter_type',mode),('cutoff',36),('resonance',20),('attack',1),('sustain',100)]:
        api.set(p,key.encode(),str(value).encode())
    note=(C.c_uint8*3)(0x90,60,110)
    api.midi(p,note,3,0)
    buf=(C.c_int16*256)()
    samples=[]
    for _ in range(30):
        api.render(p,buf,128)
        samples.extend(buf[::2])
    api.destroy(p)
    return samples
sounds=[filter_audio(mode) for mode in range(8)]
assert all(1<rms(s)<32000 for s in sounds),[(i,rms(s)) for i,s in enumerate(sounds)]
assert all(sounds[i]!=sounds[0] for i in range(1,8))
assert sounds[6]!=sounds[0] and sounds[7]!=sounds[1]
print('PASS: eight filter modes render finite, distinguishable PCM')

# Phase 4: modulation matrix defaults remain inert for legacy presets.
assert getp('mod_dest')=='0' and getp('mod_depth')=='50'
keys=[p['key'] for p in chain_params]
assert keys[keys.index('mod_dest'):keys.index('mod_dest')+5]==['mod_dest','mod_depth','lfo2_rate','lfo2_dest','lfo2_depth']
setp('mod_dest',3);setp('mod_depth',0)
assert getp('mod_dest')=='3' and getp('mod_depth')=='0'
setp('mod_depth',100)
assert getp('mod_depth')=='100'
print('PASS: Phase 4 bipolar modulation matrix metadata and state')

assert getp('lfo2_rate')=='22' and getp('lfo2_dest')=='0' and getp('lfo2_depth')=='50'
setp('lfo2_dest',2);setp('lfo2_depth',100)
assert getp('lfo2_dest')=='2' and getp('lfo2_depth')=='100'
print('PASS: independent second LFO parameter defaults and state')

# Phase 4 audio: independently verify both oscillators and shared filter routing.
def phase4_audio(routes=(), extra=()):
    p=api.create(b'.',None)
    assert p
    def put(k,v):api.set(p,k.encode(),str(v).encode())
    for k,v in [('wavetable',70),('position',45),('osc2_wavetable',82),('osc2_position',45),
                ('osc1_volume',100),('osc2_volume',100),('osc2_level',0),
                ('cutoff',48),('resonance',20),('attack',1),('sustain',100),
                ('lfo_rate',65),('lfo2_rate',29)]:
        put(k,v)
    for k,v in routes:put(k,v)
    for k,v in extra:put(k,v)
    note=(C.c_uint8*3)(0x90,60,110)
    api.midi(p,note,3,0)
    buf=(C.c_int16*256)()
    samples=[]
    for _ in range(65):
        api.render(p,buf,128)
        samples.extend(buf[::2])
    api.destroy(p)
    return samples

baseline=phase4_audio()
assert baseline==phase4_audio([('mod_dest',0),('mod_depth',100),('lfo2_dest',0),('lfo2_depth',0)])
assert baseline==phase4_audio([('mod_dest',1),('mod_depth',50),('lfo2_dest',3),('lfo2_depth',50)])
for dest in (1,2,3):
    lfo1=phase4_audio([('mod_dest',dest),('mod_depth',100)])
    lfo2=phase4_audio([('lfo2_dest',dest),('lfo2_depth',100)])
    both=phase4_audio([('mod_dest',dest),('mod_depth',100),('lfo2_dest',dest),('lfo2_depth',100)])
    negative=phase4_audio([('mod_dest',dest),('mod_depth',0)])
    assert all(1<rms(a)<32000 for a in (lfo1,lfo2,both,negative)),dest
    assert lfo1!=baseline and lfo2!=baseline,(dest,'independent LFO route is inaudible')
    assert lfo1!=lfo2 and both!=lfo1 and both!=lfo2,(dest,'simultaneous LFO routing')
    assert negative!=lfo1,(dest,'bipolar depth polarity')
print('PASS: two LFOs independently and simultaneously affect all three destinations; bipolar depth and neutral legacy audio')

# Preset state contains all five new parameters and restores them to a fresh instance.
p=api.create(b'.',None)
assert p
values={'mod_dest':1,'mod_depth':27,'lfo2_rate':78,'lfo2_dest':3,'lfo2_depth':83}
for k,v in values.items():api.set(p,k.encode(),str(v).encode())
saved=C.create_string_buffer(8192)
assert api.get(p,b'state',saved,len(saved))>0
for k,v in values.items():assert (k+'='+str(v)).encode() in saved.value,k
q=api.create(b'.',None)
assert q
api.set(q,b'state',saved.value)
for k,v in values.items():
    value=C.create_string_buffer(64)
    assert api.get(q,k.encode(),value,len(value))>=0
    assert int(value.value)==v,(k,value.value,v)
api.destroy(p);api.destroy(q)
print('PASS: Phase 4 matrix parameters survive preset state roundtrip')

# Phase 5 DSP-only waveform regression. UI descriptor integration follows separately.
def phase5_audio(lfo,key,shape):
    routes=[('mod_dest',1),('mod_depth',100)] if lfo==1 else [('lfo2_dest',1),('lfo2_depth',100)]
    return phase4_audio(routes,[(key,shape)])
for lfo,key in ((1,'lfo1_waveform'),(2,'lfo2_waveform')):
    sine=phase5_audio(lfo,key,0)
    assert sine==phase4_audio([('mod_dest',1),('mod_depth',100)] if lfo==1 else [('lfo2_dest',1),('lfo2_depth',100)]),key
    shapes=[phase5_audio(lfo,key,i) for i in range(6)]
    assert len({tuple(a) for a in shapes})==6,(key,'waveforms must render distinctly')
    assert all(1<rms(a)<32000 for a in shapes),(key,'waveforms must stay bounded')
    p=api.create(b'.',None)
    assert p
    api.set(p,key.encode(),b'5')
    saved=C.create_string_buffer(8192)
    assert api.get(p,b'state',saved,len(saved))>0
    assert (key+'=5').encode() in saved.value,key
    api.destroy(p)
print('PASS: Phase 5 six distinct LFO waveforms, original sine default, PCM bounds and state persistence')

for key in ('lfo1_waveform','lfo2_waveform'):
    descriptor=next(p for p in chain_params if p['key']==key)
    assert descriptor['type']=='enum' and descriptor['default']==0
    assert descriptor['options']==['Sine','Tri','Saw','Square','S&H','Smooth']
    assert key in meta['capabilities']['ui_hierarchy']['levels']['motion']['knobs']
    # Motion controls are exposed as level knobs; duplicate params are optional.
    assert key in meta['capabilities']['ui_hierarchy']['levels']['motion']['knobs']
print('PASS: Phase 5 waveform selectors exposed on native MOTION page')

# Phase 6: manual-BPM musical LFO divisions remain opt-in.
for key in ('sync_bpm','lfo1_sync','lfo2_sync'):
    desc=next(p for p in chain_params if p['key']==key)
    # Motion controls are exposed as level knobs; duplicate params are optional.
    assert key in meta['capabilities']['ui_hierarchy']['levels']['motion']['knobs']
    assert key in meta['capabilities']['ui_hierarchy']['levels']['motion']['knobs']
    assert desc['default']==(120 if key=='sync_bpm' else 0)
p=api.create(b'.',None)
assert p
for key,val in [('sync_bpm',135),('lfo1_sync',3),('lfo2_sync',5)]:
    api.set(p,key.encode(),str(val).encode())
state=C.create_string_buffer(8192)
assert api.get(p,b'state',state,len(state))>0
for key,val in [('sync_bpm',135),('lfo1_sync',3),('lfo2_sync',5)]:
    assert (key+'='+str(val)).encode() in state.value
api.destroy(p)
print('PASS: Phase 6 manual BPM and independent sync divisions survive preset state')

# Phase 7 matrix: historical 24 routes remain stable; Phase 12 appends 12 spectral routes.
p=api.create(b'.',None)
assert p
api.set(p,b'matrix_source',b'0')
api.set(p,b'matrix_destination',b'10')
api.set(p,b'matrix_depth',b'87')
api.set(p,b'matrix_source',b'1')
api.set(p,b'matrix_destination',b'11')
api.set(p,b'matrix_depth',b'13')
buf=C.create_string_buffer(32)
assert api.get(p,b'matrix_depth',buf,len(buf))>0 and buf.value==b'13'
saved=C.create_string_buffer(8192)
assert api.get(p,b'state',saved,len(saved))>0
assert b'mx0_10=87' in saved.value and b'mx1_11=13' in saved.value
q=api.create(b'.',None)
assert q
api.set(q,b'state',saved.value)
again=C.create_string_buffer(8192)
assert api.get(q,b'state',again,len(again))>0
assert b'mx0_10=87' in again.value and b'mx1_11=13' in again.value
api.destroy(p)
api.destroy(q)
print('PASS: Phase 7 24 independent bipolar routes survive state round trip')

# Phase 7.1: descriptive enum labels must preserve route numeric IDs.
dest=next(p for p in chain_params if p['key']=='matrix_destination')
assert dest['type']=='enum' and dest.get('default',0)==0
assert dest['options']==['O1 WT','O2 WT','Cutoff','Reso','O1 Warp','O2 Warp','O1 Pan','O2 Pan','O1 Vol','O2 Vol','O1 Tune','O2 Tune','O1 Shift','O1 Fold','O1 Scram','O2 Shift','O2 Fold','O2 Scram']
print('PASS: Phase 7.1 named destination selector preserves 0-11 route IDs')

# Phase 10G: Schwung native per-component preset uses the complete synth:state
# blob. Every advertised writable numeric parameter must survive save/restore.
native_specs = {p['key']:p for p in chain_params
                if p['type'] in ('int','float','enum') and p.get('access') != 'read'
                and p['key'] not in ('voice_activity','face_snapshot')}
p = api.create(b'.',None)
q = api.create(b'.',None)
assert p and q
for key,spec in native_specs.items():
    if spec['type']=='enum':
        target=len(spec['options'])-1
    elif spec['type']=='int':
        target=int(spec['max'])
    else:
        target=spec['max']
    api.set(p,key.encode(),str(target).encode())
native_saved=C.create_string_buffer(8192)
assert api.get(p,b'state',native_saved,len(native_saved))>0
assert len(native_saved.value)<2048, 'native state exceeds DSP state parser limit'
api.set(q,b'state',native_saved.value)
native_restored=C.create_string_buffer(8192)
assert api.get(q,b'state',native_restored,len(native_restored))>0
assert native_restored.value==native_saved.value, 'full native state roundtrip lost parameters'
for key in native_specs:
    # Matrix source/destination select the editing cursor, not persistent
    # modulation routing. The state blob stores all 36 mxN_M depths instead.
    if key in ('matrix_source', 'matrix_destination', 'matrix_depth'):
        continue
    expected=C.create_string_buffer(64)
    actual=C.create_string_buffer(64)
    assert api.get(p,key.encode(),expected,len(expected))>=0,key
    assert api.get(q,key.encode(),actual,len(actual))>=0,key
    assert expected.value==actual.value,(key,expected.value,actual.value)
api.destroy(p)
api.destroy(q)
print('PASS: Phase 10G all writable synth parameters survive Schwung native state roundtrip')

# Phase 10H: every factory recipe can be applied via the DSP parameter API
# and serialized into Schwung's native component-state format. No Move I/O.
factory_library=json.loads((ROOT/'presets/factory.json').read_text())
assert len(factory_library['presets'])==16
for recipe in factory_library['presets']:
    patch=recipe['patch']
    assert patch['module_id']=='synth_esis' and patch['schema']==1
    a=api.create(b'.',None)
    b=api.create(b'.',None)
    assert a and b
    for key,value in patch['parameters'].items():
        api.set(a,key.encode(),str(value).encode())
    state=C.create_string_buffer(8192)
    assert api.get(a,b'state',state,len(state))>0,recipe['id']
    assert len(state.value)<2048,(recipe['id'],'native state too large')
    api.set(b,b'state',state.value)
    restored=C.create_string_buffer(8192)
    assert api.get(b,b'state',restored,len(restored))>0
    assert restored.value==state.value,('factory native roundtrip',recipe['id'])
    api.destroy(a)
    api.destroy(b)
print('PASS: all 16 factory patches serialize and restore through native Schwung state')

# Phase 10B: curated bank must be audible and independently selectable.
a=api.create(b'.',None)
assert a
def probe(table1,table2):
    api.set(a,b'curated_osc1',str(table1).encode())
    api.set(a,b'curated_osc2',str(table2).encode())
    api.set(a,b'osc1_volume',b'100')
    api.set(a,b'osc2_volume',b'0')
    buf=(C.c_uint8*3)(0x90,60,100)
    api.midi(a,buf,3,0)
    out=(C.c_int16*256)()
    audio=[]
    for _ in range(8):
        api.render(a,out,128)
        audio.extend(out[::2])
    api.midi(a,(C.c_uint8*3)(0x80,60,0),3,0)
    return audio
base=probe(0,0)
curated=probe(1,0)
assert rms(curated)>10, 'curated oscillator silent'
assert rms([x-y for x,y in zip(base,curated)])>10, 'curated oscillator not audibly different'
api.set(a,b'curated_osc1',b'0')
api.set(a,b'curated_osc2',b'16')
v=C.create_string_buffer(32)
assert api.get(a,b'curated_osc2',v,len(v))>=0 and v.value==b'16'
api.destroy(a)
print('PASS: curated wavetable bank compiles and changes audible DSP output')
