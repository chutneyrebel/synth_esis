#!/usr/bin/env node
/* Phase 12G: test separate browser UI metadata without a Move or browser. */
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'src/assets/ui_reference.js'),'utf8');
const context={window:{}};vm.runInNewContext(source,context,{timeout:1000});
const ui=context.window.synthEsisUi;
assert.equal(ui.version,1);
const params=JSON.parse(fs.readFileSync(path.join(root,'src/module.json'))).capabilities.chain_params;
const byKey=new Map(params.map(p=>[p.key,p]));
const keys=[...ui.velocity,...ui.spectral].map(x=>x.key);
assert.equal(new Set(keys).size,keys.length,'duplicate UI references');
assert.deepEqual(ui.velocity.map(x=>x.key),['vel_spec','vel_f','vel_s']);
for(const item of [...ui.velocity,...ui.spectral]){
  const declared=byKey.get(item.key);
  assert.ok(declared, 'unknown DSP control: '+item.key);
  assert.equal(declared.min,0);
  assert.equal(declared.max,100);
  assert.equal(typeof item.label,'string');
  assert.ok(item.label.length>5 && item.help.length>25,'missing readable help');
}
const page=fs.readFileSync(path.join(root,'src/web_ui.html'),'utf8');
assert.match(page,/<script src="assets\/ui_reference\.js"><\/script>/);
assert.match(page,/<div id="velocity"><\/div>/);
assert.match(page,/window\.synthEsisUi\.velocity/);
assert.ok(page.includes("prefix+':'+key"),'remote writes must use component-scoped keys');
console.log('PASS: all browser-only descriptions resolve stable DSP keys; sidecar does not alter native metadata');
