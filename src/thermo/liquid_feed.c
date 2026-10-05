#include "rocketperf/liquid_feed.h"
#include "rocketperf/numeric.h"

#include <stddef.h>
#include <string.h>

typedef struct {
    const char *id;
    double eos_molar_mass_kg_per_mol;
    double chemical_molar_mass_kg_per_mol;
    size_t temperature_count;
    const double *temperatures_k;
    size_t pressure_count;
    const double *pressures_pa;
    const double (*points)[2];
} RpLiquidTable;

#include "liquid_feed_generated.h"

const char *rp_liquid_feed_dataset_id(void)
{
    return RP_LIQUID_DATASET_ID;
}

const char *rp_liquid_feed_reference_sha256(void)
{
    return RP_LIQUID_REFERENCE_SHA256;
}

static size_t interval(const double *axis, size_t count, double value)
{
    /* Domain is checked first; last endpoint belongs to the last cell. */
    size_t index = 0U;
    while (index + 2U < count && value >= axis[index + 1U]) { ++index; }
    return index;
}

RpStatus rp_liquid_feed_evaluate(const RpLiquidFeedQuery *query,
                                  RpLiquidFeedState *output, RpError *error)
{
    const RpLiquidTable *table = NULL;
    RpLiquidFeedState result = {0};
    size_t t_index, p_index;
    double t_weight, p_weight;
    double interpolated[2] = {0.0, 0.0};
    if (query == NULL || output == NULL || query->dataset_id == NULL || query->fluid_id == NULL ||
        !rp_isfinite(query->temperature_k) || !rp_isfinite(query->pressure_pa) ||
        query->temperature_k <= 0.0 || query->pressure_pa <= 0.0) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid liquid table query or output.");
    }
    if (strcmp(query->dataset_id, RP_LIQUID_DATASET_ID) != 0 ||
        query->phase != RP_LIQUID_SINGLE_PHASE) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Requires the pinned single-phase liquid table and phase.");
    }
    for (size_t i = 0U; i < sizeof(rp_liquid_tables) / sizeof(rp_liquid_tables[0]); ++i) {
        if (strcmp(query->fluid_id, rp_liquid_tables[i].id) == 0) {
            table = &rp_liquid_tables[i];
            break;
        }
    }
    if (table == NULL) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Liquid table supports only Methane and Oxygen.");
    }
    if (query->temperature_k < table->temperatures_k[0] ||
        query->temperature_k > table->temperatures_k[table->temperature_count - 1U] ||
        query->pressure_pa < table->pressures_pa[0] ||
        query->pressure_pa > table->pressures_pa[table->pressure_count - 1U]) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Outside the fixed single-phase liquid rectangle; no extrapolation.");
    }
    t_index = interval(table->temperatures_k, table->temperature_count, query->temperature_k);
    p_index = interval(table->pressures_pa, table->pressure_count, query->pressure_pa);
    t_weight = (query->temperature_k - table->temperatures_k[t_index]) /
        (table->temperatures_k[t_index + 1U] - table->temperatures_k[t_index]);
    p_weight = (query->pressure_pa - table->pressures_pa[p_index]) /
        (table->pressures_pa[p_index + 1U] - table->pressures_pa[p_index]);
    for (size_t field = 0U; field < 2U; ++field) {
        for (size_t t = 0U; t < 2U; ++t) {
            for (size_t p = 0U; p < 2U; ++p) {
                const double weight = (t == 0U ? 1.0 - t_weight : t_weight) *
                    (p == 0U ? 1.0 - p_weight : p_weight);
                interpolated[field] += weight * table->points[
                    (t_index + t) * table->pressure_count + p_index + p][field];
            }
        }
    }
    result.density_kg_per_m3 = interpolated[0];
    result.h_j_per_mol = interpolated[1];
    result.eos_molar_mass_kg_per_mol = table->eos_molar_mass_kg_per_mol;
    result.chemical_molar_mass_kg_per_mol = table->chemical_molar_mass_kg_per_mol;
    result.h_j_per_kg = result.h_j_per_mol / result.chemical_molar_mass_kg_per_mol;
    if (!rp_isfinite(result.density_kg_per_m3) || result.density_kg_per_m3 <= 0.0 ||
        !rp_isfinite(result.h_j_per_mol) || !rp_isfinite(result.h_j_per_kg)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Invalid interpolated liquid state.");
    }
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}
