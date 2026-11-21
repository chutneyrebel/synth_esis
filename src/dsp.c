/* Synth_esis: independently authored wavetable sound generator for Schwung.
 * Freestanding C11, no libc dependencies, no file I/O or allocations in DSP.
 * API layout matches src/host/plugin_api_v1.h from charlesvestal/schwung.
 * All parameters are integer display values, eliminating RT parsing costs.
 */
#include <stdint.h>
#include <stddef.h>
#include "tables.h"
#include "wavetable_engine.h"

#define SPRIG_VOICES 8
#define SPRIG_INSTANCES 8
#define SR 44100.0f
#define TABLE_MASK 255
#define ATTACK 1
#define DECAY 2
#define SUSTAIN 3
#define RELEASE 4

/* Reproduced ABI v2 layout, from Schwung's public plugin_api_v1.h. */
typedef struct plugin_api_v2 {
    uint32_t api_version;
    void *(*create_instance)(const char *, const char *);
    void (*destroy_instance)(void *);
    void (*on_midi)(void *, const uint8_t *, int, int);
    void (*set_param)(void *, const char *, const char *);
    int (*get_param)(void *, const char *, char *, int);
    int (*get_error)(void *, char *, int);
    void (*render_block)(void *, int16_t *, int);
} plugin_api_v2_t;

typedef struct {
    float phase, phase2, increment, env, vel, release_step;
    float character_phase[2], character_age; /* independent per-oscillator timbre clocks */
    float ic1, ic2, ic1_r, ic2_r, ic3, ic4, ic3_r, ic4_r, filter_env, smooth_cut;
    float oe[2],ors[2];uint8_t os[2];uint8_t filter_stage;
    unsigned age;
    uint8_t note, band, stage, down;
} Voice;

typedef struct {
    int wavetable, shape, wave, wt_bank, wt_table, spectral_shape, legacy_shape, position, cutoff, resonance, attack, decay, sustain, release, level;
    int curated_osc1, curated_osc2;
    int osc1_source_curated, osc2_source_curated; /* active bank, preserves both selections */
    int osc1_spectral_shift,osc1_spectral_fold,osc1_spectral_scramble;
    int osc2_spectral_shift,osc2_spectral_fold,osc2_spectral_scramble;
    int osc1_warp_type, osc1_warp, osc1_detune, osc1_octave, osc1_pan, osc1_volume;
    int osc2_wavetable, osc2_position, osc2_warp_type, osc2_warp, osc2_detune, osc2_octave, osc2_pan, osc2_volume;
    int osc2_level, detune, lfo_rate, lfo_depth, lfo_wt_depth, drive;
    int filter_env_amt, filter_env_attack, filter_env_decay, lfo_filter, master_pan, filter_type, mod_dest, mod_depth, lfo2_rate, lfo2_dest, lfo2_depth, lfo1_waveform, lfo2_waveform, sync_bpm, lfo1_sync, lfo2_sync;
int osc1_env_enabled,osc2_env_enabled,osc1_attack,osc1_decay,osc1_sustain,osc1_release,osc2_attack,osc2_decay,osc2_sustain,osc2_release,mix_enabled,mix_balance;
    int matrix_source, matrix_destination;
    int matrix_depth[2][18]; /* append 6 spectral routes; 50 = neutral */
    float lfo_phase, lfo2_phase;
    unsigned lfo_cycle, lfo2_cycle;
    float smooth_wave, smooth_position, smooth_bank, smooth_table, smooth_shape, smooth_g, smooth_res, smooth_level, smooth_master_pan;
    /* Two independent three-axis spectral depth smoothers, private to this instance.
     * Updated once per output sample, never in set_param or per voice. */
    float smooth_spectral[2][3];
    unsigned age;
    Voice voices[SPRIG_VOICES];
} Synth;

typedef struct { volatile int allocated; Synth synth; } Slot;
static Slot slots[SPRIG_INSTANCES];

