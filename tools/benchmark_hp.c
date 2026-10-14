#include "rocketperf/liquid_combustion.h"
#include "rocketperf/liquid_feed.h"

#include <stdio.h>
#include <time.h>

/* Fixed 31-point liquid CH4/O2 HP sweep (O/F 1.0..4.0 at 10 MPa), repeated.
 * Reports CPU time, mean outer HP iterations and summed temperatures. */
int main(void)
{
    RpContinuousLiquidFeed feed = {0};
    RpContinuousLiquidHpResult result;
    RpError error = {0};
    unsigned long hp_iterations = 0UL;
    double checksum = 0.0;
    clock_t started;
    const unsigned int runs = 310U;
    feed.dataset_id = rp_liquid_feed_dataset_id();
    feed.enthalpy_basis_id = rp_liquid_feed_enthalpy_basis_id();
    feed.fuel_phase = RP_LIQUID_SINGLE_PHASE;
    feed.oxidizer_phase = RP_LIQUID_SINGLE_PHASE;
    feed.fuel_temperature_k = 120.0;
    feed.fuel_pressure_pa = 1e7;
    feed.oxidizer_temperature_k = 100.0;
    feed.oxidizer_pressure_pa = 1e7;
    feed.product_pressure_pa = 1e7;
    started = clock();
    for (unsigned int i = 0U; i < runs; ++i) {
        feed.oxidizer_fuel_mass_ratio = 1.0 + 0.1 * (double)(i % 31U);
        if (rp_ch4_o2_continuous_liquid_hp(&feed, NULL, &result, &error) != RP_OK) {
            (void)fprintf(stderr, "%s\n", error.message);
            return 1;
        }
        hp_iterations += result.chamber.hp_iterations;
        checksum += result.chamber.gas.temperature_k;
    }
    (void)printf("{\"runs\":%u,\"cpu_seconds\":%.9g,\"mean_hp_iterations\":%.6g,\"checksum_temperature_k\":%.17g}\n",
                 runs, (double)(clock() - started) / (double)CLOCKS_PER_SEC,
                 (double)hp_iterations / (double)runs, checksum);
    return 0;
}
