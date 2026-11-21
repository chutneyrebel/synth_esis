// Host-side contract smoke test for Schwung's module-owned graphical page.
'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const code = fs.readFileSync('src/canvas.js', 'utf8');
const sandbox = {globalThis: {}};
vm.runInNewContext(code, sandbox, {timeout: 1000});
const overlay = sandbox.globalThis.canvas_overlay;
assert.equal(typeof overlay.drawPage, 'function');
let count = 0;
const ctx = {
  width: 128, height: 42,
  print(x,y,text,color) {
    assert(Number.isFinite(x) && Number.isFinite(y));
    assert(typeof text==='string');
    count++;
  },
  fillRect(x,y,w,h,color) {
    assert([x,y,w,h].every(Number.isFinite));
    assert(w>=0 && h>=0 && x>=0 && y>=0);
    count++;
  },
  line(x1,y1,x2,y2,color) {
    assert([x1,y1,x2,y2].every(Number.isFinite));
    count++;
  }
};
overlay.drawPage(ctx, {values:{wave:2,position:68,cutoff:30,lfo_depth:45,filter_env_amt:70,osc2_level:50}});
assert(count>25);
overlay.drawPage(ctx, {values:{}});
overlay.drawPage({ ...ctx, width: 25, height: 12 }, { values:{} });
// Modulation must visibly change the trace over time, while zero depth stays still.
function waveformLines(depth, nowMs, voices=0) {
  const lines=[];
  overlay.drawPage({...ctx, line(...args){lines.push(args);}}, {nowMs, values:{wave:1,position:50,cutoff:40,lfo_depth:depth,lfo_rate:25,voice_activity:voices}});
  return JSON.stringify(lines);
}
assert.equal(waveformLines(0,1000),waveformLines(0,1700));
assert.equal(waveformLines(80,1000,0),waveformLines(80,1700,0));
assert.notEqual(waveformLines(80,1000,1),waveformLines(80,1700,1));
console.log('PASS: idle waveform stable even at depth 80; sounding voices enable motion');
// Missing clock must not freeze a canvas on hosts without nowMs.
const withoutClockA=waveformLines(80,undefined,1);
let withoutClockB=withoutClockA;
for(let i=0;i<20;i++) withoutClockB=waveformLines(80,undefined,1);
assert.notEqual(withoutClockA,withoutClockB);
console.log('PASS: missing nowMs uses redraw-frame fallback');
// Schwung owns the parameter header. The canvas must never duplicate it.
const keys=['wave','position','osc2_level','detune','cutoff','resonance','lfo_depth','level'];
const vals={wave:2,position:63,osc2_level:41,detune:72,cutoff:30,resonance:25,lfo_depth:80,level:66};
for(let i=0;i<keys.length;i++){
  const printed=[];
  overlay.drawPage({...ctx,print(x,y,t,c){printed.push(t);}}, {keys,touched:i,values:vals,nowMs:1000});
  assert.deepEqual(printed,['1','2','R','D','F','P'],'canvas must not repeat host parameter header');
}
// The new root overlay uses the shared animated dual-oscillator renderer.
// Its secondary contour must be note-gated and respond to motion depth.
function ghostPixels(voices,depth,nowMs=1200){
 const pixels=[];
 overlay.drawPage({...ctx,fillRect(x,y,w,h,color){if(w===1&&h===1)pixels.push([x,y]);}},
  {nowMs,values:{wavetable:1,position:55,lfo_depth:depth,lfo_rate:30,voice_activity:voices}});
 return pixels;
}
assert.equal(ghostPixels(0,80).length,0);
assert.equal(ghostPixels(1,0).length,0);
assert(ghostPixels(1,80).length>15);
assert.notEqual(JSON.stringify(ghostPixels(1,80,1000)),JSON.stringify(ghostPixels(1,80,1800)));
console.log('PASS: root SYNTH face motion ghost is voice-gated and modulation-reactive');
console.log('PASS: no duplicate encoder feedback inside canvas');
console.log('PASS: canvas overlay loads and draws on the 128x64 hardware page contract');



function unifiedLines(table,shape=50){
 const lines=[];
 overlay.drawPage({...ctx,line(...args){lines.push(args);}}, {nowMs:1000,values:{wavetable:table,shape,position:50,voice_activity:0}});
 return JSON.stringify(lines);
}
assert.notEqual(unifiedLines(0),unifiedLines(4),'Classic and spectral waveforms differ');
assert.notEqual(unifiedLines(4),unifiedLines(40),'Spectral tables differ');
assert.notEqual(unifiedLines(40,0),unifiedLines(40,50),'Dark Shape changes waveform');
assert.notEqual(unifiedLines(40,50),unifiedLines(40,100),'Bright Shape changes waveform');
console.log('PASS: unified 52-table canvas and universal Shape');