static int eq(const char *a,const char *b){
    if(!a||!b)return 0;
    while(*a && *a==*b){a++;b++;}
    return *a==*b;
}
static float clampf(float x,float lo,float hi){ return x<lo?lo:x>hi?hi:x; }
static int clampi(int x,int lo,int hi){ return x<lo?lo:x>hi?hi:x; }
static int integer(const char *p){
    if(!p)return 0;
    int sign=1,val=0;
    if(*p=='-'){sign=-1;p++;}
    for(int i=0;i<9 && *p>='0' && *p<='9';++i,++p)val=val*10+(*p-'0');
    return sign*val;
}
static void wipe(void *ptr,size_t n){ volatile unsigned char *p=ptr; while(n--)*p++=0; }
static int write_str(char *out,int capacity,const char *s){
    int i=0;
    if(!out||capacity<=0)return -1;
    while(s[i]){ if(i>=capacity-1){out[0]=0;return -1;} out[i]=s[i];i++; }
    out[i]=0;return i;
}
static int append(char *s,int cap,int at,const char *part){
    if(at<0)return -1;
    for(int j=0;part[j];j++){if(at>=cap-1)return -1;s[at++]=part[j];}
    s[at]=0;return at;
}
static int append_int(char *s,int cap,int at,int v){
    char rev[16];int j=0;
    if(v<0){at=append(s,cap,at,"-");v=-v;}
    do{rev[j++]=(char)('0'+v%10);v/=10;}while(v && j<15);
    while(j--){if(at>=cap-1)return -1;s[at++]=rev[j];}
    s[at]=0;return at;
}
static void defaults(Synth *s){
    wipe(s,sizeof(*s));
    s->wavetable=1;s->shape=50;s->wave=1;s->spectral_shape=50;s->legacy_shape=50;s->position=50;s->cutoff=78;s->resonance=15;
    s->attack=10;s->decay=230;s->sustain=72;s->release=240;s->level=65;
    s->osc1_warp_type=0;s->osc1_warp=0;s->osc1_detune=50;s->osc1_octave=2;s->osc1_pan=50;s->osc1_volume=100;
    s->osc2_wavetable=1;s->osc2_position=50;s->osc2_warp_type=0;s->osc2_warp=0;s->osc2_detune=50;s->osc2_octave=2;s->osc2_pan=50;s->osc2_volume=0;
    s->osc2_level=0;s->detune=50;s->lfo_rate=22;s->lfo_depth=0;s->lfo_wt_depth=0;s->drive=0;
    s->filter_env_amt=0;s->filter_env_attack=5;s->filter_env_decay=400;s->lfo_filter=0;s->master_pan=50;s->osc1_attack=s->osc2_attack=10;s->osc1_decay=s->osc2_decay=230;s->osc1_sustain=s->osc2_sustain=72;s->osc1_release=s->osc2_release=240;s->mix_balance=50;s->mod_depth=50;s->lfo2_rate=22;s->sync_bpm=120;s->lfo2_depth=50;
    for(int src=0;src<2;src++)for(int dst=0;dst<18;dst++)s->matrix_depth[src][dst]=50;
    s->smooth_wave=1;s->smooth_position=1.5f;s->smooth_bank=0;s->smooth_table=1;s->smooth_shape=50;
    s->smooth_g=sprig_cutoff_g[s->cutoff];
    s->smooth_res=0.15f;s->smooth_level=.65f;s->smooth_master_pan=50.f;
}
static void *create_instance(const char *module_dir,const char *json_defaults){
    (void)module_dir;(void)json_defaults;
    for(int i=0;i<SPRIG_INSTANCES;i++){
        int expected=0;
        if(__atomic_compare_exchange_n(&slots[i].allocated,&expected,1,0,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE)){
            defaults(&slots[i].synth);return &slots[i].synth;
        }
    }
    return 0;
}
static void destroy_instance(void *instance){
    if(!instance)return;
    for(int i=0;i<SPRIG_INSTANCES;i++)if(instance==&slots[i].synth){
        __atomic_store_n(&slots[i].allocated,0,__ATOMIC_RELEASE);return;
    }
}
static void note_on(Synth *s,unsigned note,unsigned vel){
    int chosen=-1;unsigned oldest=0;
    for(int i=0;i<SPRIG_VOICES;i++)if(s->voices[i].stage==0){chosen=i;break;}
    if(chosen<0)for(int i=0;i<SPRIG_VOICES;i++)if(s->voices[i].stage==RELEASE){chosen=i;break;}
    if(chosen<0){for(int i=0;i<SPRIG_VOICES;i++){
        if(i==0 || s->voices[i].age<oldest){oldest=s->voices[i].age;chosen=i;}
    }}
    Voice *v=&s->voices[chosen];wipe(v,sizeof(*v));
    v->note=note;v->band=sprig_note_band[note];v->increment=sprig_note_phase_inc[note];
    v->vel=(float)vel/127.0f;v->stage=ATTACK;v->down=1;v->age=++s->age;
    v->filter_stage=1;v->smooth_cut=(float)s->cutoff;v->os[0]=v->os[1]=ATTACK;
}
static void note_off(Synth *s,unsigned note){
    for(int i=0;i<SPRIG_VOICES;i++){
        Voice *v=&s->voices[i];
        if(v->stage && v->down && v->note==note){
            v->down=0;v->stage=RELEASE;
            v->release_step=v->env/(clampf((float)s->release,1.f,2000.f)*.001f*SR);for(int o=0;o<2;o++){int ms=o?s->osc2_release:s->osc1_release;v->os[o]=RELEASE;v->ors[o]=v->oe[o]/(clampf((float)ms,1.f,2000.f)*.001f*SR);}
        }
    }
}
static void on_midi(void *instance,const uint8_t *msg,int len,int source){
    if(!instance||!msg||len<1 || source==5)return;
    Synth *s=instance;uint8_t kind=msg[0]&0xf0;
    if((kind==0x90 || kind==0x80) && len>=3 && msg[1]<128){
        if(kind==0x90 && msg[2])note_on(s,msg[1],msg[2]);
        else note_off(s,msg[1]);
    }else if(kind==0xb0 && len>=3 && (msg[1]==123 || msg[1]==120)){
        for(int i=0;i<SPRIG_VOICES;i++){
            Voice *v=&s->voices[i];v->down=0;v->stage=RELEASE;
            v->release_step=v->env/(SR*.015f);for(int o=0;o<2;o++){v->os[o]=RELEASE;v->ors[o]=v->oe[o]/(SR*.015f);}
        }
    }
}

