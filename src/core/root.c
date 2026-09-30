#include "rocketperf/root.h"
#include "rocketperf/numeric.h"

#include <math.h>
#include <stddef.h>

RpRootOptions rp_root_default_options(void)
{
    const RpRootOptions options = {1e-12, 1e-12, 1e-12, 200U};
    return options;
}

static int same_sign(double a, double b)
{
    return (a < 0.0) == (b < 0.0);
}

static RpStatus success(double x, double residual, unsigned int iterations,
                        RpRootResult *output, RpError *error)
{
    const RpRootResult result = {x, residual, iterations};
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}

RpStatus rp_root_bisect(RpScalarFunction function, const void *context,
                       double lower, double upper,
                       const RpRootOptions *options,
                       RpRootResult *output, RpError *error)
{
    const RpRootOptions policy = options != NULL ? *options : rp_root_default_options();
    double f_lower;
    double f_upper;
    if (function == NULL || output == NULL || !rp_isfinite(lower) ||
        !rp_isfinite(upper) || lower >= upper ||
        !rp_isfinite(policy.x_absolute_tolerance) || policy.x_absolute_tolerance <= 0.0 ||
        !rp_isfinite(policy.x_relative_tolerance) || policy.x_relative_tolerance < 0.0 ||
        !rp_isfinite(policy.f_absolute_tolerance) || policy.f_absolute_tolerance < 0.0 ||
        policy.max_iterations == 0U || policy.max_iterations > 100000U) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid root bracket, options or output.");
    }
    f_lower = function(lower, context);
    f_upper = function(upper, context);
    if (!rp_isfinite(f_lower) || !rp_isfinite(f_upper)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite function value at bracket endpoint.");
    }
    if (fabs(f_lower) <= policy.f_absolute_tolerance) {
        return success(lower, f_lower, 0U, output, error);
    }
    if (fabs(f_upper) <= policy.f_absolute_tolerance) {
        return success(upper, f_upper, 0U, output, error);
    }
    if (same_sign(f_lower, f_upper)) {
        return rp_error_set(error, RP_NOT_BRACKETED, "Endpoint function values must have opposite signs.");
    }
    for (unsigned int iteration = 1U; iteration <= policy.max_iterations; ++iteration) {
        const double middle = 0.5 * lower + 0.5 * upper;
        const double value = function(middle, context);
        const double half_width = fabs(0.5 * upper - 0.5 * lower);
        const double tolerance = policy.x_absolute_tolerance +
                                 policy.x_relative_tolerance * fabs(middle);
        if (!rp_isfinite(value) || !rp_isfinite(tolerance)) {
            return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite value during root iteration.");
        }
        if (fabs(value) <= policy.f_absolute_tolerance || half_width <= tolerance) {
            return success(middle, value, iteration, output, error);
        }
        if (middle == lower || middle == upper) {
            return rp_error_set(error, RP_NO_CONVERGENCE, "Floating-point bracket stagnated before tolerance.");
        }
        if (same_sign(f_lower, value)) {
            lower = middle;
            f_lower = value;
        } else {
            upper = middle;
        }
    }
    return rp_error_set(error, RP_NO_CONVERGENCE, "Root iteration budget exhausted.");
}
