#include "rocketperf/thermo.h"
#include "rocketperf/numeric.h"

#include <math.h>
#include <stddef.h>

RpStatus rp_nasa9_validate(const RpNasa9Species *species, RpError *error)
{
    if (species == NULL || species->id == NULL || species->id[0] == '\0' ||
        species->ranges == NULL || species->range_count == 0U ||
        species->range_count > RP_NASA9_MAX_RANGES ||
        !rp_isfinite(species->molar_mass_kg_per_kmol) || species->molar_mass_kg_per_kmol <= 0.0) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid NASA9 species metadata.");
    }
    for (unsigned int index = 0U; index < species->range_count; ++index) {
        const RpNasa9Range *range = &species->ranges[index];
        if (!rp_isfinite(range->t_min_k) || !rp_isfinite(range->t_max_k) ||
            range->t_min_k <= 0.0 || range->t_max_k <= range->t_min_k ||
            !rp_isfinite(range->h_offset_j_per_kg) || !rp_isfinite(range->s_offset_j_per_kg_k) ||
            (index != 0U && species->ranges[index - 1U].t_max_k != range->t_min_k)) {
            return rp_error_set(error, RP_INVALID_ARGUMENT, "NASA9 ranges must be finite, ordered and contiguous.");
        }
        for (unsigned int coefficient = 0U; coefficient < 9U; ++coefficient) {
            if (!rp_isfinite(range->coefficients[coefficient])) {
                return rp_error_set(error, RP_INVALID_ARGUMENT, "NASA9 coefficients must be finite.");
            }
        }
    }
    rp_error_clear(error);
    return RP_OK;
}

RpStatus rp_nasa9_evaluate(const RpNasa9Species *species, double temperature_k,
                           RpThermoState *state, RpError *error)
{
    const RpNasa9Range *range = NULL;
    RpThermoState candidate;
    RpStatus status;
    double inverse_temperature;
    double log_temperature;
    double specific_gas_constant;
    const double *coefficients;
    if (state == NULL || !rp_isfinite(temperature_k) || temperature_k <= 0.0) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid NASA9 temperature or output.");
    }
    status = rp_nasa9_validate(species, error);
    if (status != RP_OK) { return status; }
    for (unsigned int index = 0U; index < species->range_count; ++index) {
        const RpNasa9Range *interval = &species->ranges[index];
        if (temperature_k >= interval->t_min_k &&
            (temperature_k < interval->t_max_k ||
             (index + 1U == species->range_count && temperature_k == interval->t_max_k))) {
            range = interval;
            break;
        }
    }
    if (range == NULL) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Temperature outside NASA9 fit intervals.");
    }
    coefficients = range->coefficients;
    inverse_temperature = 1.0 / temperature_k;
    log_temperature = log(temperature_k);
    specific_gas_constant = RP_UNIVERSAL_GAS_CONSTANT_J_KMOL_K / species->molar_mass_kg_per_kmol;
    candidate.cp_j_per_kg_k = specific_gas_constant *
        (coefficients[0] * inverse_temperature * inverse_temperature + coefficients[1] * inverse_temperature +
         coefficients[2] + temperature_k * (coefficients[3] + temperature_k *
         (coefficients[4] + temperature_k * (coefficients[5] + temperature_k * coefficients[6]))));
    candidate.h_j_per_kg = specific_gas_constant *
        (-coefficients[0] * inverse_temperature + coefficients[1] * log_temperature + coefficients[7] +
         temperature_k * (coefficients[2] + temperature_k * (coefficients[3] / 2.0 + temperature_k *
         (coefficients[4] / 3.0 + temperature_k * (coefficients[5] / 4.0 + temperature_k * coefficients[6] / 5.0))))) +
        range->h_offset_j_per_kg;
    candidate.s_j_per_kg_k = specific_gas_constant *
        (-coefficients[0] * inverse_temperature * inverse_temperature / 2.0 - coefficients[1] * inverse_temperature +
         coefficients[2] * log_temperature + coefficients[8] + temperature_k *
         (coefficients[3] + temperature_k * (coefficients[4] / 2.0 + temperature_k *
         (coefficients[5] / 3.0 + temperature_k * coefficients[6] / 4.0)))) + range->s_offset_j_per_kg_k;
    if (!rp_isfinite(candidate.cp_j_per_kg_k) || !rp_isfinite(candidate.h_j_per_kg) ||
        !rp_isfinite(candidate.s_j_per_kg_k) || candidate.cp_j_per_kg_k <= 0.0) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "NASA9 evaluation is non-finite or cp is not positive.");
    }
    *state = candidate;
    rp_error_clear(error);
    return RP_OK;
}
