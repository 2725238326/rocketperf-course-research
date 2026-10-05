#include "rocketperf/combustion.h"
#include "rocketperf/numeric.h"
#include "reactants_generated.h"

#include <stddef.h>
#include <string.h>

const char *rp_anchor_dataset_id(void)
{
    return RP_ANCHOR_DATASET_ID;
}

RpStatus rp_ch4_o2_anchor_inlet(const RpCh4O2AnchorFeed *feed,
                                RpAnchorInlet *output, RpError *error)
{
    RpAnchorInlet result = {0};
    const RpAssignedReactant *fuel = &rp_assigned_reactants[0];
    const RpAssignedReactant *oxidizer = &rp_assigned_reactants[1];
    double fuel_fraction;
    if (feed == NULL || output == NULL || feed->fuel_anchor_id == NULL ||
        feed->oxidizer_anchor_id == NULL || !rp_isfinite(feed->pressure_pa) ||
        !rp_isfinite(feed->oxidizer_fuel_mass_ratio) || !rp_isfinite(feed->fuel_temperature_k) ||
        !rp_isfinite(feed->oxidizer_temperature_k) || feed->pressure_pa <= 0.0 ||
        feed->oxidizer_fuel_mass_ratio <= 0.0 || feed->fuel_temperature_k <= 0.0 ||
        feed->oxidizer_temperature_k <= 0.0) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid fixed-anchor feed or output.");
    }
    if (feed->phase != RP_FEED_LIQUID || strcmp(feed->fuel_anchor_id, fuel->id) != 0 ||
        strcmp(feed->oxidizer_anchor_id, oxidizer->id) != 0 ||
        feed->fuel_temperature_k != fuel->temperature_k ||
        feed->oxidizer_temperature_k != oxidizer->temperature_k) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Requires pinned CH4(L)111.643 K/O2(L)90.170 K liquid anchors; no interpolation or h override.");
    }
    if (feed->pressure_pa < 100.0 || feed->pressure_pa > 1e9 ||
        feed->oxidizer_fuel_mass_ratio < 0.1 || feed->oxidizer_fuel_mass_ratio > 20.0) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Fixed anchor products: p=100..1e9 Pa, O/F=0.1..20.");
    }
    fuel_fraction = 1.0 / (1.0 + feed->oxidizer_fuel_mass_ratio);
    result.fuel_h_j_per_kg = 1000.0 * fuel->enthalpy_j_per_mol / fuel->molar_mass_kg_per_kmol;
    result.oxidizer_h_j_per_kg = 1000.0 * oxidizer->enthalpy_j_per_mol / oxidizer->molar_mass_kg_per_kmol;
    result.mixture_h_j_per_kg = fuel_fraction * result.fuel_h_j_per_kg +
        (1.0 - fuel_fraction) * result.oxidizer_h_j_per_kg;
    for (unsigned int e = 0U; e < RP_CHO_ELEMENT_COUNT; ++e) {
        result.element_inventory_kmol_per_kg[e] =
            fuel_fraction * fuel->elements[e] / fuel->molar_mass_kg_per_kmol +
            (1.0 - fuel_fraction) * oxidizer->elements[e] / oxidizer->molar_mass_kg_per_kmol;
        if (!rp_isfinite(result.element_inventory_kmol_per_kg[e]) ||
            result.element_inventory_kmol_per_kg[e] <= 0.0) {
            return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite or empty anchor elemental inventory.");
        }
    }
    if (!rp_isfinite(result.mixture_h_j_per_kg)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite anchor enthalpy.");
    }
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}