typedef struct { const char *name; int min,max; size_t offset; } Param;
#define P(key,hi) {#key,0,hi,offsetof(Synth,key)}
static const Param params[]={
    P(curated_osc1,16),P(curated_osc2,16),
    P(osc1_spectral_shift,100),P(osc1_spectral_fold,100),P(osc1_spectral_scramble,100),
    P(osc2_spectral_shift,100),P(osc2_spectral_fold,100),P(osc2_spectral_scramble,100),
    P(wavetable,107),P(shape,100),P(wave,3),P(wt_bank,1),P(wt_table,95),P(spectral_shape,100),P(legacy_shape,100),P(position,100),P(cutoff,100),P(resonance,100),
    P(attack,2000),P(decay,2000),P(sustain,100),P(release,2000),P(level,100),
    P(osc1_warp_type,7),P(osc1_warp,100),P(osc1_detune,100),P(osc1_octave,4),P(osc1_pan,100),P(osc1_volume,100),
    P(osc2_wavetable,107),P(osc2_position,100),P(osc2_warp_type,7),P(osc2_warp,100),P(osc2_detune,100),P(osc2_octave,4),P(osc2_pan,100),P(osc2_volume,100),
    P(osc1_source_curated,1),P(osc2_source_curated,1),
    P(osc2_level,100),P(detune,100),P(lfo_rate,100),P(lfo_depth,100),P(lfo_wt_depth,100),P(drive,100),
    P(filter_type,7),P(filter_env_amt,100),P(filter_env_attack,2000),P(filter_env_decay,2000),P(lfo_filter,100),P(master_pan,100),P(osc1_env_enabled,1),P(osc2_env_enabled,1),P(osc1_attack,2000),P(osc1_decay,2000),P(osc1_sustain,100),P(osc1_release,2000),P(osc2_attack,2000),P(osc2_decay,2000),P(osc2_sustain,100),P(osc2_release,2000),P(mix_enabled,1),P(mix_balance,100),P(mod_dest,3),P(mod_depth,100),P(lfo2_rate,100),P(lfo2_dest,3),P(lfo2_depth,100),P(lfo1_waveform,5),P(lfo2_waveform,5),P(sync_bpm,240),P(lfo1_sync,5),P(lfo2_sync,5)
};
#define NP ((int)(sizeof(params)/sizeof(params[0])))
static int *param_ptr(Synth *s,int i){return (int*)((char*)s+params[i].offset);}
static void set_one(Synth *s,const char *key,const char *value,int loading_state){
    /* Direct legacy WT edits deactivate curated overrides; state recall does not. */
    if(eq(key,"wavetable")){
        s->wavetable=clampi(integer(value),0,107);
        if(!loading_state)s->osc1_source_curated=0;
        return;
    }
    if(eq(key,"osc2_wavetable")){
        s->osc2_wavetable=clampi(integer(value),0,107);
        if(!loading_state)s->osc2_source_curated=0;
        return;
    }
    if(eq(key,"curated_osc1")){
        s->curated_osc1=clampi(integer(value),0,16);
        s->osc1_source_curated=s->curated_osc1!=0;
        return;
    }
    if(eq(key,"curated_osc2")){
        s->curated_osc2=clampi(integer(value),0,16);
        s->osc2_source_curated=s->curated_osc2!=0;
        return;
    }
    if(eq(key,"matrix_source")){s->matrix_source=clampi(integer(value),0,1);return;}
    if(eq(key,"matrix_destination")){s->matrix_destination=clampi(integer(value),0,17);return;}
    if(eq(key,"matrix_depth")){s->matrix_depth[s->matrix_source][s->matrix_destination]=clampi(integer(value),0,100);return;}
    if(key[0]=='m'&&key[1]=='x'&&key[2]>='0'&&key[2]<='1'&&key[3]=='_'){
        int n=integer(key+4);if(n>=0&&n<18)s->matrix_depth[key[2]-'0'][n]=clampi(integer(value),0,100);return;
    }
    /* Stable proxy keys are necessary because Schwung caches physical knob
     * mappings when the component is loaded. */
    if(eq(key,"sync_bpm")){s->sync_bpm=clampi(integer(value),20,240);return;}
    if(eq(key,"bank_select")){if(s->wt_bank==0)s->wave=clampi(integer(value),0,3);else s->wt_table=clampi(integer(value),0,95);return;}
    if(eq(key,"bank_shape")){if(s->wt_bank==0)s->legacy_shape=clampi(integer(value),0,100);else s->spectral_shape=clampi(integer(value),0,100);return;}
    if(eq(key,"wave")){
        if(eq(value,"Sine"))value="0";
        else if(eq(value,"Saw"))value="1";
        else if(eq(value,"Square")||eq(value,"Pulse"))value="2";
        else if(eq(value,"Triangle"))value="3";
    }
    for(int i=0;i<NP;i++)if(eq(key,params[i].name)){
        *param_ptr(s,i)=clampi(integer(value),params[i].min,params[i].max);return;
    }
}
static void set_param(void *instance,const char *key,const char *value){
    if(!instance||!key||!value)return;
    Synth *s=instance;
    if(eq(key,"state")){
        /* Older presets do not contain the six Phase 10 spectral keys.
         * Loading one must restore neutral spectral processing, not retain
         * hidden values from the previously selected sound. The smoothing
         * state follows these new targets naturally without clicks. */
        s->osc1_spectral_shift=s->osc1_spectral_fold=s->osc1_spectral_scramble=0;
        s->osc2_spectral_shift=s->osc2_spectral_fold=s->osc2_spectral_scramble=0;
        /* Legacy preset files did not serialize source mode. Infer curated
         * selection from the saved curated index until explicit mode keys
         * (present in newer state snapshots) override it. */
        s->osc1_source_curated=s->osc2_source_curated=0;
        /* Older Phase 10/11 presets include just the first 12 matrix routes.
         * Clear the six newly appended spectral routes before parsing. */
        for(int src=0;src<2;src++)for(int dst=12;dst<18;dst++)
            s->matrix_depth[src][dst]=50;
        char k[32],v[24];int ix=0;
        while(value[ix] && ix<2048){
            int ki=0,vi=0;
            while(value[ix] && value[ix]!='=' && value[ix]!=',' && ki<30)k[ki++]=value[ix++];
            k[ki]=0;
            if(value[ix]!='='){if(value[ix])ix++;continue;}ix++;
            while(value[ix] && value[ix]!=',' && vi<22)v[vi++]=value[ix++];
            v[vi]=0;
            if(value[ix]==',')ix++;
            set_one(s,k,v,1);
        }
        return;
    }
    set_one(s,key,value,0);
}
/* Live DSP metadata is generated from module.json; run scripts/generate_metadata.py. */
#include "ui_metadata.h"
static int get_param(void *instance,const char *key,char *buf,int len){
    if(key && eq(key,"ui_hierarchy"))return write_str(buf,len,ui_hierarchy_json);
    if(key && eq(key,"chain_params"))return write_str(buf,len,chain_params_json);
    if(eq(key,"module_id"))return write_str(buf,len,"synth_esis");
    if(!instance||!key||!buf||len<=0)return -1;
    Synth *s=instance;
    /* Count sounding voices, including release tails, for graphical animation.
     * This read-only value never enters the audio parameter or preset list. */
    if(eq(key,"matrix_depth")){buf[0]=0;return append_int(buf,len,0,s->matrix_depth[s->matrix_source][s->matrix_destination]);}
    if(eq(key,"matrix_source")){buf[0]=0;return append_int(buf,len,0,s->matrix_source);}
    if(eq(key,"matrix_destination")){buf[0]=0;return append_int(buf,len,0,s->matrix_destination);}
    if(eq(key,"bank_select")){buf[0]=0;return append_int(buf,len,0,s->wt_bank?s->wt_table:s->wave);}
    if(eq(key,"bank_shape")){buf[0]=0;return append_int(buf,len,0,s->wt_bank?s->spectral_shape:s->legacy_shape);}
    if(eq(key,"voice_activity")){
        int active=0;
        for(int i=0;i<SPRIG_VOICES;i++)if(s->voices[i].stage)active++;
        buf[0]=0;return append_int(buf,len,0,active);
    }
    if(eq(key,"face_snapshot")){
        /* One bounded derived read per canvas. Never persisted as a preset. */
        const int data[]={
            ((s->osc1_source_curated&&s->curated_osc1)?107+s->curated_osc1:s->wavetable),s->position,s->osc1_warp_type,s->osc1_warp,
            s->osc1_detune,s->osc1_pan,s->osc1_volume,
            ((s->osc2_source_curated&&s->curated_osc2)?107+s->curated_osc2:s->osc2_wavetable),s->osc2_position,s->osc2_warp_type,
            s->osc2_warp,s->osc2_detune,s->osc2_pan,s->osc2_volume,
            s->shape,s->lfo_rate,s->lfo_depth,s->lfo_wt_depth,
            s->cutoff,s->resonance,s->drive,s->filter_env_amt,
            s->lfo_filter,s->master_pan,s->filter_type
        };
        int at=0,active=0;
        for(int i=0;i<SPRIG_VOICES;i++)if(s->voices[i].stage)active++;
        buf[0]=0;
        for(unsigned i=0;i<sizeof(data)/sizeof(data[0]);i++){
            if(i)at=append(buf,len,at,",");
            at=append_int(buf,len,at,data[i]);
            if(at<0)return -1;
        }
        at=append(buf,len,at,",");
        at=append_int(buf,len,at,active);
        if(at<0)return -1;
        /* Append-only read-only visual metadata: matrix cutoff routing for
           both LFOs, plus LFO2 rate. 50 is the neutral matrix depth. */
        const int visual[]={s->matrix_depth[0][2],s->matrix_depth[1][2],s->lfo2_rate,
            s->osc1_spectral_shift,s->osc1_spectral_fold,s->osc1_spectral_scramble,
            s->osc2_spectral_shift,s->osc2_spectral_fold,s->osc2_spectral_scramble,
            s->curated_osc1,s->curated_osc2,
            s->osc1_source_curated,s->osc2_source_curated,
            s->wavetable,s->osc2_wavetable,
            (int)(100.f*s->smooth_spectral[0][0]+.5f),
            (int)(100.f*s->smooth_spectral[0][1]+.5f),
            (int)(100.f*s->smooth_spectral[0][2]+.5f),
            (int)(100.f*s->smooth_spectral[1][0]+.5f),
            (int)(100.f*s->smooth_spectral[1][1]+.5f),
            (int)(100.f*s->smooth_spectral[1][2]+.5f)};
        for(unsigned i=0;i<sizeof(visual)/sizeof(visual[0]);i++){
            at=append(buf,len,at,",");
            at=append_int(buf,len,at,visual[i]);
            if(at<0)return -1;
        }
        return at;
    }
    if(eq(key,"state")){
        int at=0;buf[0]=0;
        for(int i=0;i<NP;i++){
            if(i)at=append(buf,len,at,",");
            at=append(buf,len,at,params[i].name);
            at=append(buf,len,at,"=");
            at=append_int(buf,len,at,*param_ptr(s,i));
            if(at<0){buf[0]=0;return -1;}
        }
        for(int src=0;src<2;src++)for(int dst=0;dst<18;dst++){
            at=append(buf,len,at,",mx");at=append_int(buf,len,at,src);
            at=append(buf,len,at,"_");at=append_int(buf,len,at,dst);
            at=append(buf,len,at,"=");at=append_int(buf,len,at,s->matrix_depth[src][dst]);
            if(at<0){buf[0]=0;return -1;}
        }
        return at;
    }
    for(int i=0;i<NP;i++)if(eq(key,params[i].name)){
        buf[0]=0;return append_int(buf,len,0,*param_ptr(s,i));
    }
    return -1;
}
static int get_error(void *instance,char *buf,int len){(void)instance;return write_str(buf,len,"");}

