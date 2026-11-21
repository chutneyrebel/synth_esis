/* Native isolated spectral-bin regression tests; not linked into Move DSP. */
#include <assert.h>
#include <math.h>
#include <string.h>
#include "../src/spectral_bins.h"
static void clear(se_complex x[129]){memset(x,0,129*sizeof(*x));}
static int near(float a,float b){return fabsf(a-b)<0.0001f;}
int main(void){
    se_complex x[129],before[129],a[129],b[129];
    clear(x);x[1].re=5;x[10].im=2;x[100].re=3;
    memcpy(before,x,sizeof(x));
    se_spectral_apply(x,0,0,0,42,127,3);
    assert(memcmp(x,before,sizeof(x))==0);
    /* Protected low harmonics survive a full compound transformation. */
    se_spectral_apply(x,1,1,1,42,127,3);
    assert(near(x[1].re,5));
    assert(near(x[2].re,0));
    assert(near(x[3].re,0));
    /* Shift moves harmonic 10 to 22 at full depth. */
    clear(x);x[10].re=1;
    se_spectral_apply(x,1,0,0,42,127,3);
    assert(near(x[10].re,0)&&near(x[22].re,1));
    /* Audible triangular Fold maps the upper harmonic 100 to bin 4. */
    clear(x);x[100].re=1;
    se_spectral_apply(x,0,1,0,42,127,3);
    assert(near(x[100].re,0)&&near(x[4].re,1));
    /* Same seed => identical spectrum, different seed => different mapping. */
    clear(x);for(int k=4;k<128;k++)x[k].re=(float)k;
    memcpy(a,x,sizeof(x));memcpy(b,x,sizeof(x));
    se_spectral_apply(a,0,0,1,77,127,3);
    se_spectral_apply(b,0,0,1,77,127,3);
    assert(memcmp(a,b,sizeof(a))==0);
    memcpy(b,x,sizeof(x));
    se_spectral_apply(b,0,0,1,78,127,3);
    assert(memcmp(a,b,sizeof(a))!=0);
    /* Pitch ceiling discards out-of-range bins after nonzero transform. */
    clear(x);x[10].re=1;x[90].re=2;
    se_spectral_apply(x,1,0,0,42,32,3);
    for(int k=33;k<129;k++)assert(near(x[k].re,0)&&near(x[k].im,0));
    /* No dynamic allocations or platform dependencies. */
    return 0;
}
