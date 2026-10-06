#include "rocketperf/propellant_study.h"
#include "rocketperf/numeric.h"

#include <stddef.h>
#include <string.h>

RpStatus rp_propellant_compare_fixed(const RpPropellantComparisonInput *input,
                                     const RpCombustionOptions *combustion_options,
                                     const RpRootOptions *nozzle_options,
                                     RpPropellantComparisonResult *output, RpError *error)
{
    RpPropellantComparisonResult result = {0};
    RpFrozenNozzleInput nozzle = {0};
    RpStatus status;
    if (input == NULL || output == NULL ||
        !rp_isfinite(input->methane.product_pressure_pa) ||
        !rp_isfinite(input->kerosene.reactants.pressure_pa) ||
        input->methane.product_pressure_pa != input->kerosene.reactants.pressure_pa ||
        !rp_isfinite(input->area_ratio) || input->area_ratio < 1.0 || input->area_ratio > 1e4 ||
        !rp_isfinite(input->ambient_pressure_pa) || input->ambient_pressure_pa < 0.0 ||
        !rp_isfinite(input->throat_area_m2) || input->throat_area_m2 <= 0.0) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Propellant comparison requires the same product pressure and valid common geometry/back pressure.");
    }
    status = rp_kerosene_anchor_inlet(&input->kerosene, &result.kerosene.inlet, error);
    if (status != RP_OK) { return status; }
    status = rp_ch4_o2_continuous_liquid_hp_fixed_area(&input->methane,
        input->area_ratio, input->ambient_pressure_pa, input->throat_area_m2,
        combustion_options, nozzle_options, &result.methane, error);
    if (status != RP_OK) { return status; }
    status = rp_kerosene_equilibrium_hp_anchor(&input->kerosene,
        combustion_options, &result.kerosene.chamber, error);
    if (status != RP_OK) { return status; }
    nozzle.chamber_temperature_k = result.kerosene.chamber.gas.temperature_k;
    nozzle.chamber_pressure_pa = result.kerosene.chamber.gas.pressure_pa;
    memcpy(nozzle.mole_fractions, result.kerosene.chamber.gas.mole_fractions,
           sizeof(nozzle.mole_fractions));
    nozzle.area_ratio = input->area_ratio;
    nozzle.ambient_pressure_pa = input->ambient_pressure_pa;
    status = rp_nozzle_solve_frozen_fixed_area(&nozzle, input->throat_area_m2,
        nozzle_options, &result.kerosene.nozzle, error);
    if (status != RP_OK) { return status; }
    result.methane_minus_kerosene_thrust_n = result.methane.nozzle.thrust_n - result.kerosene.nozzle.thrust_n;
    result.methane_minus_kerosene_isp_s = result.methane.nozzle.specific_impulse_s - result.kerosene.nozzle.specific_impulse_s;
    result.methane_minus_kerosene_mass_flow_kg_per_s = result.methane.nozzle.mass_flow_kg_per_s - result.kerosene.nozzle.mass_flow_kg_per_s;
    result.methane_minus_kerosene_cstar_m_per_s = result.methane.nozzle.nozzle.cstar_m_per_s - result.kerosene.nozzle.nozzle.cstar_m_per_s;
    if (!rp_isfinite(result.methane_minus_kerosene_thrust_n) ||
        !rp_isfinite(result.methane_minus_kerosene_isp_s) ||
        !rp_isfinite(result.methane_minus_kerosene_mass_flow_kg_per_s) ||
        !rp_isfinite(result.methane_minus_kerosene_cstar_m_per_s)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Propellant comparison difference overflow.");
    }
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}