static float env_next(Synth *s,Voice *v){
    float sus=.01f*(float)s->sustain;
    switch(v->stage){
        case ATTACK:
            v->env+=1.0f/(SR*.001f*clampf((float)s->attack,1.f,2000.f));
            if(v->env>=1.f){v->env=1.f;v->stage=DECAY;}break;
        case DECAY:
            v->env-=(1.f-sus)/(SR*.001f*clampf((float)s->decay,1.f,2000.f));
            if(v->env<=sus){v->env=sus;v->stage=SUSTAIN;}break;
        case SUSTAIN:v->env=sus;break;
        case RELEASE:
            v->env-=v->release_step;
            if(v->env<=0.f){v->env=0.f;if(!(s->osc1_env_enabled&&v->os[0])&&!(s->osc2_env_enabled&&v->os[1]))v->stage=0;v->ic1=0;v->ic2=0;v->ic1_r=0;v->ic2_r=0;v->ic3=0;v->ic4=0;v->ic3_r=0;v->ic4_r=0;}break;
        default:return 0;
    }
    return v->env;
}
static float osc_amp(Synth *s,Voice *v,int o){
 if(!(o?s->osc2_env_enabled:s->osc1_env_enabled))return v->env;
 int a=o?s->osc2_attack:s->osc1_attack,d=o?s->osc2_decay:s->osc1_decay,su=o?s->osc2_sustain:s->osc1_sustain;
 float sus=.01f*su,*e=&v->oe[o];
 switch(v->os[o]){
 case ATTACK:*e+=1.f/(SR*.001f*clampf((float)a,1.f,2000.f));if(*e>=1.f){*e=1.f;v->os[o]=DECAY;}break;
 case DECAY:*e-=(1.f-sus)/(SR*.001f*clampf((float)d,1.f,2000.f));if(*e<=sus){*e=sus;v->os[o]=SUSTAIN;}break;
 case SUSTAIN:*e=sus;break;
 case RELEASE:*e-=v->ors[o];if(*e<=0.f){*e=0.f;v->os[o]=0;}break;
 default:return 0.f;
 }return *e;
}
static float lookup(int wave,int frame,int band,float phase){
    /* Legacy bank remains sample-for-sample identical to v0.2. */
    return sprig_table_lookup_legacy(wave,frame,band,phase);
}
static float sample_wave(Voice *v,float wave,float pos){
    int w0=(int)wave; int w1=w0<3?w0+1:3;
    int p0=(int)pos; int p1=p0<3?p0+1:3;
    float wt=wave-(float)w0,pt=pos-(float)p0;
    float a=lookup(w0,p0,v->band,v->phase);
    float b=lookup(w0,p1,v->band,v->phase);
    float c=lookup(w1,p0,v->band,v->phase);
    float d=lookup(w1,p1,v->band,v->phase);
    return (a+(b-a)*pt)*(1-wt)+(c+(d-c)*pt)*wt;
}
static float warp_phase(float p,int mode,float amount){
    p=p-(float)(int)p;if(p<0.f)p+=1.f;
    float a=clampf(amount*.01f,0.f,1.f);
    if(a<=0.f || mode==0)return p;
    if(mode==1){p=p*(1.f+3.f*a);p-=(float)(int)p;}
    else if(mode==2)p+=(p*p-p)*a*.95f;
    else if(mode==3)p+=(p-p*p)*a*.95f;
    else if(mode==4){float q=.5f+.45f*a;p=p<q?.5f*p/q:.5f+.5f*(p-q)/(1.f-q);}
    else if(mode==5){float q=.5f-.4f*a;p=p<q?.5f*p/q:.5f+.5f*(p-q)/(1.f-q);}
    else if(mode==6){float q=p*(1.f+2.f*a);int n=(int)q;p=(n&1)?1.f-(q-n):q-n;}
    else if(mode==7){float steps=64.f-60.f*a;p=(float)(int)(p*steps)/steps;}
    return clampf(p,0.f,.99999f);
}
/* Curated IDs 108..123 are reserved for the optional bank.
 * Existing preset parameters still clamp at 107, so this cannot alter
 * historical patches or expose new IDs before UI/preset migration tests. */
