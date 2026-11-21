/* Phase B isolated microbenchmark. Not a Move CPU benchmark.
 * Reports native host throughput and checks bounded processing cost.
 */
#include <stdio.h>
#include <time.h>
#include "../src/spectral_bins.h"
#define ITERATIONS 10000
int main(void){
    se_complex bins[129];
    volatile float checksum=0.f;
    clock_t start=clock();
    for(int n=0;n<ITERATIONS;n++){
        for(int k=0;k<129;k++){bins[k].re=(float)((k*7+n)%29)*.01f;bins[k].im=(float)(k%13)*.01f;}
        se_spectral_apply(bins,.7f,.8f,.6f,(unsigned)n,96,3);
        checksum+=bins[7].re;
    }
    clock_t elapsed=clock()-start;
    double microseconds=(double)elapsed*1000000.0/(CLOCKS_PER_SEC*ITERATIONS);
    printf("spectral engine: %.3f us/call, %.0f calls/s (host CPU), checksum %.5f, bin bytes %zu\\n",
           microseconds,microseconds>0?1000000.0/microseconds:0.0,
           (double)checksum,sizeof(bins));
    return 0;
}
