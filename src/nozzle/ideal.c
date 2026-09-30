#include "rocketperf/nozzle.h"
#include "rocketperf/version.h"
#include "rocketperf/numeric.h"

#include <math.h>
#include <stddef.h>

typedef struct {
    double gamma;
    double log_area_ratio;
} AreaEquation;

static double area_residual(double mach, const void *context)
{
    const AreaEquation *equation = context;
    const double delta = equation->gamma - 1.0;
    const double exponent = (equation->gamma + 1.0) / (2.0 * delta);
    /* log1p avoids cancellation in the near-sonic area/Mach relation. */
    return -log(mach) + exponent *
           (log1p(0.5 * delta * mach * mach) - log1p(0.5 * delta)) -
           equation->log_area_ratio;
}

static int positive_finite(double value)
{
    return rp_isfinite(value) && value > 0.0;
}

RpStatus rp_nozzle_solve_ideal(const RpNozzleInput *input,
                             const RpRootOptions *options,
                             RpNozzleResult *output, RpError *error)
{
    RpNozzleResult result = {0};
    RpRootResult root = {1.0, 0.0, 0U};
    AreaEquation equation;
    double temperature_factor;
    double delta;
    double upper = 2.0;
    RpStatus status;
    if (input == NULL || output == NULL) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Nozzle input and output are required.");
    }
    if (!rp_isfinite(input->gamma) || input->gamma <= 1.0 || input->gamma > 2.0 ||
        !positive_finite(input->gas_constant_j_kg_k) ||
        !positive_finite(input->stagnation_temperature_k) ||
        !positive_finite(input->stagnation_pressure_pa) ||
        !positive_finite(input->throat_area_m2) ||
        !rp_isfinite(input->area_ratio) || input->area_ratio < 1.0 || input->area_ratio > 1e4 ||
        !rp_isfinite(input->ambient_pressure_pa) || input->ambient_pressure_pa < 0.0) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Invalid SI inputs or outside gamma/area-ratio domain.");
    }
    equation.gamma = input->gamma;
    equation.log_area_ratio = log(input->area_ratio);
    while (area_residual(upper, &equation) < 0.0 && upper < 512.0) {
        upper *= 2.0;
    }
    status = rp_root_bisect(area_residual, &equation, 1.0, upper, options, &root, error);
    if (status != RP_OK) {
        return status;
    }
    result.relative_area_residual = fabs(expm1(root.residual));
    if (!rp_isfinite(result.relative_area_residual) || result.relative_area_residual > 1e-8) {
        return rp_error_set(error, RP_NO_CONVERGENCE, "Nozzle area relation exceeds residual tolerance.");
    }
    delta = input->gamma - 1.0;
    temperature_factor = 1.0 + 0.5 * delta * root.x * root.x;
    result.exit_mach = root.x;
    result.root_iterations = root.iterations;
    result.exit_temperature_k = input->stagnation_temperature_k / temperature_factor;
    result.exit_pressure_pa = input->stagnation_pressure_pa *
                             exp(-input->gamma / delta * log1p(0.5 * delta * root.x * root.x));
    if (input->ambient_pressure_pa > result.exit_pressure_pa * (1.0 + 1e-10)) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Overexpanded/back-pressure flow is not supported by this model.");
    }
    result.exit_velocity_m_s = root.x * sqrt(input->gamma * input->gas_constant_j_kg_k *
                                            result.exit_temperature_k);
    result.exit_area_m2 = input->throat_area_m2 * input->area_ratio;
    result.characteristic_velocity_m_s =
        sqrt(input->gas_constant_j_kg_k * input->stagnation_temperature_k / input->gamma) *
        exp((input->gamma + 1.0) / (2.0 * delta) * log1p(0.5 * delta));
    result.mass_flow_kg_s = input->stagnation_pressure_pa * input->throat_area_m2 /
                            result.characteristic_velocity_m_s;
    result.thrust_n = result.mass_flow_kg_s * result.exit_velocity_m_s +
                      (result.exit_pressure_pa - input->ambient_pressure_pa) * result.exit_area_m2;
    result.thrust_coefficient = result.thrust_n /
                               (input->stagnation_pressure_pa * input->throat_area_m2);
    result.specific_impulse_s = result.thrust_n /
                               (result.mass_flow_kg_s * RP_STANDARD_GRAVITY_M_S2);
    if (!positive_finite(result.exit_temperature_k) || !positive_finite(result.exit_pressure_pa) ||
        !positive_finite(result.exit_velocity_m_s) || !positive_finite(result.exit_area_m2) ||
        !positive_finite(result.characteristic_velocity_m_s) || !positive_finite(result.mass_flow_kg_s) ||
        !positive_finite(result.thrust_n) || !positive_finite(result.thrust_coefficient) ||
        !positive_finite(result.specific_impulse_s)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Derived result overflowed, underflowed or became invalid.");
    }
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}