const faces=sandbox.globalThis.sprig_faces;
assert.deepEqual(Object.keys(faces).sort(),['filter','main','osc1','osc2']);
for(const name of Object.keys(faces)){
  const lines=[];
  const labels=[];
  faces[name]({...ctx,line(...args){lines.push(args);},print(x,y,t){labels.push(t);}},{
    nowMs:1000,values:{wavetable:1,osc2_wavetable:24,position:30,osc2_position:80,cutoff:45,resonance:50,lfo_depth:60,voice_activity:1}
  });
  assert(lines.length>30, name+' face has no trace');
  assert.equal(labels.length,name==='main'?6:name==='filter'?4:5,name+' face needs four meters and oscillator source identifier');
}
const faceLines=(name)=>{const lines=[];faces[name]({...ctx,line(...args){lines.push(args);}},{
  nowMs:1000,values:{wavetable:1,osc2_wavetable:24,position:30,osc2_position:80,cutoff:45,resonance:50}
});return JSON.stringify(lines);};
assert.notEqual(faceLines('osc1'),faceLines('osc2'),'oscillator faces must be distinct');
assert.notEqual(faceLines('filter'),faceLines('osc1'),'filter must show response rather than oscillator wave');
console.log('PASS: four separate canvas face renderers produce distinct graphics');

// Regression: all curated core IDs must draw distinct physical Move traces.
function coreTrace(id, face='main') {
  const lines=[];
  const draw=face==='main'?overlay.drawPage:sandbox.globalThis.sprig_faces[face];
  draw({...ctx,line(...args){lines.push(args);}}, {nowMs:1000,values:{wavetable:id,osc2_wavetable:id,position:48,osc2_position:48,lfo_depth:0,voice_activity:0}});
  return JSON.stringify(lines);
}
const coreTraces=Array.from({length:8},(_,i)=>coreTrace(100+i));
assert.equal(new Set(coreTraces).size,8,'all eight core tables must have distinct native traces');
assert.notEqual(coreTrace(99),coreTrace(100),'ID 99 and core ID 100 must differ');
assert.notEqual(coreTrace(100,'osc1'),coreTrace(107,'osc1'));
console.log('PASS: native Move canvas renders all eight curated core wavetable IDs');

// Dedicated WT LFO must animate native waveforms independently of Motion Depth.
function wtLfoTrace(depth,nowMs,voices=1){
  const lines=[];
  overlay.drawPage({...ctx,line(...args){lines.push(args);}}, {
    nowMs,values:{wavetable:106,position:50,lfo_depth:0,lfo_wt_depth:depth,lfo_rate:15,voice_activity:voices}
  });
  return JSON.stringify(lines);
}
assert.notEqual(wtLfoTrace(0,1000),wtLfoTrace(0,1700),'held notes must animate even without LFO modulation');
assert.equal(wtLfoTrace(100,1000,0),wtLfoTrace(100,1700,0));
assert.notEqual(wtLfoTrace(100,1000),wtLfoTrace(100,1700));
console.log('PASS: dedicated WT LFO animates physical waveform only while sounding');

// All curated IDs must render on both oscillator faces across WT positions.
// This catches partial fixes where the main face works but OSC2 is still clamped.
for(const face of ['main','osc1','osc2']){
  for(const position of [0,33,67,100]){
    const traces=[];
    for(let id=100;id<=107;id++){
      const lines=[];
      const draw=face==='main'?overlay.drawPage:sandbox.globalThis.sprig_faces[face];
      draw({...ctx,line(...args){lines.push(args);}}, {
        nowMs:1000,values:{wavetable:id,osc2_wavetable:id,position,osc2_position:position,lfo_depth:0,lfo_wt_depth:0,voice_activity:0}
      });
      assert(lines.length>30,face+' failed to render '+id+' at '+position);
      traces.push(JSON.stringify(lines));
    }
    assert.equal(new Set(traces).size,8,face+' has indistinguishable curated traces at '+position);
  }
}
console.log('PASS: all eight curated waveforms render distinctly on main, OSC1 and OSC2 at four positions');

