#!/usr/bin/env node
// Functional contract for a patched Schwung checkout. No Move required.
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
import { readFileSync } from 'node:fs';
const root=process.argv[2];
if(!root) throw Error('Pass Schwung checkout path');
const {planPages,pageSlotKeys}=await import(pathToFileURL(resolve(root,'src/shared/param_pages/page_plan.mjs')).href);
const keys=['lfo_rate','lfo_depth','lfo_filter','cutoff','resonance','master_pan','level','osc2_volume'];
const make=(flag,extra=false,hidden=false)=>({
 hierarchy:{root:'root',levels:{root:{name:'Main',knobs:keys,params:[{key:'face',type:'canvas',as_page:true,page_first:true,...(flag?{replace_knob_grid:true}:{})},...(extra?['bonus']:[]),{level:'osc1'}]},osc1:{name:'OSC1',knobs:['osc1_level'],params:['osc1_level']}}},
 chainParams:[{key:'face',type:'canvas',as_page:true,page_first:true,name:'FACE',...(flag?{replace_knob_grid:true}:{})},...keys.map(key=>({key,type:'float'})),...(extra?[{key:'bonus',type:'float'}]:[]),{key:'osc1_level',type:'float'}],
 visible:hidden?{face:false}:undefined
});
function run(opts){return planPages({...make(...opts),trailingMenus:[]}).pages}
const baseline=run([false,false,false]);
const opted=run([true,false,false]);
const canvases=pages=>pages.filter(p=>p.canvas?.key==='face');
assert.equal(canvases(baseline).length,1,'baseline canvas present');
assert.equal(canvases(opted).length,1,'opt-in canvas present');
assert.deepEqual(pageSlotKeys(canvases(opted)[0]),keys,'FACE retains eight encoder keys');
const rootGrids=pages=>pages.filter(p=>p.level==='root'&&p.kind==='knobs'&&!p.canvas);
assert.ok(rootGrids(baseline).length>=1,'default keeps MAIN');
assert.equal(rootGrids(opted).length,0,'opt-in removes MAIN');
assert.ok(opted.some(p=>p.level==='osc1'),'child level preserved');
const overflow=run([true,true,false]);
assert.ok(overflow.some(p=>p.keys?.includes('bonus')),'overflow remains reachable');
// Use the *real* Synth_esis descriptor, not only a synthetic host fixture.
// The same face overlay must appear on OSC and OSC Spectral with the
// spectrum page's OWN knob assignments.
const descriptor=JSON.parse(readFileSync('src/module.json','utf8'));
const real=planPages({hierarchy:descriptor.capabilities.ui_hierarchy,
                      chainParams:descriptor.capabilities.chain_params,
                      trailingMenus:[]}).pages;
// Phase12F: the compact root FACE reference must resolve to the same
// canvas with the original eight hardware encoders.
const facePages=real.filter(p=>p.canvas?.key==='face');
assert.equal(facePages.length,1,'compact FACE alias must resolve once');
assert.deepEqual(pageSlotKeys(facePages[0]).filter(Boolean),
  descriptor.capabilities.ui_hierarchy.levels.root.knobs,
  'compact FACE must retain eight original hardware encoder keys');
// Metadata `name` is separate from stable preset/DSP `key`.
for(const [key,name] of [['vel_spec','Vel Shift'],['vel_f','Vel Fold'],['vel_s','Vel Scram']]){
  const entry=descriptor.capabilities.chain_params.find(p=>p.key===key);
  assert.equal(entry?.name,name,'readable chain parameter label');
}
for(const osc of [1,2]){
  const face='face_osc'+osc;
  const levels=['osc'+osc,'osc'+osc+'_spectral'];
  for(const level of levels){
    const matching=real.filter(p=>p.level===level && p.canvas?.key===face);
    assert.equal(matching.length,1,
      'Synth_esis '+level+' must have its waveform canvas on the actual Schwung planner');
    assert.deepEqual(pageSlotKeys(matching[0]).filter(k=>k!==null),
      descriptor.capabilities.ui_hierarchy.levels[level].knobs,
      'Spectral waveform canvas must retain the spectral encoder bindings');
  }
}
console.log('PASS: actual OSC1/OSC2 and spectral canvas pages rendered by Schwung planner');
console.log('Schwung functional planner tests passed');
