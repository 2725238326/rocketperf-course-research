#include "rocketperf/combustion.h"
#include "rocketperf/numeric.h"

#include <math.h>
#include <stddef.h>

static const char *const species_ids[RP_CHO_SPECIES_COUNT] = {
    "H2", "O2", "H2O", "CO", "CO2", "CH4", "H", "O", "OH"
};
static const unsigned int atoms[RP_CHO_SPECIES_COUNT][RP_CHO_ELEMENT_COUNT] = {
    {0U, 2U, 0U}, {0U, 0U, 2U}, {0U, 2U, 1U},
    {1U, 0U, 1U}, {1U, 0U, 2U}, {1U, 4U, 0U},
    {0U, 1U, 0U}, {0U, 0U, 1U}, {0U, 1U, 1U}
};

const char *rp_cho_species_id(unsigned int index)
{
    return index < RP_CHO_SPECIES_COUNT ? species_ids[index] : NULL;
}

unsigned int rp_cho_element_count(unsigned int species, unsigned int element)
{
    return species < RP_CHO_SPECIES_COUNT && element < RP_CHO_ELEMENT_COUNT ? atoms[species][element] : 0U;
}

RpStatus rp_cho_mixture_evaluate(const double mole_fractions[RP_CHO_SPECIES_COUNT],
                                 double temperature_k, double pressure_pa,
                                 RpGasMixture *output, RpError *error)
{
    RpGasMixture result = {0};
    double sum = 0.0;
    double cp_molar = 0.0;
    double h_molar = 0.0;
    double s_molar = 0.0;
    if (mole_fractions == NULL || output == NULL || !rp_isfinite(temperature_k) ||
        temperature_k <= 0.0 || !rp_isfinite(pressure_pa) || pressure_pa <= 0.0) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid gas composition, temperature or pressure.");
    }
    for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
        const double fraction = mole_fractions[i];
        const RpNasa9Species *species;
        RpThermoState state;
        RpStatus status;
        if (!rp_isfinite(fraction) || fraction < 0.0 || fraction > 1.0) {
            return rp_error_set(error, RP_INVALID_ARGUMENT, "Mole fractions must be finite and non-negative.");
        }
        result.mole_fractions[i] = fraction;
        sum += fraction;
        if (fraction == 0.0) { continue; }
        species = rp_thermo_find_species(species_ids[i]);
        status = rp_nasa9_evaluate(species, temperature_k, &state, error);
        if (status != RP_OK) { return status; }
        result.molar_mass_kg_per_kmol += fraction * species->molar_mass_kg_per_kmol;
        cp_molar += fraction * species->molar_mass_kg_per_kmol * state.cp_j_per_kg_k;
        h_molar += fraction * species->molar_mass_kg_per_kmol * state.h_j_per_kg;
        s_molar += fraction * (species->molar_mass_kg_per_kmol * state.s_j_per_kg_k -
                   RP_UNIVERSAL_GAS_CONSTANT_J_KMOL_K * log(fraction));
    }
    if (fabs(sum - 1.0) > 1e-12) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Mole fractions must sum to one; no silent normalization.");
    }
    result.temperature_k = temperature_k;
    result.pressure_pa = pressure_pa;
    result.gas_constant_j_per_kg_k = RP_UNIVERSAL_GAS_CONSTANT_J_KMOL_K / result.molar_mass_kg_per_kmol;
    result.cp_frozen_j_per_kg_k = cp_molar / result.molar_mass_kg_per_kmol;
    result.h_j_per_kg = h_molar / result.molar_mass_kg_per_kmol;
    result.s_j_per_kg_k = s_molar / result.molar_mass_kg_per_kmol -
        result.gas_constant_j_per_kg_k * (log(pressure_pa) - log(rp_thermo_reference_pressure_pa()));
    if (!rp_isfinite(result.gas_constant_j_per_kg_k) || !rp_isfinite(result.cp_frozen_j_per_kg_k) ||
        !rp_isfinite(result.h_j_per_kg) || !rp_isfinite(result.s_j_per_kg_k) ||
        result.cp_frozen_j_per_kg_k <= result.gas_constant_j_per_kg_k) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite mixture state or non-positive frozen cv.");
    }
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}

