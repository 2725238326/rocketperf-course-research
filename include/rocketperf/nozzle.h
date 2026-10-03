#ifndef ROCKETPERF_NOZZLE_H
#define ROCKETPERF_NOZZLE_H

#include "rocketperf/root.h"

#include <stddef.h>

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

typedef struct {
    double area_ratio;
    double ambient_pressure_pa;
    RpStatus status;
    RpNozzleResult result;
    char message[192];
} RpNozzleStudyPoint;

typedef struct {
    const double *area_ratios;
    size_t area_ratio_count;
    const double *ambient_pressures_pa;
    size_t ambient_pressure_count;
} RpNozzleStudyGrid;

/* Reservoir-to-exit, calorically perfect gas, sonic throat, supersonic branch.
 * Initial validated domain: 1 < gamma <= 2; 1 <= Ae/At <= 1e4;
 * ambient pressure <= ideal exit pressure (matched/underexpanded).
 * No chemistry, losses, shocks, separation, cooling, cycle or reuse model.
 * Output is unchanged on failure. No allocation, I/O or global mutable state. */
RpStatus rp_nozzle_solve_ideal(const RpNozzleInput *input,
                             const RpRootOptions *options,
                             RpNozzleResult *output, RpError *error);

/* Evaluate a Cartesian area-ratio/back-pressure grid using the same L0 model.
 * Grid points outside the model domain are retained as diagnostics rather than
 * aborting the complete study. Invalid grid storage or non-finite grid values
 * still fail the call without writing points. If point_count is non-NULL, it
 * is reset to zero on entry. RP_OK means the grid was evaluated, not that every
 * point succeeded; callers must inspect statuses (numeric failures are not
 * expected domain exclusions). Output points are written in row-major order:
 * area ratio outer loop, ambient pressure inner loop. */
RpStatus rp_nozzle_scan_area_ratio_ambient(const RpNozzleInput *base,
                                           const RpNozzleStudyGrid *grid,
                                           RpNozzleStudyPoint *points,
                                           size_t point_capacity,
                                           size_t *point_count,
                                           RpError *error);

#endif