#ifdef SYNTH_ESIS_ENABLE_CURATED
#include "curated_tables.h"
#include "noncurated_spectral_tables.h"
static float curated_table_at(int index,int frame,int band,float phase){
    int i=(int)phase & 255;
    float frac=phase-(float)((int)phase);
    const float *row=synth_esis_curated_tables[index][frame][band];
    return row[i]+(row[(i+1)&255]-row[i])*frac;
}
/* 0..107: fixed-point offline spectral corners of the original bank.
 * 108..123: curated floating-point corners. Every oscillator source therefore
 * responds to Shift, Fold and Scramble, with no FFT/locks/allocations in DSP.
 * Historical zero-depth playback bypasses this function bit-for-bit. */
static float spectral_table_at(int mode,int index,int frame,int band,float phase){
    if(mode<0 || mode>=SYNTH_ESIS_SPECTRAL_MODES || index<0 || index>=124)
        return 0.f;
    if(frame<0 || frame>=SYNTH_ESIS_CURATED_FRAMES || band<0 || band>=SYNTH_ESIS_CURATED_BANDS)
        return 0.f;
    int i=(int)phase & 255;
    float frac=phase-(float)((int)phase);
    if(index>=108){
        const float *row=synth_esis_spectral_tables[mode][index-108][frame][band];
        return row[i]+(row[(i+1)&255]-row[i])*frac;
    }
    const int16_t *row=synth_esis_noncurated_spectral_tables[mode][index][frame][band];
    return ((float)row[i]+((float)row[(i+1)&255]-(float)row[i])*frac)*(1.f/32767.f);
}
#endif
static float table_at(int table,float position,int band,float phase){
#ifdef SYNTH_ESIS_ENABLE_CURATED
    int t=clampi(table,0,123);
#else
    int t=clampi(table,0,107);
#endif
    float pos=clampf(position,0.f,3.f);
    int p0=(int)pos,p1=p0<3?p0+1:3;float pt=pos-p0;
    /* Smoothstep only for new core tables, preserving historical preset response. */
    if(t>=100)pt=pt*pt*(3.f-2.f*pt);
    float a,b;
#ifdef SYNTH_ESIS_ENABLE_CURATED
    if(t>=108){
        a=curated_table_at(t-108,p0,band,phase);
        b=curated_table_at(t-108,p1,band,phase);
    }else
#endif
    {
        a=t<4?lookup(t,p0,band,phase):sprig_table_lookup_expanded(t-4,p0,band,phase);
        b=t<4?lookup(t,p1,band,phase):sprig_table_lookup_expanded(t-4,p1,band,phase);
    }
    return a+(b-a)*pt;
}
#ifdef SYNTH_ESIS_ENABLE_CURATED
/* Compositional spectral cube: 000 is the exact base, while 001..111
 * represent sequential Shift -> Fold -> Scramble at their full endpoints.
 * Trilinear weights keep all six encoder depths continuously interpolated
 * without spectral FFT, allocation, locks or rebuilding in render_block.
 * Tables are independently bandlimited and peak/RMS bounded offline. */
static float spectral_morph_at(int index,float position,int band,float phase,
                               float shift,float fold,float scramble){
    float a=clampf(shift,0.f,1.f),b=clampf(fold,0.f,1.f),c=clampf(scramble,0.f,1.f);
    float total=a+b+c;
    float original=table_at(index,position,band,phase);
    if(total<=0.f)return original;
    float pos=clampf(position,0.f,3.f);
    int p0=(int)pos,p1=p0<3?p0+1:3;
    float t=pos-(float)p0;t=t*t*(3.f-2.f*t);
    float result=original*(1.f-a)*(1.f-b)*(1.f-c);
    for(int mask=1;mask<=SYNTH_ESIS_SPECTRAL_MODES;mask++){
        float weight=((mask&1)?a:1.f-a)*((mask&2)?b:1.f-b)*((mask&4)?c:1.f-c);
        if(weight<=0.f)continue;
        float lo=spectral_table_at(mask-1,index,p0,band,phase);
        float hi=spectral_table_at(mask-1,index,p1,band,phase);
        result+=weight*(lo+(hi-lo)*t);
    }
    return result;
}
#else
/* Native factory-preset export builds without the optional curated table bank.
 * Keep the plugin loadable: spectral controls are neutral in this configuration.
 * The hardware build defines SYNTH_ESIS_ENABLE_CURATED and uses the full engine. */
static float spectral_morph_at(int index,float position,int band,float phase,
                               float shift,float fold,float scramble){
    (void)shift;(void)fold;(void)scramble;
    return table_at(index,position,band,phase);
}
#endif
/* Curated 9..16 need different sound physics, not eight filtered copies
 * of Metallic. Introduce low-cost, oscillator-local, noninteger-ratio phase
 * modulation for selected timbres. No FFT, memory allocation or host reads.
 * The original 0..107 bank and curated 1..8 remain untouched. */
