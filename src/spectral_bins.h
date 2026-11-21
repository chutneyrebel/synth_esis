/* Synth_esis isolated spectral-bin prototype, Phase B.
 * No host dependencies, allocation, FFT or live DSP integration.
 * Caller owns 129 complex positive-frequency bins (0..128).
 * The operators compose in place on the supplied spectrum.
 */
#ifndef SYNTH_ESIS_SPECTRAL_BINS_H
#define SYNTH_ESIS_SPECTRAL_BINS_H
#define SE_BINS 128
typedef struct { float re, im; } se_complex;
static inline se_complex se_mix(se_complex a,se_complex b,float d) {
    se_complex v={a.re+(b.re-a.re)*d,a.im+(b.im-a.im)*d};return v;
}
static inline float se_depth(float d) {return d<0.f?0.f:d>1.f?1.f:d;}
static inline int se_ceiling(int k) {return k<1?1:k>127?127:k;}
static inline void se_spectral_apply(se_complex x[129],float shift,float fold,float scramble,
                                      unsigned seed,int ceiling,int protect) {
    se_complex y[129];
    float ds=se_depth(shift),df=se_depth(fold),dc=se_depth(scramble);
    int top=se_ceiling(ceiling),p=protect<0?0:protect>top?top:protect;
    /* Zero-depth is bit-exact, including DC and Nyquist. */
    if(ds==0.f && df==0.f && dc==0.f)return;
    /* Shift: quantized upward harmonic remapping, preserving bins 1..p.
     * At depth 1, shift by 12 bins; depth controls wet/dry and distance.
     */
    if(ds>0.f){
        /* Keep Shift audible at upper pitch bands instead of dropping
         * every harmonic beyond a fixed twelve-bin displacement. */
        int distance=(int)(12.f*ds+0.5f);
        int max_distance=(top-p)/3;
        if(max_distance<1)max_distance=1;
        if(distance>max_distance)distance=max_distance;
        for(int k=0;k<129;k++){y[k]=x[k];if(k>p && k<=top){y[k].re=0;y[k].im=0;}}
        for(int k=p+1;k<=top;k++){
            int target=k+distance;
            if(target<=top){y[target].re+=x[k].re;y[target].im+=x[k].im;}
        }
        for(int k=p+1;k<=top;k++)x[k]=se_mix(x[k],y[k],ds);
    }
    /* Fold: reflect upper harmonics about midpoint, accumulating collisions. */
    if(df>0.f && top>p+1){
        /* Previous halfway pivot only touched nearly silent upper bins.
         * Repeated triangular folding starts near harmonic 12, preserving
         * bins 1..3 but acting on the audible midrange. */
        int span=(top-p)/2;
        if(span>8)span=8;
        if(span<1)span=1;
        int period=2*span;
        for(int k=0;k<129;k++){y[k]=x[k];if(k>p && k<=top){y[k].re=0;y[k].im=0;}}
        for(int k=p+1;k<=top;k++){
            int offset=(k-p-1)%period;
            int target=p+1+(offset<=span?offset:period-offset);
            y[target].re+=x[k].re;y[target].im+=x[k].im;
        }
        for(int k=p+1;k<=top;k++)x[k]=se_mix(x[k],y[k],df);
    }
    /* Scramble: deterministic Fisher-Yates permutation of complex bins.
     * Seed is local; no mutable global RNG and no heap allocation.
     */
    if(dc>0.f && top>p+1){
        unsigned char indices[128];
        int count=top-p;
        for(int i=0;i<count;i++)indices[i]=(unsigned char)(p+1+i);
        unsigned state=seed?seed:0x9e3779b9u;
        for(int i=count-1;i>0;i--){
            state^=state<<13;state^=state>>17;state^=state<<5;
            unsigned j=state%(unsigned)(i+1);
            unsigned char tmp=indices[i];indices[i]=indices[j];indices[j]=tmp;
        }
        for(int i=0;i<count;i++)y[p+1+i]=x[indices[i]];
        for(int k=p+1;k<=top;k++)x[k]=se_mix(x[k],y[k],dc);
    }
    for(int k=top+1;k<128;k++){x[k].re=0;x[k].im=0;}
    x[128].re=0;x[128].im=0;
}
#endif
