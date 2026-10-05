#ifndef ROCKETPERF_LIQUID_NOZZLE_H
#define ROCKETPERF_LIQUID_NOZZLE_H

#include "rocketperf/frozen_nozzle.h"
#include "rocketperf/liquid_combustion.h"

typedef struct {
    RpContinuousLiquidHpResult hp;
    RpFrozenNozzleFixedResult nozzle;
} RpContinuousLiquidFixedResult;

/* Continuous liquid HP followed by the existing chamber-frozen nozzle.
 * Fixed throat and area ratio determine mass flow, thrust and Isp.
 * Both option pointers may be NULL. Every failure preserves output, including
 * successful HP followed by nozzle rejection. No pumps, shaft or cycle solve. */
RpStatus rp_ch4_o2_continuous_liquid_hp_fixed_area(
    const RpContinuousLiquidFeed *feed, double area_ratio,
    double ambient_pressure_pa, double throat_area_m2,
    const RpCombustionOptions *combustion_options,
    const RpRootOptions *nozzle_options,
    RpContinuousLiquidFixedResult *output, RpError *error);

#endif
