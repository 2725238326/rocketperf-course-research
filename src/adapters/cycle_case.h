#ifndef ROCKETPERF_CYCLE_CASE_H
#define ROCKETPERF_CYCLE_CASE_H

#include "rocketperf/cycle.h"

#include <stdio.h>

typedef struct {
    char id[64];
    char kind[32];
    char source_ref[256];
    RpCycleInput input;
} RpCycleCase;

/* Strict, all-required SI schema. Every load failure leaves output unchanged. */
RpStatus rp_cycle_case_load(const char *utf8_path, RpCycleCase *output, RpError *error);
/* Load and solve before writing anything. Parse/solve failure writes no bytes;
 * stream failure may leave partial JSON. Caller owns the stream and flushing. */
RpStatus rp_cycle_case_run(const char *utf8_path, FILE *stream, RpError *error);

#endif
