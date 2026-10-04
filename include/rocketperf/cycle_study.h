#ifndef ROCKETPERF_CYCLE_STUDY_H
#define ROCKETPERF_CYCLE_STUDY_H

#include "rocketperf/cycle.h"
#include <stddef.h>

typedef enum {
    RP_CYCLE_MAIN_AREA_RATIO,
    RP_CYCLE_AMBIENT_PRESSURE,
    RP_CYCLE_BRANCH_PROJECTION,
    RP_CYCLE_TURBINE_EFFICIENCY,
    RP_CYCLE_CHAMBER_TEMPERATURE,
    RP_CYCLE_OVERALL_OF,
    RP_CYCLE_FUEL_PUMP_EFFICIENCY,
    RP_CYCLE_OXIDIZER_PUMP_EFFICIENCY,
    RP_CYCLE_FIELD_COUNT
} RpCycleStudyField;

typedef struct {
    double thrust_change_n;
    double isp_change_s;
    double branch_flow_change_kg_per_s;
    double required_heat_change_w;
    double main_exit_area_m2;
    double main_exit_diameter_m;
    double main_exit_area_change_m2;
    double thrust_relative_change;
    double isp_relative_change;
    /* Relative finite-step response, not an infinitesimal derivative. */
    int elasticity_defined;
    double thrust_secant_elasticity;
    double isp_secant_elasticity;
} RpCycleStudyMetrics;

typedef struct {
    double value;
    RpStatus status;
    RpCycleInput input;
    RpCycleResult result;
    RpCycleStudyMetrics metrics;
    char message[192];
} RpCycleStudyPoint;

const char *rp_cycle_study_field_name(RpCycleStudyField field);
/* Returns NaN for a null input or invalid field. */
double rp_cycle_study_input_value(const RpCycleInput *input, RpCycleStudyField field);
/* Baseline must solve. Preflight failures do not write baseline or points;
 * count is reset to zero. Finite but unsupported scenarios are retained per
 * point. RP_OK means the grid was evaluated, not that all scenarios succeeded.
 * Same dataset/boundary; only one declared input changes. No I/O/allocation. */
RpStatus rp_cycle_scan_prescribed(const RpCycleInput *base, RpCycleStudyField field,
                                  const double *values, size_t count,
                                  RpCycleResult *baseline, RpCycleStudyPoint *points,
                                  size_t capacity, size_t *point_count, RpError *error);

#endif
