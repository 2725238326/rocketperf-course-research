#include "combustion_report.h"

static int write_quoted(FILE *stream, const char *value)
{
    if (fputc('"', stream) == EOF) { return 0; }
    for (const char *p = value; *p != '\0'; ++p) {
        if ((*p == '"' || *p == '\\') && fputc('\\', stream) == EOF) { return 0; }
        if (fputc((unsigned char)*p, stream) == EOF) { return 0; }
    }
    return fputc('"', stream) != EOF;
}

int rp_report_write_mixture(FILE *stream, const RpGasMixture *gas)
{
    if (fprintf(stream, "{\"temperature_k\":%.17g,\"pressure_pa\":%.17g,\"molar_mass_kg_per_kmol\":%.17g,"
               "\"gas_constant_j_per_kg_k\":%.17g,\"cp_frozen_j_per_kg_k\":%.17g,"
               "\"h_j_per_kg\":%.17g,\"s_j_per_kg_k\":%.17g,\"mole_fractions\":{",
               gas->temperature_k, gas->pressure_pa, gas->molar_mass_kg_per_kmol,
               gas->gas_constant_j_per_kg_k, gas->cp_frozen_j_per_kg_k,
               gas->h_j_per_kg, gas->s_j_per_kg_k) < 0) { return 0; }
    for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
        if (fprintf(stream, "%s\"%s\":%.17g", i == 0U ? "" : ",", rp_cho_species_id(i), gas->mole_fractions[i]) < 0) { return 0; }
    }
    return fputs("}}", stream) >= 0;
}

int rp_report_write_station(FILE *stream, const RpFrozenFlowStation *station)
{
    return fputs("{\"gas\":", stream) >= 0 && rp_report_write_mixture(stream, &station->gas) &&
        fprintf(stream, ",\"velocity_m_per_s\":%.17g,\"mach\":%.17g,\"mass_flux_kg_per_m2_s\":%.17g,"
               "\"energy_residual_j_per_kg\":%.17g,\"entropy_residual_j_per_kg_k\":%.17g}",
               station->velocity_m_per_s, station->mach, station->mass_flux_kg_per_m2_s,
               station->energy_residual_j_per_kg, station->entropy_residual_j_per_kg_k) >= 0;
}

int rp_report_write_diagnostics(FILE *stream, const RpCombustionResult *result)
{
    return fprintf(stream, ",\"diagnostics\":{\"element_relative_residual\":[%.17g,%.17g,%.17g],\"equilibrium_residual\":%.17g,"
                  "\"enthalpy_residual_j_per_kg\":%.17g,\"equilibrium_iterations\":%u,\"hp_iterations\":%u}",
                  result->element_relative_residual[0], result->element_relative_residual[1],
                  result->element_relative_residual[2], result->equilibrium_residual,
                  result->enthalpy_residual_j_per_kg, result->equilibrium_iterations,
                  result->hp_iterations) >= 0;
}

int rp_report_write_frozen_report(FILE *stream, const RpFrozenNozzleResult *nozzle)
{
    return fputs(",\"nozzle\":{\"freeze_location\":\"chamber\",\"throat\":", stream) >= 0 &&
        rp_report_write_station(stream, &nozzle->throat) && fputs(",\"exit\":", stream) >= 0 &&
        rp_report_write_station(stream, &nozzle->exit) &&
        fprintf(stream, ",\"cstar_m_per_s\":%.17g,\"vacuum_effective_velocity_m_per_s\":%.17g,"
               "\"effective_velocity_m_per_s\":%.17g,\"thrust_coefficient\":%.17g,"
               "\"continuity_relative_residual\":%.17g,\"sonic_relative_residual\":%.17g}",
               nozzle->cstar_m_per_s, nozzle->vacuum_effective_velocity_m_per_s,
               nozzle->effective_velocity_m_per_s, nozzle->thrust_coefficient,
               nozzle->continuity_relative_residual, nozzle->sonic_relative_residual) >= 0;
}

int rp_report_write_fixed_geometry(FILE *stream, const RpFrozenNozzleFixedResult *geometry)
{
    return fprintf(stream, ",\"geometry\":{\"throat_area_m2\":%.17g,\"exit_area_m2\":%.17g,"
                  "\"mass_flow_kg_per_s\":%.17g,\"thrust_n\":%.17g,\"specific_impulse_s\":%.17g}",
                  geometry->throat_area_m2, geometry->exit_area_m2, geometry->mass_flow_kg_per_s,
                  geometry->thrust_n, geometry->specific_impulse_s) >= 0;
}

