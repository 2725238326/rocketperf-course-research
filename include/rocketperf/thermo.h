#ifndef ROCKETPERF_THERMO_H
#define ROCKETPERF_THERMO_H

#include "rocketperf/status.h"

#define RP_NASA9_MAX_RANGES 16U
#define RP_UNIVERSAL_GAS_CONSTANT_J_KMOL_K 8314.5100

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
RpStatus rp_nasa9_validate(const RpNasa9Species *species, RpError *error);
const RpNasa9Species *rp_thermo_find_species(const char *id);
const char *rp_thermo_dataset_id(void);
double rp_thermo_reference_pressure_pa(void);

#endif