const named=sandbox.globalThis.canvas_overlays;
assert.deepEqual(Object.keys(named).sort(),['sprig_filter','sprig_main','sprig_osc1','sprig_osc2']);
for(const [name,entry] of Object.entries(named)){
  assert.equal(typeof entry.drawPage,'function',name+' must provide drawPage');
  const lines=[];
  entry.drawPage({...ctx,line(...args){lines.push(args);}}, {
    nowMs:1000,values:{wavetable:106,osc2_wavetable:107,position:60,osc2_position:40,voice_activity:0}
  });
  assert(lines.length>0,name+' must draw waveform or filter response');
}
console.log('PASS: four named native overlay entry points render without changing legacy overlay');


// Phase 1: the four named native pages consume the derived read-only DSP
// snapshot, rather than using more than four Schwung extra_keys.
const snapshotOrder=[
  'wavetable','position','osc1_warp_type','osc1_warp','osc1_detune',
  'osc1_pan','osc1_volume','osc2_wavetable','osc2_position','osc2_warp_type',
  'osc2_warp','osc2_detune','osc2_pan','osc2_volume','shape','lfo_rate',
  'lfo_depth','lfo_wt_depth','cutoff','resonance','drive','filter_env_amt',
  'lfo_filter','master_pan','filter_type','voice_activity',
  'matrix_cutoff_lfo1','matrix_cutoff_lfo2','lfo2_rate',
  'osc1_spectral_shift','osc1_spectral_fold','osc1_spectral_scramble',
  'osc2_spectral_shift','osc2_spectral_fold','osc2_spectral_scramble',
  'curated_osc1','curated_osc2','osc1_source_curated','osc2_source_curated',
  'raw_wavetable','raw_osc2_wavetable'
];
function snapshot(extra={}){
  const state={wavetable:1,position:50,osc1_warp_type:0,osc1_warp:0,
    osc1_detune:50,osc1_pan:50,osc1_volume:100,osc2_wavetable:1,
    osc2_position:50,osc2_warp_type:0,osc2_warp:0,osc2_detune:50,
    osc2_pan:50,osc2_volume:0,shape:50,lfo_rate:22,lfo_depth:0,
    lfo_wt_depth:0,cutoff:78,resonance:15,drive:0,filter_env_amt:0,
    lfo_filter:0,master_pan:50,filter_type:0,voice_activity:0,
    matrix_cutoff_lfo1:50,matrix_cutoff_lfo2:50,lfo2_rate:22,
    osc1_spectral_shift:0,osc1_spectral_fold:0,osc1_spectral_scramble:0,
    osc2_spectral_shift:0,osc2_spectral_fold:0,osc2_spectral_scramble:0,...extra};
  for(const [id, legacy] of [['1','wavetable'],['2','osc2_wavetable']]){
    const curated='curated_osc'+id, mode='osc'+id+'_source_curated', raw=id==='1'?'raw_wavetable':'raw_osc2_wavetable';
    if(extra[curated]===undefined)state[curated]=Math.max(0,state[legacy]-107);
    if(extra[mode]===undefined)state[mode]=state[legacy]>107?1:0;
    if(extra[raw]===undefined)state[raw]=Math.min(107,state[legacy]);
  }
  return snapshotOrder.map(k=>state[k]).join(',');
}
function nativeLines(face,extra={},nowMs=1000){
  const lines=[];
  named['sprig_'+face].drawPage({...ctx,line(...args){lines.push(args);}},
    {nowMs,values:{face_snapshot:snapshot(extra)}});
  return JSON.stringify(lines);
}
assert.equal(nativeLines('main'),nativeLines('main',{osc2_wavetable:107,osc2_position:100}),
  'muted OSC2 must not alter the combined waveform');
assert.notEqual(nativeLines('main',{osc2_volume:100,osc2_wavetable:1}),
                nativeLines('main',{osc2_volume:100,osc2_wavetable:107}),
  'audible OSC2 wavetable must alter the combined waveform');
assert.notEqual(nativeLines('main',{osc2_volume:100,osc2_position:0}),
                nativeLines('main',{osc2_volume:100,osc2_position:100}),
  'audible OSC2 position must alter the combined waveform');
assert.notEqual(nativeLines('osc1',{osc1_warp_type:1,osc1_warp:0}),
                nativeLines('osc1',{osc1_warp_type:1,osc1_warp:90}),
  'OSC1 native preview must react to warp');
assert.notEqual(nativeLines('osc2',{osc2_warp_type:6,osc2_warp:0}),
                nativeLines('osc2',{osc2_warp_type:6,osc2_warp:90}),
  'OSC2 native preview must react to warp');
assert.equal(nativeLines('osc1',{lfo_depth:90,voice_activity:0},1000),
             nativeLines('osc1',{lfo_depth:90,voice_activity:0},1800),
  'inactive native oscillator must not animate');
