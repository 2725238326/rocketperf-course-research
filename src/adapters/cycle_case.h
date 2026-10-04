#ifndef ROCKETPERF_CYCLE_CASE_H
#define ROCKETPERF_CYCLE_CASE_H

#include "rocketperf/cycle.h"
#include "rocketperf/cycle_study.h"

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
/* Evaluate before writing; caller owns stream/flush. Failed points carry status
 * and error, never a successful physical result. */
RpStatus rp_cycle_case_study(const char *utf8_path, RpCycleStudyField field,
                             const double *values, size_t count, FILE *stream, RpError *error);

#endif
