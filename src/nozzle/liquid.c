#include "rocketperf/liquid_nozzle.h"
#include "rocketperf/numeric.h"

#include <stddef.h>

RpStatus rp_ch4_o2_continuous_liquid_hp_fixed_area(
    const RpContinuousLiquidFeed *feed, double area_ratio,
    double ambient_pressure_pa, double throat_area_m2,
    const RpCombustionOptions *combustion_options,
    const RpRootOptions *nozzle_options,
    RpContinuousLiquidFixedResult *output, RpError *error)
{
    RpContinuousLiquidFixedResult result = {0};
    RpFrozenNozzleInput input = {0};
    RpStatus status;
    if (output == NULL || !rp_isfinite(area_ratio) || area_ratio < 1.0 ||
        !rp_isfinite(ambient_pressure_pa) || ambient_pressure_pa < 0.0 ||
        !rp_isfinite(throat_area_m2) || throat_area_m2 <= 0.0) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid continuous liquid fixed-nozzle geometry.");
    }
    status = rp_ch4_o2_continuous_liquid_hp(feed, combustion_options, &result.hp, error);
    if (status != RP_OK) { return status; }
    input.chamber_temperature_k = result.hp.chamber.gas.temperature_k;
    input.chamber_pressure_pa = result.hp.chamber.gas.pressure_pa;
    for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
        input.mole_fractions[i] = result.hp.chamber.gas.mole_fractions[i];
    }
    input.area_ratio = area_ratio;
    input.ambient_pressure_pa = ambient_pressure_pa;
    status = rp_nozzle_solve_frozen_fixed_area(&input, throat_area_m2,
                                                nozzle_options, &result.nozzle, error);
    if (status != RP_OK) { return status; }
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}
