/* Synth_esis: native Move 128x64 graphics page.
 * Uses documented Schwung canvas overlay drawPage().
 * Pure rendering: no parameter reads, file operations or allocations from DSP.
 */
(function () {
  function bounded(v, fallback, lo, hi) {
    const n = Number(v);
    return Number.isFinite(n) ? Math.max(lo, Math.min(hi, n)) : fallback;
  }
  function value(values, key, fallback) {
    return values && values[key] != null ? Number(values[key]) : fallback;
  }
  function waveform(phase, wave, pos) {
    const sine = Math.sin(phase * 6.28318530718);
    const saw = phase * 2 - 1;
    const sq = phase < .5 ? 1 : -1;
    const tri = 1 - 4 * Math.abs(phase - .5);
    const shape = [sine, saw, sq, tri][Math.max(0, Math.min(3, wave | 0))];
    return shape * (1 - .19 * pos) + .19 * pos * Math.sin(phase * 18.84955592);
  }
  /* Visual approximation of the generated spectral families, not an audio readback.
   * Cap at 24 harmonics to keep the Move canvas render lightweight. */
  function expandedWave(phase, table, pos, shape=50) {
    const family=Math.floor(table/4),variant=table%4;
    const frame=pos*3;
    const tilt=.85+.33*variant+.22*frame;
    let sum=0,norm=0;
    for(let h=1;h<=24;h++){
      let weight=0;
      if(family===0)weight=1/Math.pow(h,tilt);
      else if(family===1)weight=(h%2?1:.01)/Math.pow(h,tilt);
      else if(family===2)weight=(h%3===1?1:.01)/Math.pow(h,tilt);
      else if(family===3)weight=(h%4===1?1:.01)/Math.pow(h,tilt);
      else if(family===4)weight=(.2+.8*Math.abs(Math.sin(h*(.55+.12*variant)+frame*.2)))/Math.pow(h,tilt);
      else if(family===5)weight=(Math.abs(h-(3+variant*2+frame*2))<=1?1:.005)/Math.pow(h,.35+.1*frame);
      else if(family===6)weight=([1,2+variant,5+Math.round(frame),9+variant*2].includes(h)?1:.005)/Math.pow(h,.4+.1*frame);
      else if(family===7)weight=(.02+.98*Math.abs(Math.cos(h*(1.2+.13*variant)+frame*.3)))/Math.pow(h,.55+.15*frame);
      else if(family===8)weight=([1,3+variant,8+Math.round(frame)*3,17+variant*4].includes(h)?1:.002)/Math.pow(h,.3);
      else if(family===9)weight=(h%2===0?1:.01)*Math.abs(Math.sin(h*(.3+.1*variant)+frame*.5))/Math.pow(h,.5+.1*frame);
      else if(family===10)weight=(h%(5+variant)===1?1:.005)/Math.pow(h,.3+.2*frame);
      else if(family===11)weight=([1,6+variant*2,13+Math.round(frame)*3,23+variant*3].includes(h)?1:.003)/Math.pow(h,.3+.15*frame);
      else if(family===12)weight=Math.exp(-Math.pow((h-(4+variant*3+frame*4))/(2+variant),2))+.02/h;
      else if(family===13)weight=.8*Math.exp(-Math.pow((h-(3+variant+frame*2))/2,2))+.7*Math.exp(-Math.pow((h-(14+variant*4-frame))/4,2))+.02/h;
      else if(family===14)weight=(Math.abs(h-(5+variant*2+frame*3))<3?.02:1)/Math.pow(h,.55+.12*variant);
      else if(family===15)weight=([1,4+variant,11+Math.round(frame)*2,22+variant*3].includes(h)?1:.002)/Math.pow(h,.18+.08*frame);
      else if(family===16)weight=(.1+.9*Math.abs(Math.sin(h*h*(.13+.02*variant)+frame*.7)))/Math.pow(h,.65+.1*frame);
      else if(family===17)weight=((h+Math.round(frame))%(3+variant)===0?1:.015)/Math.pow(h,.25+.16*frame);
      else if(family===18)weight=(.02+.98*Math.pow(Math.abs(Math.cos(h*(.24+.09*variant)+frame*.9)),4))/Math.pow(h,.5+.1*variant);
      else if(family===19)weight=([1,2,3+variant*2,20+Math.round(frame)*5].includes(h)?1:.003)/Math.pow(h,.3+.1*frame);
      else if(family===20)weight=Math.exp(-Math.pow((h-(9+variant*4-frame*2))/(3+frame),2))+.05/h;
      else if(family===21)weight=(h%(4+variant)===Math.round(frame)%(4+variant)?.02:1)/Math.pow(h,.7+.1*frame);
      else if(family===22)weight=(.1+.9*Math.abs(Math.sin(h*(1.9+.2*variant)+frame*.6)))/Math.pow(h,.2+.15*frame);
      else weight=([1,7+Math.round(frame)*3,16+variant*4,35-Math.round(frame)*4].includes(h)?1:.001)/Math.pow(h,.2+.1*variant);
      sum+=weight*Math.sin(h*phase*6.28318530718+.13*frame*h+.07*variant*h);
      norm+=weight;
    }
    const base=sum/Math.max(.6,norm*.55);
    const sh=(shape-50)/50;
    const dark=.5*(Math.sin(phase*6.28318530718)+Math.sin(phase*6.28318530718+.15));
    return Math.max(-1,Math.min(1,sh<0?base*(1+sh*.7)+dark*(-sh*.7):base*(1+sh*.35)));
  }
  function coreWave(phase,id,pos){
    const frame=Math.min(3,Math.floor(pos*3)),next=Math.min(3,frame+1);
    const u=pos*3-frame,m=u*u*(3-2*u);
    function sample(f){
      const t=f/3,core=id-100,p=phase*6.28318530718;
      let v=0;
      for(let h=1;h<=24;h++){
        const bell=(c,w)=>Math.exp(-Math.pow((h-c)/w,2));
        let a=0,shift=0;
        if(core===0)a=(1-t)*(h===1?.98:0)+t*(h===2?.75:h===3?.4:0);
        else if(core===1)a=Math.pow(h,-(1.15-.65*t))*(f===0?1:f===1?(h%2?1:.05):f===2?(h%3===1?1:.03):1);
        else if(core===2){a=(h%2?1:0)/Math.pow(h,.9-.45*t);if(f<=1&&h>=7)a*=.12;if(f>=2&&h<7)a*=.015;}
        else if(core===3)a=.03/h+.95*bell(3+10*t,1.6)+.8*bell(19-10*t,2.4);
        else if(core===4){a=.08*bell(1,.42)+bell(7+f*3,.42)+.8*bell(19+f*4,.42)+.5*bell(37-f*2,.42);shift=h*h*.17;}
        else if(core===5){a=.65*bell(2,1.2)+bell(8+f*5,1.2)+.9*bell(27-f*4,1.2)+.7*bell(43-f*3,1.2);shift=h*h*(.23+.12*t);}
        else if(core===6){a=(h===1?.9-.65*t:.025/h)+(.08+1.35*t)*bell(3+18*t,1.3+3.2*t);shift=.3*Math.sin(h*.3+t*3);}
        else {a=f===0?(h===1?.28:h===5?.9:h===11?.6:0):f===1?(h%7===1?1:.005)/Math.pow(h,.25):f===2?([3,11,23,41].includes(h)?1:.002)/Math.pow(h,.12):(h%2===0?1:.001)/Math.pow(h,.1);shift=h*h*(.13+.15*t);}
        v+=a*Math.sin(h*p+shift+.13*f*h);
      }
      return v;
    }
    return Math.max(-1,Math.min(1,((1-m)*sample(frame)+m*sample(next))*.45));
  }
  function displayedWave(phase,wave,pos,bank,table,shape,legacyShape=50){
    if(table>=96&&table<=103&&bank)return coreWave(phase,table+4,pos);
    const legacy=waveform(phase,wave,pos)+Math.sin(phase*6.28318530718)*((legacyShape-50)/50)*.32;
    return bank?expandedWave(phase,table,pos,shape):legacy;
  }
  function trace(ctx, x, y, w, h, wave, pos, drift, bank, table, shape, legacyShape) {
    let lastX=x,lastY=y+h/2;
    for(let i=0;i<w;i++){
      const v=displayedWave((i/w + drift) % 1,wave,pos,bank,table,shape,legacyShape);
      const py=y+Math.round(h/2-v*(h/2-2));
      if(i)ctx.line(lastX,lastY,x+i,py,1);
      lastX=x+i;lastY=py;
    }
  }
  // Detune visualization: a second trace separates in phase while notes sound.
  // Rate and direction follow the oscillator detune controls; no audio readback.
  function detuneGhost(ctx,x,y,w,h,wave,pos,drift,bank,table,shape,legacyShape,values,seconds){
    const d1=bounded(value(values,'osc1_detune',50),50,0,100)-50;
    const d2=bounded(value(values,'osc2_detune',50),50,0,100)-50;
    const mix=bounded(value(values,'osc2_volume',0),0,0,100)/100;
    const delta=(d2-d1)*.0005776;
    if(mix<.02||Math.abs(delta)<.00001)return;
    const slip=seconds*delta*1.8;
    const phaseOffset=slip-Math.floor(slip);
    for(let i=0;i<w;i+=3){
      const p=((i/w+drift+phaseOffset)%1+1)%1;
      const v=displayedWave(p,wave,pos,bank,table,shape,legacyShape);
      const py=y+Math.round(h/2-v*(h/2-2)*.72);
      ctx.fillRect(x+i,py,1,1,1);
    }
  }
  /* Four distinct page renderers. The host must register separate canvas
   * page entries for these to become physical jog-wheel stops. */
  function pageMeters(ctx,meters,H,W){
    const y=H-9,cell=Math.floor(W/meters.length);
    meters.forEach((m,i)=>{
      const x=i*cell,barW=Math.max(3,cell-11);
      ctx.print(x+1,y,m[0],1);
      ctx.fillRect(x+8,y+2,barW,3,0);
      ctx.fillRect(x+8,y+2,Math.round(barW*bounded(m[1],0,0,100)/100),3,1);
    });
  }

  /* Exactly one extra_keys read from DSP, no dynamic DSP queries in JS. */
  const snapshotKeys=[
    'wavetable','position','osc1_warp_type','osc1_warp','osc1_detune',
    'osc1_pan','osc1_volume','osc2_wavetable','osc2_position',
    'osc2_warp_type','osc2_warp','osc2_detune','osc2_pan','osc2_volume',
    'shape','lfo_rate','lfo_depth','lfo_wt_depth','cutoff','resonance',
    'drive','filter_env_amt','lfo_filter','master_pan','filter_type','voice_activity','matrix_cutoff_lfo1','matrix_cutoff_lfo2','lfo2_rate',
    'osc1_spectral_shift','osc1_spectral_fold','osc1_spectral_scramble',
    'osc2_spectral_shift','osc2_spectral_fold','osc2_spectral_scramble',
    'curated_osc1','curated_osc2','osc1_source_curated','osc2_source_curated',
    'raw_wavetable','raw_osc2_wavetable'
  ];
  function faceValues(o){
    const initial=(o&&o.values)||{};
    const pageKeys=Array.isArray(o&&o.keys)?o.keys:[];
    if(typeof initial.face_snapshot!=='string')return {...initial,_pageKeys:pageKeys};
    const parts=initial.face_snapshot.split(',');
    if(parts.length!==snapshotKeys.length && parts.length!==35 &&
       parts.length!==29 && parts.length!==26)return {...initial,_pageKeys:pageKeys};
    const result={...initial,_pageKeys:pageKeys};
    for(let i=0;i<parts.length;i++){
      const n=Number(parts[i]);
      if(!Number.isFinite(n))return initial;
      const key=snapshotKeys[i];
      /* Canvas pages have live encoder/extra-key values alongside the
       * staggered snapshot. The newer value must win, including 0 (silence
       * or the 'legacy' curated selector). Preserve the snapshot separately
       * for comparing source changes without overriding the knob. */
      if(key==='voice_activity' && initial[key]!=null){
        /* Reads are staggered. A fresh active voice from EITHER source must
         * animate immediately; motion stops after both reach zero. */
        result[key]=Math.max(n,Number(initial[key])||0);
      }else if(initial[key]!=null){
        result['snapshot_'+key]=n;
      }else result[key]=n;
    }
    return result;
  }
  /* Schwung publishes the touched encoder key immediately, while
   * face_snapshot is polled on a staggered extra-key schedule. Never let
   * the older snapshot overwrite a newer curated knob detent.
   * Keeping both values local to this paint avoids DSP-side reads. */
  function activeSourceId(values, osc2) {
    const legacyKey=osc2?'osc2_wavetable':'wavetable';
    const curatedKey=osc2?'curated_osc2':'curated_osc1';
    const modeKey=osc2?'osc2_source_curated':'osc1_source_curated';
    const current=bounded(value(values,legacyKey,1),1,0,123)|0;
    const raw=bounded(value(values,curatedKey,0),0,0,16)|0;
    const mode=value(values,modeKey,NaN);
    const snapshotSelected=value(values,'snapshot_'+curatedKey,NaN);
    const legacy=bounded(value(values,osc2?'raw_osc2_wavetable':'raw_wavetable',current),current,0,107)|0;
    /* The knob has newer data than the staggered snapshot. In that short
     * window its live selection wins. This also works when turning to 0. */
    const pageKeys=values&&values._pageKeys||[];
    const curatedKnob=pageKeys.indexOf(curatedKey)>=0;
    if(Number.isFinite(snapshotSelected) && raw!==snapshotSelected){
      /* A physical Curated knob is authoritative. Off-page curated extras
       * can be older than face_snapshot, so the snapshot wins there. */
      if(curatedKnob || pageKeys.length===0)return raw?107+raw:legacy;
      return mode && snapshotSelected?107+snapshotSelected:legacy;
    }
    if(Number.isFinite(mode)){
      const chosen=!curatedKnob && Number.isFinite(snapshotSelected)?snapshotSelected:raw;
      return mode && chosen?107+chosen:legacy;
    }
    /* Pre-upgrade snapshot fallback: an oscillator page with the live curated
     * key must respond to it directly, even when face_snapshot lags. */
    if(values && values[curatedKey]!=null) {
      return raw?107+raw:current<=107?current:
        bounded(value(values,osc2?'raw_osc2_wavetable':'raw_wavetable',1),1,0,107)|0;
    }
    return current;
  }
  /* Same piecewise warp curves as DSP, drawn on a low-cost mono preview. */
  function warpedPhase(p,mode,amount){
    const a=bounded(amount,0,0,100)/100;
    if(!mode||!a)return p;
    if(mode===1)p=(p*(1+3*a))%1;
    else if(mode===2)p+=(p*p-p)*a*.95;
    else if(mode===3)p+=(p-p*p)*a*.95;
    else if(mode===4){const q=.5+.45*a;p=p<q?.5*p/q:.5+.5*(p-q)/(1-q);}
    else if(mode===5){const q=.5-.4*a;p=p<q?.5*p/q:.5+.5*(p-q)/(1-q);}
    else if(mode===6){const z=p*(1+2*a),n=Math.floor(z);p=(n%2)?1-(z-n):z-n;}
    else if(mode===7){const steps=64-60*a;p=Math.floor(p*steps)/steps;}
    return Math.max(0,Math.min(.99999,p));
  }
  /* Curated oscillator display uses the *active* ID from the DSP snapshot.
   * This is a responsive harmonic illustration, not a measured FFT. Build
   * only once per canvas render, then reuse coefficients for every pixel. */
  const curatedCenters=[
    [[1],[1],[1],[1]],
    [[3,7,12],[3,10,19],[7,18,27],[12,24,33]],
    [[3,7,11],[5,9,15],[9,17,25],[5,17,31]],
    [[3,7,13],[5,11,19],[7,17,25],[15,23,33]],
    [[3,7,15],[5,11,21],[9,17,29],[7,23,35]],
    [[3,9,17],[5,14,23],[8,21,32],[4,26,36]],
    [[4,10,17],[10,15,24],[19,26,33],[5,25,37]],
    [[4,9,17],[8,14,23],[5,17,29],[11,20,33]],
    [[2,5,11],[3,7,14],[2,9,17],[4,11,23]],
    [[2,6,10],[3,8,12],[4,10,15],[2,11,18]],
    [[1,5,9],[1,7,13],[1,9,17],[1,11,21]],
    [[1,3,6],[1,5,10],[1,8,16],[1,12,24]],
    [[2,7,13],[3,8,15],[2,10,19],[5,12,23]],
    [[3,8,15],[5,11,20],[8,14,25],[11,19,33]],
    [[1,3,7],[1,4,10],[1,5,13],[1,6,16]],
    [[3,7,12],[5,11,17],[7,15,23],[9,19,29]]
  ];
  function curatedPreviewSpectrum(id,pos,shift,fold,scramble){
    const top=24,kind=Math.max(0,Math.min(15,id-108));
    const fpos=Math.max(0,Math.min(3,pos*3)),f0=Math.floor(fpos),f1=Math.min(3,f0+1);
    let mix=fpos-f0;mix=mix*mix*(3-2*mix);
    const weights=Array(top+1).fill(0);
    for(let h=1;h<=top;h++){
      if(id<108){
        /* Lightweight illustrative partial set for 0..107. Their actual
         * wet waveforms come from offline DSP banks, not an FFT in canvas. */
        const type=id<4?id:Math.floor((id-4)/4)%8;
        let w=type===0?1/Math.pow(h,1+.5*pos)
          :type===1?(h%2?1:.03)/Math.pow(h,.9+.4*pos)
          :type===2?(h%3===1?1:.05)/Math.pow(h,.65+.4*pos)
          :type===3?(h%4===1?1:.03)/Math.pow(h,.5+.5*pos)
          :(.1+.9*Math.abs(Math.sin(h*(.27+.07*type)+pos*3)))/Math.pow(h,.8);
        if(id===0)w=h===1?1:0;
        if(id===3)w=h%2?1/Math.pow(h,2.5-pos):0;
        weights[h]=w;
        continue;
      }
      if(kind===0){weights[h]=h===1?1:0;continue;}
      const scene=(frame)=>{
        const centers=curatedCenters[kind][frame];
        let v=h===1?.23:.018/Math.sqrt(h);
        if(kind===2 || kind===3 || kind===4){if((h&1)===0)v*=.08;}
        for(let j=0;j<centers.length;j++){
          const z=(h-centers[j])/(1.35+j*.55);
          v+=[1.25,1.0,.65][j]*Math.exp(-.5*z*z);
        }
        return v;
      };
      weights[h]=(1-mix)*scene(f0)+mix*scene(f1);
    }
    /* Nearly pure original waveforms need a modest source for spectral
     * permutation. This mirrors the wet-only offline harmonic scaffold,
     * while neutral playback remains the original waveform. */
    if(id<108 && shift+fold+scramble>0 && top>=8){
      const low=weights[1]||1;
      weights[6]+=.21*low;
      weights[11]+=.16*low;
      weights[17]+=.13*low;
      weights[23]+=.10*low;
    }
    /* Keep the lower harmonics recognizable; spectral controls change the
     * shape even when only one parameter is moved. */
    const p=3;
    let current=weights;
    if(shift>0){
      const next=current.slice(),dist=Math.max(1,Math.min(8,Math.round(shift*8)));
      for(let k=p+1;k<=top;k++)next[k]=current[k]*(1-shift);
      for(let k=p+1;k+dist<=top;k++)next[k+dist]+=current[k]*shift;
      current=next;
    }
    if(fold>0){
      const next=current.slice(),span=8,period=span*2;
      for(let k=p+1;k<=top;k++)next[k]=current[k]*(1-fold);
      for(let k=p+1;k<=top;k++){
        const off=(k-p-1)%period,target=p+1+(off<=span?off:period-off);
        next[target]+=current[k]*fold;
      }
      current=next;
    }
    if(scramble>0){
      const next=current.slice(),count=top-p;
      for(let k=p+1;k<=top;k++){
        const src=p+1+(((k-p-1)*5+kind*3)%count);
        next[k]=current[k]*(1-scramble)+current[src]*scramble;
      }
      current=next;
    }
    const norm=Math.max(.001,current.reduce((a,b)=>a+Math.abs(b),0));
    return current.map(v=>v*(3.0/norm));
  }
  function oscillatorPreview(phase,v,osc2,seconds,active){
    const prefix=osc2?'osc2_':'osc1_';
    const id=activeSourceId(v,osc2);
    const wave=Math.min(3,id),bank=id>=4?1:0,table=Math.max(0,id-4);
    const position=bounded(value(v,osc2?'osc2_position':'position',50),50,0,100)/100;
    const rate=bounded(value(v,'lfo_rate',22),22,0,100);
    const depth=bounded(value(v,'lfo_depth',0),0,0,100);
    const wtDepth=bounded(value(v,'lfo_wt_depth',0),0,0,100);
    const modulation=active?(depth+wtDepth)*.005*Math.sin(seconds*(.06+.12*rate)*6.28318530718):0;
    const pos=Math.max(0,Math.min(1,position+modulation));
    const detune=bounded(value(v,prefix+'detune',50),50,0,100);
    const slip=active?seconds*(detune-50)*.0005776*2:0;
    /* Note-gated movement is visible without requiring an LFO assignment.
     * This is a visual phase drift, not a claim of live audio readback. */
    const visualMotion=active?seconds*(.14+.006*(id%13)):0;
    const raw=((phase+slip+visualMotion)%1+1)%1;
    const warped=warpedPhase(raw,bounded(value(v,prefix+'warp_type',0),0,0,7)|0,value(v,prefix+'warp',0));
    const shape=osc2?50:bounded(value(v,'shape',50),50,0,100);
    const shift=bounded(value(v,prefix+'spectral_shift',0),0,0,100)/100;
    const fold=bounded(value(v,prefix+'spectral_fold',0),0,0,100)/100;
    const scramble=bounded(value(v,prefix+'spectral_scramble',0),0,0,100)/100;
    if(id>=108 || shift+fold+scramble>0){
      const cacheKey=osc2?'spectrum2':'spectrum1';
      if(!v[cacheKey])v[cacheKey]=curatedPreviewSpectrum(id,pos,shift,fold,scramble);
      const amps=v[cacheKey];
      let sample=0;
      for(let h=1;h<amps.length;h++)sample+=amps[h]*Math.sin(warped*6.28318530718*h+
        (id>=115?h*h*.037+pos*3*h*.13:0));
      return Math.max(-1,Math.min(1,sample));
    }
    return displayedWave(warped,wave,pos,bank,table,shape,shape);
  }
  function drawOscillators(ctx,v,which,seconds,active,W,H){
    const width=W-3,height=Math.max(7,H-(which==='main'?25:15));
    const vol1=bounded(value(v,'osc1_volume',100),100,0,100)/100;
    const vol2=bounded(value(v,'osc2_volume',0),0,0,100)/100;
    const scale=which==='main'?Math.max(.5,vol1+vol2):1;
    let last=0;
    for(let i=0;i<width;i++){
      const phase=i/width;
      let sample;
      if(which==='main'){
        sample=(vol1*oscillatorPreview(phase,v,false,seconds,active)+
                vol2*oscillatorPreview(phase,v,true,seconds,active))/scale;
      }else sample=oscillatorPreview(phase,v,which==='osc2',seconds,active);
      const y=2+Math.round(height/2-Math.max(-1,Math.min(1,sample))*(height/2-2));
      if(i)ctx.line(i,last,i+1,y,1);
      last=y;
    }
  }
  function renderFace(ctx,o,which){
    const v=faceValues(o),W=ctx.width||128,H=ctx.height||40;
    if(W<32||H<18)return;
    frame++;
    const seconds=(o&&Number.isFinite(o.nowMs))?o.nowMs/1000:frame/30;
    const active=bounded(value(v,'voice_activity',0),0,0,8)>0;
    if(which==='filter'){
      /* Eight DSP filter response families; illustrative, not a measured FFT. */
      const cutoff=bounded(value(v,'cutoff',78),78,0,100);
      const res=bounded(value(v,'resonance',15),15,0,100);
      const mode=bounded(value(v,'filter_type',0),0,0,7);
      const y0=2,h=Math.max(8,H-16);
      let previous=0;
      for(let x=0;x<W-2;x++){
        const t=x/(W-2),center=.1+.8*cutoff/100;
        const ratio=Math.max(.001,t)/Math.max(.001,center);
        const lp=1/(1+Math.pow(ratio,4)),hp=1-lp;
        const band=Math.exp(-Math.pow(Math.log(ratio)/.36,2));
        const peak=(res/100)*.35*band;
        const response=[lp,hp,band,1-band,Math.min(1,.5+band*.5),1,lp*lp,hp*hp][mode];
        const y=y0+Math.round(h*(1-Math.max(0,Math.min(1,response+peak*(mode===0||mode===6?1:0)))));
        if(x)ctx.line(x,y0+previous,x+1,y,1);
        previous=y-y0;
      }
      // Resonance accent: sparse moving peak marker, only while notes sound.
      if(active && res>25){
        const cx=Math.round((W-3)*(.1+.8*cutoff/100));
        const pulse=.5+.5*Math.sin(seconds*(1+res/50)*6.28318530718);
        const span=Math.max(1,Math.round(res/35*pulse));
        for(let d=-span;d<=span;d+=2)ctx.fillRect(Math.max(0,Math.min(W-2,cx+d)),3,1,1,1);
      }
      // Phase 9 foundation: a voice-gated LFO filter sweep cursor.
      // This is a control-derived preview, not a DSP readback.
      const filterMotion=bounded(value(v,'lfo_filter',0),0,0,100)/100;
      const matrix1=(bounded(value(v,'matrix_cutoff_lfo1',50),50,0,100)-50)/50;
      const matrix2=(bounded(value(v,'matrix_cutoff_lfo2',50),50,0,100)-50)/50;
      if(active && (filterMotion>.01 || Math.abs(matrix1)>.01 || Math.abs(matrix2)>.01)){
        const rate=bounded(value(v,'lfo_rate',22),22,0,100);
        const cycle=Math.sin(seconds*(.15+rate*.02)*6.28318530718);
        const rate2=bounded(value(v,'lfo2_rate',22),22,0,100);
        const cycle2=Math.sin(seconds*(.15+rate2*.02)*6.28318530718);
        const shifted=Math.max(0,Math.min(100,cutoff+cycle*(filterMotion*32+matrix1*24)+cycle2*matrix2*24));
        const cursorX=2+Math.round((W-5)*(.1+.8*shifted/100));
        ctx.fillRect(cursorX,2,2,4,1);
      }
      pageMeters(ctx,[['C',cutoff],['R',res],['E',value(v,'filter_env_amt',0)],['L',value(v,'lfo_filter',0)]],H,W);
    }else{
      drawOscillators(ctx,v,which,seconds,active,W,H);
      // A restrained phase-offset ghost illustrates active motion and oscillator beating.
      // Purely graphical: no claim of measured audio or spectral analysis.
      if(active){
        const width=W-3,height=Math.max(7,H-(which==='main'?25:15));
        const rate=bounded(value(v,'lfo_rate',22),22,0,100);
        const depth=bounded(value(v,'lfo_depth',0),0,0,100);
        const mix=bounded(value(v,'osc2_volume',0),0,0,100)/100;
        const detune=Math.abs(value(v,'osc1_detune',50)-value(v,'osc2_detune',50))/50;
        const intensity=which==='main'?Math.max(depth/100,mix*detune):depth/100;
        if(intensity>.04){
          const shift=.012+.045*intensity*Math.sin(seconds*(.15+rate*.02)*6.28318530718);
          for(let x=2;x<width;x+=4){
            const phase=(x/width+shift+1)%1;
            const sample=which==='main'
              ?(oscillatorPreview(phase,v,false,seconds,true)+mix*oscillatorPreview(phase,v,true,seconds,true))/(1+mix)
              :oscillatorPreview(phase,v,which==='osc2',seconds,true);
            const y=2+Math.round(height/2-Math.max(-1,Math.min(1,sample))*(height/2-2)*.78);
            ctx.fillRect(x,y,1,1,1);
          }
        }
      }
      if(which==='main'){
        // Performance HUD: osc balance and stereo position. Derived from current
        // synth controls; no FFT or audio-meter accuracy is implied.
        const voices=bounded(value(v,'voice_activity',0),0,0,8);
        const a=bounded(value(v,'osc1_volume',100),100,0,100);
        const b=bounded(value(v,'osc2_volume',0),0,0,100);
        const total=Math.max(1,a+b);
        const split=Math.round((W-8)*a/total);
        const pan=bounded(value(v,'master_pan',50),50,0,100);
        // Two dedicated HUD lanes, separated from waveform and bottom meters.
        // Wide blocks remain legible on the physical monochrome Move display.
        const hudY=Math.max(2,H-20),barX=3,barW=W-9;
        const osc1W=Math.round(barW*a/total);
        ctx.print(1,hudY-1,'1',1);
        ctx.print(W-5,hudY-1,'2',1);
        ctx.fillRect(barX,hudY,barW,4,0);
        ctx.fillRect(barX,hudY,osc1W,4,1);
        // Pan marker remains independent of oscillator balance.
        ctx.fillRect(Math.max(barX,Math.min(barX+barW-2,barX+Math.round((barW-2)*pan/100))),hudY-2,2,8,1);
        // Eight visible voice slots; active voices fill from left to right.
        const voiceY=H-13;
        for(let n=0;n<8;n++){
          const x=5+n*15;
          ctx.fillRect(x,voiceY,10,3,0);
          if(n<voices)ctx.fillRect(x,voiceY,10,3,1);
        }
        pageMeters(ctx,[['R',value(v,'lfo_rate',22)],['D',value(v,'lfo_depth',0)],['F',value(v,'lfo_filter',0)],['P',value(v,'master_pan',50)]],H,W);
      }else{
        const is2=which==='osc2',prefix=is2?'osc2_':'osc1_';
        const onSpectralPage=Array.isArray(o&&o.keys) &&
          o.keys.indexOf(prefix+'spectral_shift')>=0;
        if(onSpectralPage){
          /* The same graph lives on the spectral page with its own knobs.
           * Meter labels display the three *actual* spectral depths. */
          pageMeters(ctx,[['S',value(v,prefix+'spectral_shift',0)],
            ['F',value(v,prefix+'spectral_fold',0)],
            ['X',value(v,prefix+'spectral_scramble',0)],
            ['T',value(v,is2?'osc2_position':'position',50)]],H,W);
        }else{
          pageMeters(ctx,[['W',value(v,prefix+'warp',0)],
            ['T',value(v,is2?'osc2_position':'position',50)],
            ['P',value(v,prefix+'pan',50)],
            ['V',value(v,prefix+'volume',is2?0:100)]],H,W);
        }
        /* Explicit active-source diagnostic. The previous previews looked
         * almost identical and a failing snapshot could go unnoticed. */
        const activeId=activeSourceId(v,is2);
        const sourceLabel=activeId>=108
          ?'C'+String(activeId-107).padStart(2,'0')
          :'W'+String(activeId).padStart(3,'0');
        ctx.fillRect(W-28,1,28,7,0);
        ctx.print(W-27,1,sourceLabel,1);
      }
    }
  }
  let frame = 0;
  globalThis.sprig_faces = {main:(ctx,o)=>renderFace(ctx,o,'main'),osc1:(ctx,o)=>renderFace(ctx,o,'osc1'),osc2:(ctx,o)=>renderFace(ctx,o,'osc2'),filter:(ctx,o)=>renderFace(ctx,o,'filter')};
  // Named overlay entry points for future Schwung as_page registrations.
  // Keep the existing default overlay intact until hierarchy registration is validated.
  globalThis.canvas_overlays = {
    sprig_main: {drawPage:(ctx,o)=>renderFace(ctx,o,'main')},
    sprig_osc1: {drawPage:(ctx,o)=>renderFace(ctx,o,'osc1')},
    sprig_osc2: {drawPage:(ctx,o)=>renderFace(ctx,o,'osc2')},
    sprig_filter: {drawPage:(ctx,o)=>renderFace(ctx,o,'filter')}
  };
  globalThis.canvas_overlay = {
    drawPage(ctx, o) {
      // Root SYNTH face uses the same combined-oscillator renderer as sprig_main.
      return renderFace(ctx, o, 'main');
      const v=o && o.values || {};
      const W=ctx.width||128,H=ctx.height||40;
      if(W<32||H<18)return;
      const selected=bounded(value(v,"wavetable",1),1,0,107)|0;
      const wave=Math.min(3,selected);
      const bank=selected>=4?1:0;
      const table=Math.max(0,selected-4);
      const shape=bounded(value(v,"shape",50),50,0,100);
      const legacyShape=shape;
      const pos=bounded(value(v,"position",50),50,0,100)/100;
      const cut=bounded(value(v,"cutoff",78),78,0,100);
      const motion=bounded(value(v,"lfo_depth",0),0,0,100)+bounded(value(v,"lfo_wt_depth",0),0,0,100);
      const env=bounded(value(v,"filter_env_amt",0),0,0,100);
      const mix=bounded(value(v,"osc2_level",0),0,0,100);
      const rate=bounded(value(v,"lfo_rate",22),22,0,100);
      /* Only sounding voices (including release tails) enable motion.
       * A missing activity read is treated as idle, never as always-on. */
      const voices=bounded(value(v,"voice_activity",0),0,0,8);
      const depth=voices>0?motion/100:0;
      /* Some Move hosts omit nowMs. Use redraw ticks as a fallback. */
      frame++;
      const now=o && o.nowMs;
      const seconds=(typeof now==="number" && Number.isFinite(now))?now/1000:frame/30;
      /* Motion depth shapes the visual only while a voice is sounding. */
      const hz=.06+.12*rate;
      const drift=depth*.12*Math.sin(seconds*hz*6.28318530718);
      const animatedPos=Math.max(0,Math.min(1,pos+depth*.5*Math.sin(seconds*hz*6.28318530718)));
      /* The host already draws the active encoder's label and value in its
       * own header. Duplicating that feedback inside drawPage creates two
       * overlapping rows on the actual Move display. Keep this page visual. */
      const waveY=1, waveH=Math.max(7,H-14);
      trace(ctx,1,waveY+1,W-3,waveH,wave,animatedPos,drift,bank,table,shape,legacyShape);
      if(voices>0)detuneGhost(ctx,1,waveY+1,W-3,waveH,wave,animatedPos,drift,bank,table,shape,legacyShape,v,seconds);
      /* A sparse second harmonic contour gives the technical trace an organic
       * shimmer. It exists only while voices sound and Motion is substantial.
       * The base waveform remains unchanged and idle stays perfectly still. */
      if(voices>0 && motion>=15){
        const x0=1, y0=waveY+1, width=W-3, height=waveH;
        const shimmer=depth*.16*Math.sin(seconds*hz*6.28318530718+1.57);
        const ghostPos=Math.max(0,Math.min(1,animatedPos+shimmer));
        for(let i=0;i<width;i+=4){
          const phase=(i/width+drift*.6+shimmer*.15)%1;
          const v0=displayedWave(phase<0?phase+1:phase,wave,ghostPos,bank,table,shape);
          const py=y0+Math.round(height/2-v0*(height/2-2)*.78);
          ctx.fillRect(x0+i,py,1,1,1);
        }
      }
      /* Tiny persistent signal meters keep the synth readable when idle. */
      const meters=[["C",cut],["M",motion],["E",env],["O",mix]];
      const y=H-9,cell=Math.floor(W/4);
      meters.forEach((m,i)=>{
        const x=i*cell;
        ctx.print(x+1,y,m[0],1);
        const barX=x+8,barW=Math.max(3,cell-11);
        ctx.fillRect(barX,y+2,barW,3,0);
        ctx.fillRect(barX,y+2,Math.round(barW*m[1]/100),3,1);
      });
    }
  };
})();
