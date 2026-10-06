#ifndef ROCKETPERF_PROPELLANT_CASE_H
#define ROCKETPERF_PROPELLANT_CASE_H

#include "rocketperf/propellant_study.h"

typedef struct {
    char id[64];
    char source_ref[256];
    RpPropellantComparisonInput input;
} RpPropellantCase;

/* Parsing does not solve the model. On failure, output is unchanged. */
RpStatus rp_propellant_case_load(const char *utf8_path,
                                 RpPropellantCase *output,
                                 RpError *error);

#endif