static float curated_color_ratio(int curated){
    switch(curated){
      case 9:return 1.4142136f;   /* glass partials */
      case 10:return .501f;       /* vowel / speech-like formant motion */
      case 11:return .997f;       /* slowly drifting organic pulse */
      case 12:return 2.01f;       /* narrow resonant reed */
      case 13:return 2.4142136f;  /* inharmonic bell sidebands */
      case 14:return .721f;       /* continuously moving spectral sweep */
      case 15:return 3.171f;      /* fractured, noninteger clusters */
      case 16:return 5.731f;      /* rough, noise-like partials */
      default:return 1.f;
    }
}
static float curated_color_phase(float p,int curated,float mod,float age,int band){
    float depth=1.f;
    if(band>=7)depth=0.f;else if(band==6)depth=.12f;else if(band==5)depth=.32f;else if(band==4)depth=.65f;
    float offset=0.f;
    switch(curated){
      case 9: offset=9.f*mod;break;
      case 10:offset=4.f*mod;break;
      case 11:offset=13.f*mod;break;
      case 12:offset=2.f*mod;break;
      case 13:offset=24.f*mod/(1.f+age*4.f);break;
      case 14:offset=11.f*mod;break;
      case 15:offset=16.f*mod;break;
      case 16:offset=20.f*mod;break;
      default:break;
    }
    p+=offset*depth;
    if(p>=256.f)p-=256.f;
    if(p<0.f)p+=256.f;
    return p;
}
static float curated_color_gain(float signal,int curated,float mod,int band){
    /* Keep gain bounded; contrasts are in temporal character, not loudness. */
    if(curated==10)return signal*(.82f+.18f*(1.f+mod)*.5f);
    if(curated==11)return signal*(.87f+.13f*(1.f+mod)*.5f);
    if(curated==16)return band>=6?signal*.84f:signal*(.72f+.28f*(mod<0.f?-mod:mod));
    return signal;
}
static int16_t pcm(float f){
    float x=clampf(f*32767.0f,-32767.f,32767.f);
    return (int16_t)(x>=0.f?x+.5f:x-.5f);
}
/* Phase 5 waveform engine. Index 0 retains the original sine lookup exactly.
 * Random variants use deterministic phase-derived hashes, so modulation is
 * reproducible and does not allocate memory or depend on global RNG state. */
static float lfo_waveform_sample(int shape,float phase,unsigned cycle){
    if(shape==0)return lookup(0,0,0,phase);
    float t=phase*(1.f/256.f);

    if(shape==1)return 1.f-4.f*(t<.5f?t:1.f-t);
    if(shape==2)return 2.f*t-1.f;
    if(shape==3)return t<.5f?1.f:-1.f;
    unsigned x=(unsigned)cycle*747796405u+2891336453u;
    x^=x>>16;x*=2246822519u;x^=x>>13;
    float a=2.f*(float)(x&65535u)/65535.f-1.f;
    if(shape==4)return a;
    unsigned y=(unsigned)(cycle+1)*747796405u+2891336453u;
    y^=y>>16;y*=2246822519u;y^=y>>13;
    float b=2.f*(float)(y&65535u)/65535.f-1.f;
    float smooth=t*t*(3.f-2.f*t);
    return a+(b-a)*smooth;
}
/* Sync division 0=free, 1=quarter, 2=eighth, 3=sixteenth,
 * 4=quarter triplet, 5=eighth triplet. BPM is manual until the host
 * provides a documented tempo callback. */
