#ifndef ROCKETPERF_THERMO_H
#define ROCKETPERF_THERMO_H

#include "rocketperf/status.h"

typedef struct {
    double t_min_k;
    double t_max_k;
    double coefficients[9];
    double h_offset_j_per_kg;
    double s_offset_j_per_kg_k;
} RpNasa9Range;

typedef struct {
    const char *id;
    double molar_mass_kg_per_kmol;
    unsigned int range_count;
    const RpNasa9Range *ranges;
} RpNasa9Species;

typedef struct {
    double cp_j_per_kg_k;
    double h_j_per_kg;
    double s_j_per_kg_k;
} RpThermoState;

RpStatus rp_nasa9_evaluate(const RpNasa9Species *species, double temperature_k,
                           RpThermoState *state, RpError *error);

#endif