assert.notEqual(nativeLines('osc1',{lfo_depth:90,voice_activity:1},1000),
                nativeLines('osc1',{lfo_depth:90,voice_activity:1},1800),
  'active native oscillator must animate');
assert.notEqual(nativeLines('filter',{cutoff:15}),nativeLines('filter',{cutoff:85}),
  'filter graphic must track cutoff');
// New curated bank must appear on both animated native oscillator faces,
 // and each spectral control must change the illustrated harmonic envelope.
 for(const face of ['osc1','osc2']){
   const idKey=face==='osc1'?'wavetable':'osc2_wavetable';
   const posKey=face==='osc1'?'position':'osc2_position';
   const foldKey=face==='osc1'?'osc1_spectral_fold':'osc2_spectral_fold';
   const shiftKey=face==='osc1'?'osc1_spectral_shift':'osc2_spectral_shift';
   assert.notEqual(nativeLines(face,{[idKey]:115,[posKey]:0}),
                   nativeLines(face,{[idKey]:115,[posKey]:100}),
                   face+' curated ID 8 position must change the native waveform');
   assert.notEqual(nativeLines(face,{[idKey]:115,[foldKey]:0}),
                   nativeLines(face,{[idKey]:115,[foldKey]:100}),
                   face+' Fold must change its visual waveform');
   assert.notEqual(nativeLines(face,{[idKey]:115,[shiftKey]:0}),
                   nativeLines(face,{[idKey]:115,[shiftKey]:100}),
                   face+' Shift must change its visual waveform');
   assert.notEqual(nativeLines(face,{[idKey]:115}),
                   nativeLines(face,{[idKey]:116}),
                   face+' curated wavetable selection must update the waveform');
 }
 console.log('PASS: new curated sources, spectral axes and WT position drive both oscillator faces');