RpStatus rp_ch4_o2_feed_enthalpy(const RpCh4O2Feed *feed, double *output, RpError *error)
{
    RpThermoState fuel;
    RpThermoState oxidizer;
    RpStatus status;
    double result;
    double fuel_fraction;
    if (feed == NULL || output == NULL || !rp_isfinite(feed->pressure_pa) || feed->pressure_pa <= 0.0 ||
        !rp_isfinite(feed->oxidizer_fuel_mass_ratio) || feed->oxidizer_fuel_mass_ratio <= 0.0) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid CH4/O2 feed pressure or mass ratio.");
    }
    if (feed->phase != RP_FEED_GAS) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Only gas-feed CH4/O2 is supported; no liquid enthalpy substitution.");
    }
    status = rp_nasa9_evaluate(rp_thermo_find_species("CH4"), feed->fuel_temperature_k, &fuel, error);
    if (status != RP_OK) { return status; }
    status = rp_nasa9_evaluate(rp_thermo_find_species("O2"), feed->oxidizer_temperature_k, &oxidizer, error);
    if (status != RP_OK) { return status; }
    fuel_fraction = 1.0 / (1.0 + feed->oxidizer_fuel_mass_ratio);
    result = fuel_fraction * fuel.h_j_per_kg + (1.0 - fuel_fraction) * oxidizer.h_j_per_kg;
    if (!rp_isfinite(result)) { return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite feed enthalpy."); }
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}

static RpStatus gas_enthalpy_bounds(const char *id, double enthalpy, RpError *error)
{
    const RpNasa9Species *species = rp_thermo_find_species(id);
    RpThermoState lower, upper;
    RpStatus status = rp_nasa9_evaluate(species, 200.0, &lower, error);
    if (status != RP_OK) { return status; }
    status = rp_nasa9_evaluate(species, 6000.0, &upper, error);
    if (status != RP_OK) { return status; }
    if (enthalpy < lower.h_j_per_kg || enthalpy > upper.h_j_per_kg) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Inlet species enthalpy outside pinned gas fit's 200..6000 K interval.");
    }
    return RP_OK;
}

RpStatus rp_ch4_o2_inlet_enthalpy(const RpCh4O2EnthalpyFeed *feed,
                                  double *output, RpError *error)
{
    double fuel_fraction, result;
    RpStatus status;
    if (feed == NULL || output == NULL || !rp_isfinite(feed->pressure_pa) || feed->pressure_pa <= 0.0 ||
        !rp_isfinite(feed->oxidizer_fuel_mass_ratio) || feed->oxidizer_fuel_mass_ratio <= 0.0 ||
        !rp_isfinite(feed->fuel_h_j_per_kg) || !rp_isfinite(feed->oxidizer_h_j_per_kg)) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid explicit-enthalpy CH4/O2 feed.");
    }
    if (feed->phase != RP_FEED_GAS || feed->basis != RP_ENTHALPY_NASA9_CEA_V334) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Explicit inlet requires gas phase and pinned NASA9 CEA v3.3.4 formation-enthalpy basis.");
    }
    if (feed->pressure_pa < 100.0 || feed->pressure_pa > 1e9 ||
        feed->oxidizer_fuel_mass_ratio < 0.1 || feed->oxidizer_fuel_mass_ratio > 20.0) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Explicit inlet: p=100..1e9 Pa, O/F=0.1..20.");
    }
    status = gas_enthalpy_bounds("CH4", feed->fuel_h_j_per_kg, error);
    if (status != RP_OK) { return status; }
    status = gas_enthalpy_bounds("O2", feed->oxidizer_h_j_per_kg, error);
    if (status != RP_OK) { return status; }
    fuel_fraction = 1.0 / (1.0 + feed->oxidizer_fuel_mass_ratio);
    result = fuel_fraction * feed->fuel_h_j_per_kg + (1.0 - fuel_fraction) * feed->oxidizer_h_j_per_kg;
    if (!rp_isfinite(result)) { return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite explicit inlet enthalpy."); }
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}
