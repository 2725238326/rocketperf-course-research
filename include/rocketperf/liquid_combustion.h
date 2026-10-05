#ifndef ROCKETPERF_LIQUID_COMBUSTION_H
#define ROCKETPERF_LIQUID_COMBUSTION_H

#include "rocketperf/combustion.h"
#include "rocketperf/liquid_feed.h"

typedef struct {
    const char *dataset_id;
    const char *enthalpy_basis_id;
    RpLiquidFeedPhase fuel_phase;
    RpLiquidFeedPhase oxidizer_phase;
    double fuel_temperature_k;
    double fuel_pressure_pa;
    double oxidizer_temperature_k;
    double oxidizer_pressure_pa;
    double product_pressure_pa;
    double oxidizer_fuel_mass_ratio;
} RpContinuousLiquidFeed;

typedef struct {
    RpLiquidFeedState fuel;
    RpLiquidFeedState oxidizer;
    double fuel_mass_fraction;
    double oxidizer_mass_fraction;
    double mixture_h_j_per_kg;
    double element_inventory_kmol_per_kg[RP_CHO_ELEMENT_COUNT];
} RpContinuousLiquidInlet;

typedef struct {
    RpContinuousLiquidInlet inlet;
    RpCombustionResult chamber;
} RpContinuousLiquidHpResult;

/* Continuous single-phase table -> nine-species ideal-gas HP.
 * Fuel and oxidizer pressures are table-query pressures; product pressure is
 * the ideal-gas chamber pressure. Q=0, no inlet kinetic energy or shaft work.
 * Requires the pinned table and enthalpy basis, with both single-liquid phases.
 * Density retains EOS mass; chemical h and inventory use CEA mass.
 * No pump path, injector feasibility, phase flash or cycle closure is solved.
 * NULL options uses defaults; every failure preserves output. */
RpStatus rp_ch4_o2_continuous_liquid_inlet(const RpContinuousLiquidFeed *feed,
                                           RpContinuousLiquidInlet *output,
                                           RpError *error);
RpStatus rp_ch4_o2_continuous_liquid_hp(const RpContinuousLiquidFeed *feed,
                                        const RpCombustionOptions *options,
                                        RpContinuousLiquidHpResult *output,
                                        RpError *error);
#endif