// Most important hardware regression: Schwung can hand a fresh physical
// encoder detent to the canvas while face_snapshot is still one poll behind.
// The face MUST prefer the encoder, not keep displaying the previous ID.
function liveFaceLines(face, extra, live) {
  const lines=[];
  named['sprig_'+face].drawPage({...ctx,line(...args){lines.push(args);}},{
    nowMs:1000,values:{face_snapshot:snapshot(extra),...live}
  });
  return JSON.stringify(lines);
}
for(const face of ['osc1','osc2']){
  const is2=face==='osc2';
  const source=is2?'osc2_wavetable':'wavetable';
  const curated=is2?'curated_osc2':'curated_osc1';
  const active=is2?'osc2_source_curated':'osc1_source_curated';
  const baseline=liveFaceLines(face,{[source]:115,[curated]:8,[active]:1},{[curated]:8});
  const turned=liveFaceLines(face,{[source]:115,[curated]:8,[active]:1},{[curated]:9});
  assert.notEqual(baseline,turned,face+' must redraw when live Curated 8->9 but snapshot still says 8');
  const cleared=liveFaceLines(face,{[source]:115,[curated]:8,[active]:1},{[curated]:0});
  assert.notEqual(baseline,cleared,face+' must redraw when Curated is changed to zero');
  assert.notEqual(nativeLines(face,{[source]:115,[curated]:8,[active]:1,voice_activity:1},1000),
                  nativeLines(face,{[source]:115,[curated]:8,[active]:1,voice_activity:1},1800),
                  face+' must visibly animate on held notes without LFO depth');
  assert.equal(nativeLines(face,{[source]:115,[curated]:8,[active]:1,voice_activity:0},1000),
               nativeLines(face,{[source]:115,[curated]:8,[active]:1,voice_activity:0},1800),
               face+' must remain still when voices are inactive');
}
console.log('PASS: live curated encoder beats delayed snapshot and note-gated OSC1/OSC2 animation');
// Wavetable 0..107 is a fully active spectral DSP source. Its visual must
// also respond to the three spectral controls on BOTH OSC spectral pages.
for(const face of ['osc1','osc2']){
  const is2=face==='osc2', key=is2?'osc2_wavetable':'wavetable';
  const curated=is2?'curated_osc2':'curated_osc1';
  const mode=is2?'osc2_source_curated':'osc1_source_curated';
  const effects=['shift','fold','scramble'];
  const base={[key]:30,[curated]:0,[mode]:0};
  const neutral=nativeLines(face,base);
  for(const effect of effects){
    const wet=nativeLines(face,{...base,['osc'+(is2?2:1)+'_spectral_'+effect]:100});
    assert.notEqual(neutral,wet,face+' Wavetable 30 '+effect+' must change the visible trace');
  }
  const muted=nativeLines(face,{...base,voice_activity:0},1200);
  const held=nativeLines(face,{...base,voice_activity:1},1200);
  assert.notEqual(muted,held,face+' must show an active-note trace');
  assert.notEqual(nativeLines(face,{...base,voice_activity:1},1200),
                  nativeLines(face,{...base,voice_activity:1},1750),
                  face+' held legacy wavetable must visibly animate');
  const snap={...base,voice_activity:0};
  const live=liveFaceLines(face,snap,{voice_activity:1});
  assert.notEqual(live,nativeLines(face,snap),
                  face+' direct voice-activity read must override older snapshot');
  const snapshotActive=liveFaceLines(face,{...snap,voice_activity:1},{voice_activity:0});
  assert.notEqual(snapshotActive,nativeLines(face,snap),
                  face+' active voice in snapshot must win over stale direct zero');
}
console.log('PASS: both OSC spectral canvases animate legacy WT with Shift, Fold, Scramble and live note activity');
// Spectral canvas has exactly the same drawing engine as OSC1/OSC2 but
// uses its own assigned S/F/X/Wavetable knobs. A source ID readout makes
// stale or disconnected Curated values visible immediately on real hardware.
for(const osc of [1,2]){
 const face='osc'+osc;
 const keys=['osc'+osc+'_spectral_shift','osc'+osc+'_spectral_fold',
             'osc'+osc+'_spectral_scramble',osc===1?'wavetable':'osc2_wavetable'];
 const source=osc===1?'wavetable':'osc2_wavetable';
 const cid='curated_osc'+osc;
 const mode='osc'+osc+'_source_curated';
 const labels=[];
 named['sprig_'+face].drawPage({...ctx,print(x,y,label){labels.push(label);}},{
   nowMs:1000,keys,values:{face_snapshot:snapshot({[source]:115,[cid]:8,[mode]:1,
                                      [keys[0]]:40,[keys[1]]:70,[keys[2]]:95})}
 });
 for(const meter of ['S','F','X','T'])assert(labels.includes(meter),
        face+' missing active spectral meter '+meter);
 assert(labels.includes('C08'),face+' must display active Curated 8');
 const regular=[];
 named['sprig_'+face].drawPage({...ctx,print(x,y,label){regular.push(label);}},{
   nowMs:1000,keys,values:{face_snapshot:snapshot({[source]:30,[cid]:8,[mode]:0,
                                      [osc===1?'raw_wavetable':'raw_osc2_wavetable']:30})}
 });
 assert(regular.includes('W030'),face+' must show active regular Wavetable 30');
}
console.log('PASS: spectral pages render oscillator waveform, S/F/X meters and readable active source ID');



console.log('PASS: OSC1, OSC2, MAIN and FILTER native face snapshots, warp and motion');

assert.notEqual(nativeLines('filter',{filter_type:0}),nativeLines('filter',{filter_type:1}),'Filter FACE must change with mode');
assert.notEqual(nativeLines('filter',{filter_type:2}),nativeLines('filter',{filter_type:3}),'Bandpass and notch curves must differ');
console.log('PASS: Phase 3 FILTER FACE changes response by filter type');

// Phase 8: main performance HUD tracks oscillator blend, pan and note activity.
function performancePixels(values){const pixels=[];overlay.drawPage({...ctx,fillRect(x,y,w,h,c){pixels.push([x,y,w,h,c]);}}, {nowMs:1000,values});return pixels;}
const baseHud={wavetable:1,osc1_volume:100,osc2_volume:0,master_pan:50,voice_activity:0};
const leftHud=performancePixels(baseHud);
const blendedHud=performancePixels({...baseHud,osc1_volume:50,osc2_volume:50});
const rightHud=performancePixels({...baseHud,master_pan:90});
assert.notDeepEqual(leftHud,blendedHud,'oscillator balance must change HUD');
assert.notDeepEqual(leftHud,rightHud,'master pan must change HUD');
const soundingHud=performancePixels({...baseHud,voice_activity:3});
assert(soundingHud.some(p=>p[0]===5&&p[1]===ctx.height-13&&p[2]===10&&p[3]===3&&p[4]===1),'voice activity slots missing');
assert(!leftHud.some(p=>p[0]===5&&p[1]===ctx.height-13&&p[2]===10&&p[3]===3&&p[4]===1),'idle voice slots must remain unfilled');
console.log('PASS: Phase 8 balance, stereo position and voice-activity HUD');