int rp_report_write_liquid_state(FILE *stream, const RpLiquidFeedState *state)
{
    return fprintf(stream, "{\"density_kg_per_m3\":%.17g,\"h_j_per_mol\":%.17g,\"h_j_per_kg\":%.17g,"
                  "\"eos_molar_mass_kg_per_mol\":%.17g,\"chemical_molar_mass_kg_per_mol\":%.17g}",
                  state->density_kg_per_m3, state->h_j_per_mol, state->h_j_per_kg,
                  state->eos_molar_mass_kg_per_mol, state->chemical_molar_mass_kg_per_mol) >= 0;
}

int rp_report_write_propellant(FILE *stream, const RpPropellantComparisonInput *input,
                               const RpPropellantComparisonResult *result, const RpPropellantCase *study)
{
    if (fputs("{\"schema_version\":1,\"study\":\"propellant_fixed_geometry_v1\",", stream) < 0) { return 0; }
    if (study != NULL) {
        if (fputs("\"case\":{\"id\":", stream) < 0 || !write_quoted(stream, study->id) ||
            fputs(",\"source_ref\":", stream) < 0 || !write_quoted(stream, study->source_ref) ||
            fputs("},", stream) < 0) { return 0; }
    }
    return fprintf(stream,
        "\"inputs\":{\"pressure_pa\":%.17g,\"throat_area_m2\":%.17g,\"area_ratio\":%.17g,"
        "\"ambient_pressure_pa\":%.17g,\"methane_of\":%.17g,\"kerosene_of\":%.17g},"
        "\"inlets\":{\"methane\":{\"dataset\":\"%s\",\"basis\":\"%s\",\"fuel_temperature_k\":%.17g,"
        "\"oxidizer_temperature_k\":%.17g,\"fuel_pressure_pa\":%.17g,\"oxidizer_pressure_pa\":%.17g},"
        "\"kerosene\":{\"dataset\":\"%s\",\"fuel\":\"RP-1\",\"oxidizer\":\"O2(L)\","
        "\"fuel_temperature_k\":%.17g,\"oxidizer_temperature_k\":%.17g}},\"methane\":{\"chamber\":",
        input->methane.product_pressure_pa, input->throat_area_m2, input->area_ratio, input->ambient_pressure_pa,
        input->methane.oxidizer_fuel_mass_ratio, input->kerosene.reactants.oxidizer_fuel_mass_ratio, rp_liquid_feed_dataset_id(),
        rp_liquid_feed_enthalpy_basis_id(), input->methane.fuel_temperature_k, input->methane.oxidizer_temperature_k,
        input->methane.fuel_pressure_pa, input->methane.oxidizer_pressure_pa, rp_kerosene_dataset_id(),
        input->kerosene.reactants.fuel_temperature_k, input->kerosene.reactants.oxidizer_temperature_k) >= 0 &&
        rp_report_write_mixture(stream, &result->methane.hp.chamber.gas) && rp_report_write_diagnostics(stream, &result->methane.hp.chamber) &&
        fprintf(stream, ",\"inlet_mixture_h_j_per_kg\":%.17g", result->methane.hp.inlet.mixture_h_j_per_kg) >= 0 &&
        rp_report_write_frozen_report(stream, &result->methane.nozzle.nozzle) && rp_report_write_fixed_geometry(stream, &result->methane.nozzle) &&
        fputs("},\"kerosene\":{\"chamber\":", stream) >= 0 &&
        rp_report_write_mixture(stream, &result->kerosene.chamber.gas) && rp_report_write_diagnostics(stream, &result->kerosene.chamber) &&
        fprintf(stream, ",\"inlet_mixture_h_j_per_kg\":%.17g", result->kerosene.inlet.mixture_h_j_per_kg) >= 0 &&
        rp_report_write_frozen_report(stream, &result->kerosene.nozzle.nozzle) && rp_report_write_fixed_geometry(stream, &result->kerosene.nozzle) &&
        fprintf(stream, "},\"methane_minus_kerosene\":{\"thrust_n\":%.17g,\"isp_s\":%.17g,"
               "\"mass_flow_kg_per_s\":%.17g,\"cstar_m_per_s\":%.17g},"
               "\"limitations\":[\"Declared inlet states and O/F; not flight engine performance or optimum mixtures.\","
               "\"Nine neutral gas HP and chamber-frozen nozzle; no carbon, pump, cycle or hardware losses.\"]}\n",
               result->methane_minus_kerosene_thrust_n, result->methane_minus_kerosene_isp_s,
               result->methane_minus_kerosene_mass_flow_kg_per_s, result->methane_minus_kerosene_cstar_m_per_s) >= 0;
}