static float lfo_frequency(int division,int rate,int bpm){
    if(division==0)return .06f+.12f*(float)rate;
    float beat_hz=(float)clampi(bpm,20,240)/60.f;
    switch(division){
      case 1:return beat_hz;
      case 2:return beat_hz*2.f;
      case 3:return beat_hz*4.f;
      case 4:return beat_hz*1.5f;
      default:return beat_hz*3.f;
    }
}
static void render_block(void *instance,int16_t *out,int frames){
    if(!out||frames<=0)return;
    if(frames>128)frames=128;
    Synth *s=instance;
    if(!s){for(int i=0;i<frames*2;i++)out[i]=0;return;}
    for(int j=0;j<frames;j++){
        s->smooth_wave+=.004f*((float)s->wave-s->smooth_wave);
        s->smooth_bank+=.0015f*((float)s->wt_bank-s->smooth_bank);
        s->smooth_table+=.0015f*((float)s->wavetable-s->smooth_table);
        s->smooth_shape+=.003f*((float)s->shape-s->smooth_shape);
        s->smooth_position+=.004f*(.03f*(float)s->position-s->smooth_position);
        s->smooth_g+=.004f*(sprig_cutoff_g[s->cutoff]-s->smooth_g);
        s->smooth_res+=.004f*(.01f*(float)s->resonance-s->smooth_res);
        s->smooth_level+=.004f*(.01f*(float)s->level-s->smooth_level);
        s->smooth_master_pan+=.004f*((float)s->master_pan-s->smooth_master_pan);
        /* About 5.7 ms one-pole time constant at 44.1 kHz; avoids clicks on
         * abrupt hardware encoder/preset changes without allocating or locking. */
        /* The spectral smoothers are updated AFTER both LFO samples.
         * Modulation is additive/bipolar, 50 = neutral, and clamped to 0..1.
         * Their center remains the manually selected depth; this preserves
         * the old audio path exactly when the new routes are neutral. */
        /* One global low-frequency modulator for subtle continuous wavetable motion. */
        float lfo_hz=lfo_frequency(s->lfo1_sync,s->lfo_rate,s->sync_bpm);
        s->lfo_phase+=lfo_hz*(256.f/SR);
        if(s->lfo_phase>=256.f){s->lfo_phase-=256.f;s->lfo_cycle++;}
        float lfo=lfo_waveform_sample(s->lfo1_waveform,s->lfo_phase,s->lfo_cycle);
        float lfo2_hz=lfo_frequency(s->lfo2_sync,s->lfo2_rate,s->sync_bpm);
        s->lfo2_phase+=lfo2_hz*(256.f/SR);
        if(s->lfo2_phase>=256.f){s->lfo2_phase-=256.f;s->lfo2_cycle++;}
        float lfo2=lfo_waveform_sample(s->lfo2_waveform,s->lfo2_phase,s->lfo2_cycle);
        float mod2=(.01f*(float)(s->lfo2_depth-50))*lfo2;
        float mx[18];
        for(int d=0;d<18;d++)
            mx[d]=((float)(s->matrix_depth[0][d]-50)*.02f)*lfo+
                  ((float)(s->matrix_depth[1][d]-50)*.02f)*lfo2;
        /* New spectral modulation destinations: 12..14 OSC1 and
         * 15..17 OSC2 (Shift/Fold/Scramble). +/-50 depth percentage points
         * is enough for evolving timbres without an uncontrolled jump. */
        const int spectral_base[2][3]={
            {s->osc1_spectral_shift,s->osc1_spectral_fold,s->osc1_spectral_scramble},
            {s->osc2_spectral_shift,s->osc2_spectral_fold,s->osc2_spectral_scramble}
        };
        for(int osc=0;osc<2;osc++)for(int axis=0;axis<3;axis++){
            float target=clampf((float)spectral_base[osc][axis]*.01f+
                                .5f*mx[12+3*osc+axis],0.f,1.f);
            s->smooth_spectral[osc][axis]+=.004f*(target-s->smooth_spectral[osc][axis]);
        }
        float wave=clampf(s->smooth_wave,0,3);
        float mod=(.01f*(float)(s->mod_depth-50))*lfo;
        float pos=clampf(s->smooth_position + (.015f*s->lfo_depth+.015f*s->lfo_wt_depth)*lfo+(s->mod_dest==1?mod:0.f)+(s->lfo2_dest==1?mod2:0.f)+mx[0],0,3);
        float pos2=clampf(.03f*(float)s->osc2_position + (.015f*s->lfo_depth+.015f*s->lfo_wt_depth)*lfo+(s->mod_dest==2?mod:0.f)+(s->lfo2_dest==2?mod2:0.f)+mx[1],0.f,3.f);
        float k=2.f-1.9f*clampf(s->smooth_res+mx[3]*.5f,0.f,1.f);
        float sumL=0.f,sumR=0.f;
        for(int i=0;i<SPRIG_VOICES;i++){
            Voice *v=&s->voices[i];if(!v->stage)continue;
            float env=env_next(s,v),amp1=osc_amp(s,v,0),amp2=osc_amp(s,v,1);if(!v->stage&&amp1<=0.f&&amp2<=0.f)continue;if(v->stage==RELEASE&&env<=0.f&&amp1<=0.f&&amp2<=0.f){v->stage=0;continue;}int newmode=s->mix_enabled||s->osc1_env_enabled||s->osc2_env_enabled;
            float bal=.01f*s->mix_balance,gain1=s->mix_enabled?2.f*(1.f-bal):1.f,gain2=s->mix_enabled?2.f*bal:1.f;
            float table=clampf(s->smooth_table,0.f,107.f);
            int t0=(int)table,t1=t0<107?t0+1:107;float tm=table-(float)t0;
            float p1=warp_phase(v->phase/256.f,s->osc1_warp_type,clampf((float)s->osc1_warp+mx[4]*50.f,0.f,100.f))*256.f;
            /* Spectral processing applies equally to curated and legacy sources. */
            int source1=(s->osc1_source_curated&&s->curated_osc1)?107+s->curated_osc1:t0;
            int char1=source1>=116?source1-107:0;
            float character1=char1?lookup(0,0,0,v->character_phase[0]):0.f;
            if(char1)p1=curated_color_phase(p1,char1,character1,v->character_age,v->band);
            float x=spectral_morph_at(source1,pos,v->band,p1,
                s->smooth_spectral[0][0],s->smooth_spectral[0][1],s->smooth_spectral[0][2]);
            if(!(s->osc1_source_curated&&s->curated_osc1) && tm>.00001f)
                x+=(spectral_morph_at(t1,pos,v->band,p1,
                    s->smooth_spectral[0][0],s->smooth_spectral[0][1],s->smooth_spectral[0][2])-x)*tm;
            float sh=clampf((s->smooth_shape-50.f)/50.f,-1.f,1.f);
            if(sh!=0.f){
                float ph1=p1+8.f,ph2=p1-8.f;
                if(ph1>=256.f)ph1-=256.f;if(ph2<0.f)ph2+=256.f;
                int shape_table=(s->osc1_source_curated&&s->curated_osc1)?107+s->curated_osc1:t0;
                /* Shape samples the same spectral signal as the main oscillator. */
                float left=spectral_morph_at(shape_table,pos,v->band,ph1,
                    s->smooth_spectral[0][0],s->smooth_spectral[0][1],s->smooth_spectral[0][2]);
                float right=spectral_morph_at(shape_table,pos,v->band,ph2,
                    s->smooth_spectral[0][0],s->smooth_spectral[0][1],s->smooth_spectral[0][2]);
                float avg=.5f*(left+right);
                x+=sh<0.f?(avg-x)*(-sh*.9f):(x-avg)*(sh*.85f);
            }
            if(char1)x=curated_color_gain(x,char1,character1,v->band);
            x*=.01f*clampf((float)s->osc1_volume+mx[8]*50.f,0.f,100.f);if(newmode)x*=gain1*amp1;
            float p2=warp_phase(v->phase2/256.f,s->osc2_warp_type,clampf((float)s->osc2_warp+mx[5]*50.f,0.f,100.f))*256.f;
            int source2=(s->osc2_source_curated&&s->curated_osc2)?107+s->curated_osc2:s->osc2_wavetable;
            int char2=source2>=116?source2-107:0;
            float character2=char2?lookup(0,0,0,v->character_phase[1]):0.f;
            if(char2)p2=curated_color_phase(p2,char2,character2,v->character_age,v->band);
            float second=spectral_morph_at(source2,pos2,v->band,p2,
                s->smooth_spectral[1][0],s->smooth_spectral[1][1],s->smooth_spectral[1][2])*
                (.01f*clampf((float)s->osc2_volume+mx[9]*50.f,0.f,100.f));
            if(char2)second=curated_color_gain(second,char2,character2,v->band);
            second+=lookup(1,0,v->band,v->phase2)*(.006f*s->osc2_level);if(newmode)second*=gain2*amp2;
            float pan1=.01f*clampf((float)s->osc1_pan+mx[6]*50.f,0.f,100.f),pan2=.01f*clampf((float)s->osc2_pan+mx[7]*50.f,0.f,100.f);
            float left=x*(1.f-pan1)+second*(1.f-pan2);
            float right=x*pan1+second*pan2;
            x=left+right;
            float step2=v->increment*(1.f+.0005776f*(clampf((float)s->osc2_detune+mx[11]*50.f,0.f,100.f)-50.f))*(s->osc2_octave==0?.25f:s->osc2_octave==1?.5f:s->osc2_octave==3?2.f:s->osc2_octave==4?4.f:1.f);
            float step1=v->increment*(1.f+.0005776f*(clampf((float)s->osc1_detune+mx[10]*50.f,0.f,100.f)-50.f))*(s->osc1_octave==0?.25f:s->osc1_octave==1?.5f:s->osc1_octave==3?2.f:s->osc1_octave==4?4.f:1.f);
            v->phase2+=step2;while(v->phase2>=256.f)v->phase2-=256.f;
            v->phase+=step1;while(v->phase>=256.f)v->phase-=256.f;
            v->character_phase[0]+=step1*curated_color_ratio(char1);
            v->character_phase[1]+=step2*curated_color_ratio(char2);
            for(int osc=0;osc<2;osc++)while(v->character_phase[osc]>=256.f)v->character_phase[osc]-=256.f;
            if(v->character_age<8.f)v->character_age+=1.f/SR;
            /* Soft clipping before filter: independent nonlinear shaper. */
            if(s->drive>0){float d=.03f*(float)s->drive;float u=left*(1.f+d);left=u/(1.f+(u<0.f?-u:u)*d*.25f);u=right*(1.f+d);right=u/(1.f+(u<0.f?-u:u)*d*.25f);}
            /* Triggered filter envelope (attack then decay to zero). */
            if(v->filter_stage==1){
                float denom=(float)s->filter_env_attack*.001f*SR;
                if(denom<1.f)denom=1.f;
                v->filter_env+=1.f/denom;
                if(v->filter_env>=1.f){v->filter_env=1.f;v->filter_stage=2;}
            }else if(v->filter_stage==2){
                float denom=(float)s->filter_env_decay*.001f*SR;
                if(denom<1.f)denom=1.f;
                v->filter_env-=1.f/denom;
                if(v->filter_env<=0.f){v->filter_env=0.f;v->filter_stage=0;}
            }
            float cutoff_target=(float)s->cutoff + .45f*(float)s->filter_env_amt*v->filter_env + .35f*(float)s->lfo_filter*lfo+(s->mod_dest==3?60.f*mod:0.f)+(s->lfo2_dest==3?60.f*mod2:0.f)+mx[2]*50.f;
            v->smooth_cut+=.005f*(clampf(cutoff_target,0.f,100.f)-v->smooth_cut);
            int ci=clampi((int)(v->smooth_cut+.5f),0,100);
            float g=sprig_cutoff_g[ci];
            float a1=1.f/(1.f+g*(g+k)),a2=g*a1,a3=g*a2;
            float v3=left-v->ic2;
            float v1=a1*v->ic1+a2*v3;
            float v2=v->ic2+a2*v->ic1+a3*v3;
            v->ic1=2*v1-v->ic1;
            v->ic2=2*v2-v->ic2;
            float v3r=right-v->ic2_r;
            float v1r=a1*v->ic1_r+a2*v3r;
            float v2r=v->ic2_r+a2*v->ic1_r+a3*v3r;
            v->ic1_r=2*v1r-v->ic1_r;
            v->ic2_r=2*v2r-v->ic2_r;
            /* Preserve the exact historical LP12 output for filter_type=0. */
            float hp=left-k*v1-v2,hpr=right-k*v1r-v2r;
            float filtered=v2,filteredR=v2r;
            switch(s->filter_type){
              case 1:filtered=hp;filteredR=hpr;break;             /* HP12 */
              case 2:filtered=v1;filteredR=v1r;break;           /* BP12 */
              case 3:filtered=hp+v2;filteredR=hpr+v2r;break;   /* Notch */
              case 4:filtered=v2-hp;filteredR=v2r-hpr;break;   /* Peak */
              case 5:filtered=hp+v2-k*v1;filteredR=hpr+v2r-k*v1r;break; /* Allpass */
              case 6:case 7:{
                float src=s->filter_type==6?v2:hp;
                float srcR=s->filter_type==6?v2r:hpr;
                float z=src-v->ic4,zz=srcR-v->ic4_r;
                float b1=a1*v->ic3+a2*z,b2=v->ic4+a2*v->ic3+a3*z;
                float b1r=a1*v->ic3_r+a2*zz,b2r=v->ic4_r+a2*v->ic3_r+a3*zz;
                v->ic3=2*b1-v->ic3;v->ic4=2*b2-v->ic4;
                v->ic3_r=2*b1r-v->ic3_r;v->ic4_r=2*b2r-v->ic4_r;
                filtered=s->filter_type==6?b2:src-k*b1-b2;
                filteredR=s->filter_type==6?b2r:srcR-k*b1r-b2r;
                break;
              }
            }
            sumL+=filtered*(newmode?1.f:env)*v->vel;
            sumR+=filteredR*(newmode?1.f:env)*v->vel;
        }
        /* Conservative poly mix to prevent clipping with eight voices. */
        float pan=clampf(s->smooth_master_pan,0.f,100.f);
        float balanceL=pan<=50.f?1.f:(100.f-pan)*.02f;
        float balanceR=pan>=50.f?1.f:pan*.02f;
        out[2*j]=pcm(sumL*balanceL*.48f*s->smooth_level);
        out[2*j+1]=pcm(sumR*balanceR*.48f*s->smooth_level);
    }
}
static plugin_api_v2_t api={2,create_instance,destroy_instance,on_midi,set_param,get_param,get_error,render_block};
__attribute__((visibility("default"))) plugin_api_v2_t *move_plugin_init_v2(const void *host){
    (void)host;return &api;
}
