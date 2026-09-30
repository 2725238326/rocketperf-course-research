#ifndef ROCKETPERF_NOZZLE_H
#define ROCKETPERF_NOZZLE_H

#include "rocketperf/root.h"

typedef struct {
    double gamma;
    double gas_constant_j_kg_k;
    double stagnation_temperature_k;
    double stagnation_pressure_pa;
    double area_ratio;
    double throat_area_m2;
    double ambient_pressure_pa;
} RpNozzleInput;

typedef struct {
    double exit_mach;
    double exit_temperature_k;
    double exit_pressure_pa;
    double exit_velocity_m_s;
    double exit_area_m2;
    double characteristic_velocity_m_s;
    double mass_flow_kg_s;
    double thrust_n;
    double thrust_coefficient;
    double specific_impulse_s;
    double relative_area_residual;
    unsigned int root_iterations;
} RpNozzleResult;

/* Reservoir-to-exit, calorically perfect gas, sonic throat, supersonic branch.
 * Initial validated domain: 1 < gamma <= 2; 1 <= Ae/At <= 1e4;
 * ambient pressure <= ideal exit pressure (matched/underexpanded).
 * No chemistry, losses, shocks, separation, cooling, cycle or reuse model.
 * Output is unchanged on failure. No allocation, I/O or global mutable state. */
RpStatus rp_nozzle_solve_ideal(const RpNozzleInput *input,
                             const RpRootOptions *options,
                             RpNozzleResult *output, RpError *error);

#endif
