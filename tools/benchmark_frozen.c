#include "rocketperf/combustion.h"
#include "rocketperf/frozen_nozzle.h"

#include <stdio.h>
#include <string.h>
#include <time.h>

int main(void)
{
    const RpCh4O2Feed feed = {1e7, 3.4, 298.15, 298.15, RP_FEED_GAS};
    RpCombustionResult chamber;
    RpFrozenNozzleInput input = {0};
    RpFrozenNozzleFixedResult result;
    RpError error = {0};
    double checksum = 0.0;
    clock_t started;
    const unsigned int runs = 2000U;
    if (rp_ch4_o2_equilibrium_hp(&feed, NULL, &chamber, &error) != RP_OK) {
        (void)fprintf(stderr, "%s\n", error.message); return 1;
    }
    input.chamber_temperature_k = chamber.gas.temperature_k;
    input.chamber_pressure_pa = chamber.gas.pressure_pa;
    memcpy(input.mole_fractions, chamber.gas.mole_fractions, sizeof(input.mole_fractions));
    started = clock();
    for (unsigned int i = 0U; i < runs; ++i) {
        input.area_ratio = i % 2U == 0U ? 10.0 : 40.0;
        if (rp_nozzle_solve_frozen_fixed_area(&input, 0.01, NULL, &result, &error) != RP_OK) {
            (void)fprintf(stderr, "%s\n", error.message); return 1;
        }
        checksum += result.thrust_n;
    }
    (void)printf("{\"runs\":%u,\"cpu_seconds\":%.9g,\"checksum_thrust_n\":%.17g}\n",
                 runs, (double)(clock() - started) / (double)CLOCKS_PER_SEC, checksum);
    return 0;
}
