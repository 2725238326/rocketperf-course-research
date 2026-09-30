#ifndef ROCKETPERF_ROOT_H
#define ROCKETPERF_ROOT_H

#include "rocketperf/status.h"

typedef double (*RpScalarFunction)(double x, const void *context);

typedef struct {
    double x_absolute_tolerance;
    double x_relative_tolerance;
    double f_absolute_tolerance;
    unsigned int max_iterations;
} RpRootOptions;

typedef struct {
    double x;
    double residual;
    unsigned int iterations;
} RpRootResult;

RpRootOptions rp_root_default_options(void);

/* Continuous f on a finite bracket is the caller's responsibility.
 * NULL options uses defaults. Output is unchanged on failure. */
RpStatus rp_root_bisect(RpScalarFunction function, const void *context,
                       double lower, double upper,
                       const RpRootOptions *options,
                       RpRootResult *output, RpError *error);

#endif
