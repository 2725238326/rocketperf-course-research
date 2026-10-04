#ifndef ROCKETPERF_FROZEN_NOZZLE_H
#define ROCKETPERF_FROZEN_NOZZLE_H

#include "rocketperf/combustion.h"
#include "rocketperf/root.h"

typedef struct {
    double chamber_temperature_k;
    double chamber_pressure_pa;
    double mole_fractions[RP_CHO_SPECIES_COUNT];
    double area_ratio;
    double ambient_pressure_pa;
} RpFrozenNozzleInput;
typedef struct {
    RpGasMixture gas;
    double velocity_m_per_s;
    double mach;
    double mass_flux_kg_per_m2_s;
    double energy_residual_j_per_kg;
    double entropy_residual_j_per_kg_k;
} RpFrozenFlowStation;
typedef struct {
    RpGasMixture chamber;
    RpFrozenFlowStation throat;
    RpFrozenFlowStation exit;
    double cstar_m_per_s;
    double vacuum_effective_velocity_m_per_s;
    double effective_velocity_m_per_s;
    double thrust_coefficient;
    double continuity_relative_residual;
    double sonic_relative_residual;
} RpFrozenNozzleResult;

typedef struct {
    RpFrozenNozzleResult nozzle;
    double throat_area_m2;
    double exit_area_m2;
    double mass_flow_kg_per_s;
    double thrust_n;
    double specific_impulse_s;
} RpFrozenNozzleFixedResult;

/* Adiabatic inviscid gas, chamber-frozen composition, supersonic exit.
 * Ambient pressure must not exceed exit pressure. No shocks/separation.
 * NULL options uses model defaults. Failure leaves output unchanged. */
RpStatus rp_nozzle_solve_frozen(const RpFrozenNozzleInput *input,
                                const RpRootOptions *options,
                                RpFrozenNozzleResult *output, RpError *error);

/* Fixed throat area and input area ratio; derives mass flow from choked flux.
 * Single nozzle only: not shaft, feed-system or full-cycle hardware closure.
 * Same supported flow domain and failure-keeps-output contract as above. */
RpStatus rp_nozzle_solve_frozen_fixed_area(const RpFrozenNozzleInput *input,
                                           double throat_area_m2,
                                           const RpRootOptions *options,
                                           RpFrozenNozzleFixedResult *output,
                                           RpError *error);

#endif
