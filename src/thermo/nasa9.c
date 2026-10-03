#include "rocketperf/thermo.h"
#include "rocketperf/numeric.h"

#include <math.h>
#include <stddef.h>

static int finite_range(const RpNasa9Range *range)
{
    unsigned int i;
    if (range == NULL || !rp_isfinite(range->t_min_k) || !rp_isfinite(range->t_max_k) ||
        range->t_min_k <= 0.0 || range->t_max_k <= range->t_min_k ||
        !rp_isfinite(range->h_offset_j_per_kg) || !rp_isfinite(range->s_offset_j_per_kg_k)) {
        return 0;
    }
    for (i = 0U; i < 9U; ++i) {
        if (!rp_isfinite(range->coefficients[i])) {
            return 0;
        }
    }
    return 1;
}

static const RpNasa9Range *select_range(const RpNasa9Species *species, double temperature_k)
{
    unsigned int i;
    for (i = 0U; i < species->range_count; ++i) {
        const RpNasa9Range *range = &species->ranges[i];
        const int last = i + 1U == species->range_count;
        if ((temperature_k >= range->t_min_k) &&
            ((temperature_k < range->t_max_k) || (last && temperature_k <= range->t_max_k))) {
            return range;
        }
    }
    return NULL;
}

RpStatus rp_nasa9_evaluate(const RpNasa9Species *species, double temperature_k,
                           RpThermoState *state, RpError *error)
{
    const RpNasa9Range *range;
    const double *a;
    const double t = temperature_k;
    const double t2 = t * t;
    const double t3 = t2 * t;
    const double t4 = t3 * t;
    const double inv_t = 1.0 / t;
    double r_specific;
    double cp_over_r;
    double h_over_rt;
    double s_over_r;

    if (species == NULL || state == NULL || species->id == NULL || species->ranges == NULL ||
        species->range_count == 0U || !rp_isfinite(species->molar_mass_kg_per_kmol) ||
        species->molar_mass_kg_per_kmol <= 0.0 || !rp_isfinite(temperature_k) || temperature_k <= 0.0) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "invalid NASA9 input");
    }
    range = select_range(species, temperature_k);
    if (range == NULL) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "temperature outside NASA9 ranges");
    }
    if (!finite_range(range)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "invalid NASA9 coefficients");
    }
    a = range->coefficients;
    r_specific = 8314.46261815324 / species->molar_mass_kg_per_kmol;
    cp_over_r = a[0] * inv_t * inv_t + a[1] * inv_t + a[2] + a[3] * t + a[4] * t2 +
                 a[5] * t3 + a[6] * t4;
    h_over_rt = -a[0] * inv_t * inv_t + a[1] * log(t) * inv_t + a[2] + 0.5 * a[3] * t +
                (a[4] * t2) / 3.0 + 0.25 * a[5] * t3 + 0.2 * a[6] * t4 + a[7] * inv_t;
    s_over_r = -0.5 * a[0] * inv_t * inv_t - a[1] * inv_t + a[2] * log(t) + a[3] * t +
               0.5 * a[4] * t2 + (a[5] * t3) / 3.0 + 0.25 * a[6] * t4 + a[8];
    state->cp_j_per_kg_k = r_specific * cp_over_r;
    state->h_j_per_kg = r_specific * t * h_over_rt + range->h_offset_j_per_kg;
    state->s_j_per_kg_k = r_specific * s_over_r + range->s_offset_j_per_kg_k;
    if (!rp_isfinite(state->cp_j_per_kg_k) || !rp_isfinite(state->h_j_per_kg) ||
        !rp_isfinite(state->s_j_per_kg_k) || state->cp_j_per_kg_k <= 0.0) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "NASA9 evaluation is not finite/positive");
    }
    rp_error_clear(error);
    return RP_OK;
}


