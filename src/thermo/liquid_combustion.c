#include "rocketperf/liquid_combustion.h"
#include "rocketperf/numeric.h"
#include "equilibrium_internal.h"

#include <stddef.h>
#include <string.h>

static RpStatus validate_feed(const RpContinuousLiquidFeed *feed, RpError *error)
{
    if (feed == NULL || feed->dataset_id == NULL || feed->enthalpy_basis_id == NULL ||
        !rp_isfinite(feed->fuel_temperature_k) ||
        !rp_isfinite(feed->fuel_pressure_pa) ||
        !rp_isfinite(feed->oxidizer_temperature_k) ||
        !rp_isfinite(feed->oxidizer_pressure_pa) ||
        !rp_isfinite(feed->product_pressure_pa) ||
        !rp_isfinite(feed->oxidizer_fuel_mass_ratio) ||
        feed->fuel_temperature_k <= 0.0 || feed->fuel_pressure_pa <= 0.0 ||
        feed->oxidizer_temperature_k <= 0.0 || feed->oxidizer_pressure_pa <= 0.0 ||
        feed->product_pressure_pa <= 0.0 ||
        feed->oxidizer_fuel_mass_ratio <= 0.0) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid continuous liquid feed.");
    }
    if (strcmp(feed->enthalpy_basis_id, rp_liquid_feed_enthalpy_basis_id()) != 0) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Continuous liquid HP requires the pinned HEOS/CEA chemical enthalpy basis.");
    }
    if (feed->product_pressure_pa < 100.0 || feed->product_pressure_pa > 1e9 ||
        feed->oxidizer_fuel_mass_ratio < 0.1 ||
        feed->oxidizer_fuel_mass_ratio > 20.0) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Continuous liquid HP requires product p=100..1e9 Pa and O/F=0.1..20.");
    }
    return RP_OK;
}

RpStatus rp_ch4_o2_continuous_liquid_inlet(const RpContinuousLiquidFeed *feed,
                                           RpContinuousLiquidInlet *output,
                                           RpError *error)
{
    RpContinuousLiquidInlet result = {0};
    RpLiquidFeedQuery fuel_query = {0};
    RpLiquidFeedQuery oxidizer_query = {0};
    RpStatus status;
    double fuel_kmol_per_kg;
    double oxidizer_kmol_per_kg;
    if (output == NULL) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Continuous liquid inlet output is required.");
    }
    status = validate_feed(feed, error);
    if (status != RP_OK) { return status; }
    fuel_query.dataset_id = feed->dataset_id;
    fuel_query.fluid_id = "Methane";
    fuel_query.phase = feed->fuel_phase;
    fuel_query.temperature_k = feed->fuel_temperature_k;
    fuel_query.pressure_pa = feed->fuel_pressure_pa;
    oxidizer_query = fuel_query;
    oxidizer_query.fluid_id = "Oxygen";
    oxidizer_query.phase = feed->oxidizer_phase;
    oxidizer_query.temperature_k = feed->oxidizer_temperature_k;
    oxidizer_query.pressure_pa = feed->oxidizer_pressure_pa;
    status = rp_liquid_feed_evaluate(&fuel_query, &result.fuel, error);
    if (status != RP_OK) { return status; }
    status = rp_liquid_feed_evaluate(&oxidizer_query, &result.oxidizer, error);
    if (status != RP_OK) { return status; }
    result.fuel_mass_fraction = 1.0 / (1.0 + feed->oxidizer_fuel_mass_ratio);
    result.oxidizer_mass_fraction = 1.0 - result.fuel_mass_fraction;
    result.mixture_h_j_per_kg =
        result.fuel_mass_fraction * result.fuel.h_j_per_kg +
        result.oxidizer_mass_fraction * result.oxidizer.h_j_per_kg;
    fuel_kmol_per_kg = result.fuel_mass_fraction /
        (result.fuel.chemical_molar_mass_kg_per_mol * 1000.0);
    oxidizer_kmol_per_kg = result.oxidizer_mass_fraction /
        (result.oxidizer.chemical_molar_mass_kg_per_mol * 1000.0);
    result.element_inventory_kmol_per_kg[0] = fuel_kmol_per_kg;
    result.element_inventory_kmol_per_kg[1] = 4.0 * fuel_kmol_per_kg;
    result.element_inventory_kmol_per_kg[2] = 2.0 * oxidizer_kmol_per_kg;
    if (!rp_isfinite(result.mixture_h_j_per_kg) ||
        !rp_isfinite(result.element_inventory_kmol_per_kg[0]) ||
        !rp_isfinite(result.element_inventory_kmol_per_kg[1]) ||
        !rp_isfinite(result.element_inventory_kmol_per_kg[2]) ||
        result.element_inventory_kmol_per_kg[0] <= 0.0 ||
        result.element_inventory_kmol_per_kg[1] <= 0.0 ||
        result.element_inventory_kmol_per_kg[2] <= 0.0) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite continuous liquid inlet conversion.");
    }
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}

RpStatus rp_ch4_o2_continuous_liquid_hp(const RpContinuousLiquidFeed *feed,
                                        const RpCombustionOptions *options,
                                        RpContinuousLiquidHpResult *output,
                                        RpError *error)
{
    RpContinuousLiquidHpResult result = {0};
    RpStatus status;
    if (output == NULL) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Continuous liquid HP output is required.");
    }
    status = rp_ch4_o2_continuous_liquid_inlet(feed, &result.inlet, error);
    if (status != RP_OK) { return status; }
    status = rp_cho_equilibrium_hp_inventory(
        feed->product_pressure_pa, result.inlet.element_inventory_kmol_per_kg,
        result.inlet.mixture_h_j_per_kg, options, &result.chamber, error);
    if (status != RP_OK) { return status; }
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}
