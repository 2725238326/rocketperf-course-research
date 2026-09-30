#ifndef ROCKETPERF_NUMERIC_H
#define ROCKETPERF_NUMERIC_H

#include <float.h>

/* Typed finite check avoids MinGW's type-generic macro conversion warnings.
 * Ordered comparisons reject both infinities and NaNs without narrowing. */
static inline int rp_isfinite(double value)
{
    return value >= -DBL_MAX && value <= DBL_MAX;
}

#endif
