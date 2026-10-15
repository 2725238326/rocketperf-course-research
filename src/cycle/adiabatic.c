/* Adiabatic single-shaft GG/ORSC cycle (contract in engine_cycle.h).
 * Shaft: eta_shaft * W_turbine = W_pump_fuel + W_pump_ox + W_aux.
 * GG: turbine p_out is declared and the branch flow follows from the shaft
 * load. ORSC: the branch flow is fixed by the preburner O/F and p_out is
 * bisected between chamber p + return drop and preburner p.
 * finish_balance rejects mass > 1e-12, shaft > 2e-8 and exit element
 * > 1e-8 relative residuals; the energy bound scales with the HP tolerance.
 * Component HP states are checked against CEA in tests/test_cycle_reference.py. */

#include "rocketperf/engine_cycle.h"
#include "rocketperf/numeric.h"
#include "rocketperf/version.h"

#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

static double inventory_mass(const double *elements)
{
    const double oxygen = rp_thermo_find_species("O")->molar_mass_kg_per_kmol;
    const double carbon = rp_thermo_find_species("CO")->molar_mass_kg_per_kmol - oxygen;
    return elements[0] * carbon + elements[1] * rp_thermo_find_species("H")->molar_mass_kg_per_kmol + elements[2] * oxygen;
}

static int valid_propellant(const RpCyclePropellant *propellant)
{
    if (propellant->basis != RP_ENTHALPY_NASA9_CEA_V334 || propellant->pump.mass_flow_kg_per_s != 0.0) { return 0; }
    for (unsigned int e = 0U; e < RP_CHO_ELEMENT_COUNT; ++e) {
        if (!rp_isfinite(propellant->elements_kmol_per_kg[e]) || propellant->elements_kmol_per_kg[e] < 0.0) { return 0; }
    }
    return fabs(inventory_mass(propellant->elements_kmol_per_kg) - 1.0) <= 1e-10;
}

static RpStatus validate_input(const RpEngineCycleInput *input, RpError *error)
{
    if (!valid_propellant(&input->fuel) || !valid_propellant(&input->oxidizer) ||
        !rp_isfinite(input->total_mass_flow_kg_per_s) || input->total_mass_flow_kg_per_s <= 0.0 ||
        !rp_isfinite(input->overall_oxidizer_fuel_ratio) || input->overall_oxidizer_fuel_ratio <= 0.0 ||
        !rp_isfinite(input->preburner_oxidizer_fuel_ratio) || input->preburner_oxidizer_fuel_ratio <= 0.0 ||
        !rp_isfinite(input->chamber_pressure_pa) || input->chamber_pressure_pa < 100.0 || input->chamber_pressure_pa > 1e9 ||
        !rp_isfinite(input->preburner_pressure_pa) || input->preburner_pressure_pa < 100.0 || input->preburner_pressure_pa > 1e9 ||
        !rp_isfinite(input->turbine_outlet_pressure_pa) || input->turbine_outlet_pressure_pa < 0.0 ||
        !rp_isfinite(input->turbine_efficiency) || input->turbine_efficiency <= 0.0 || input->turbine_efficiency > 1.0 ||
        !rp_isfinite(input->shaft_efficiency) || input->shaft_efficiency <= 0.0 || input->shaft_efficiency > 1.0 ||
        !rp_isfinite(input->auxiliary_power_w) || input->auxiliary_power_w < 0.0 ||
        !rp_isfinite(input->maximum_branch_fraction) || input->maximum_branch_fraction <= 0.0 || input->maximum_branch_fraction >= 1.0 ||
        !rp_isfinite(input->pump_to_chamber_drop_pa) || input->pump_to_chamber_drop_pa < 0.0 ||
        !rp_isfinite(input->pump_to_preburner_drop_pa) || input->pump_to_preburner_drop_pa < 0.0 ||
        !rp_isfinite(input->return_pressure_drop_pa) || input->return_pressure_drop_pa < 0.0 ||
        !rp_isfinite(input->main_area_ratio) || input->main_area_ratio < 1.0 || input->main_area_ratio > 1e4 ||
        !rp_isfinite(input->branch_area_ratio) || input->branch_area_ratio < 1.0 || input->branch_area_ratio > 1e4 ||
        !rp_isfinite(input->branch_axial_projection) || input->branch_axial_projection < 0.0 || input->branch_axial_projection > 1.0 ||
        !rp_isfinite(input->ambient_pressure_pa) || input->ambient_pressure_pa < 0.0) {
        char message[192];
        (void)snprintf(message, sizeof(message),
            "Invalid cycle input: Pc=%.3e Pa (100 Pa-1 GPa), O/F=%.4g (>0), "
            "turbine efficiency=%.4g (0-1), preburner O/F=%.4g (>0); flows and areas finite.",
            input->chamber_pressure_pa, input->overall_oxidizer_fuel_ratio,
            input->turbine_efficiency, input->preburner_oxidizer_fuel_ratio);
        return rp_error_set(error, RP_INVALID_ARGUMENT, message);
    }
    if (input->fuel.elements_kmol_per_kg[0] <= 0.0 || input->fuel.elements_kmol_per_kg[1] <= 0.0 || input->fuel.elements_kmol_per_kg[2] != 0.0 ||
        input->oxidizer.elements_kmol_per_kg[0] != 0.0 || input->oxidizer.elements_kmol_per_kg[1] != 0.0) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Cycle feed requires a CH fuel and pure oxygen oxidizer on the pinned chemical mass basis.");
    }
    if (input->staged_combustion) {
        const double lower = input->chamber_pressure_pa + input->return_pressure_drop_pa;
        if (input->turbine_outlet_pressure_pa != 0.0 || input->branch_area_ratio != 1.0 || input->branch_axial_projection != 0.0) {
            return rp_error_set(error, RP_INVALID_ARGUMENT, "ORSC derives turbine outlet pressure and has no external exhaust nozzle.");
        }
        if (!rp_isfinite(lower) || lower >= input->preburner_pressure_pa ||
            input->preburner_oxidizer_fuel_ratio <= input->overall_oxidizer_fuel_ratio) {
            char message[192];
            (void)snprintf(message, sizeof(message),
                "ORSC needs preburner pressure %.3e Pa > chamber + return drop %.3e Pa "
                "and preburner O/F %.4g > overall O/F %.4g.",
                input->preburner_pressure_pa, lower,
                input->preburner_oxidizer_fuel_ratio, input->overall_oxidizer_fuel_ratio);
            return rp_error_set(error, RP_OUT_OF_DOMAIN, message);
        }
    } else if (input->return_pressure_drop_pa != 0.0 || input->turbine_outlet_pressure_pa <= 0.0 ||
               input->turbine_outlet_pressure_pa > input->preburner_pressure_pa) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "GG requires external turbine outlet pressure and zero return drop.");
    }
    return RP_OK;
}

static RpStatus pump_feeds(const RpEngineCycleInput *input, RpCycleResult *result, RpError *error)
{
    RpLiquidPumpInput fuel = input->fuel.pump;
    RpLiquidPumpInput oxidizer = input->oxidizer.pump;
    RpStatus status;
    result->fuel_mass_flow_kg_per_s = input->total_mass_flow_kg_per_s / (1.0 + input->overall_oxidizer_fuel_ratio);
    result->oxidizer_mass_flow_kg_per_s = input->total_mass_flow_kg_per_s - result->fuel_mass_flow_kg_per_s;
    if (result->fuel_mass_flow_kg_per_s <= 0.0 || result->oxidizer_mass_flow_kg_per_s <= 0.0) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Cycle feed split lost positive-flow precision.");
    }
    fuel.mass_flow_kg_per_s = result->fuel_mass_flow_kg_per_s;
    oxidizer.mass_flow_kg_per_s = result->oxidizer_mass_flow_kg_per_s;
    status = rp_liquid_pump_solve(&fuel, &result->fuel_pump, error);
    if (status != RP_OK) { return status; }
    status = rp_liquid_pump_solve(&oxidizer, &result->oxidizer_pump, error);
    if (status != RP_OK) { return status; }
    result->pump_power_w = result->fuel_pump.shaft_power_w + result->oxidizer_pump.shaft_power_w;
    result->turbine_power_w = (result->pump_power_w + input->auxiliary_power_w) / input->shaft_efficiency;
    if (!rp_isfinite(result->turbine_power_w)) { return rp_error_set(error, RP_NUMERIC_ERROR, "Cycle shaft demand overflow."); }
    /* Both streams reach the preburner; the fresh fuel also reaches the chamber.
     * The GG fresh oxidizer reaches the chamber separately. */
    if (fuel.outlet_pressure_pa - input->preburner_pressure_pa < input->pump_to_preburner_drop_pa ||
        oxidizer.outlet_pressure_pa - input->preburner_pressure_pa < input->pump_to_preburner_drop_pa ||
        fuel.outlet_pressure_pa - input->chamber_pressure_pa < input->pump_to_chamber_drop_pa ||
        (!input->staged_combustion && oxidizer.outlet_pressure_pa - input->chamber_pressure_pa < input->pump_to_chamber_drop_pa)) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Pump delivery cannot overcome declared chamber/preburner feed pressure drops.");
    }
    return RP_OK;
}

static RpChoMixedFeed fresh_feed(const RpEngineCycleInput *input, const RpCycleResult *result,
                                 double fuel_fraction, double pressure)
{
    RpChoMixedFeed feed = {0};
    feed.pressure_pa = pressure;
    feed.basis = RP_ENTHALPY_NASA9_CEA_V334;
    feed.h_j_per_kg = fuel_fraction * result->fuel_pump.outlet_h_j_per_kg +
        (1.0 - fuel_fraction) * result->oxidizer_pump.outlet_h_j_per_kg;
    for (unsigned int e = 0U; e < RP_CHO_ELEMENT_COUNT; ++e) {
        feed.elements_kmol_per_kg[e] = fuel_fraction * input->fuel.elements_kmol_per_kg[e] +
            (1.0 - fuel_fraction) * input->oxidizer.elements_kmol_per_kg[e];
    }
    return feed;
}

static RpStatus turbine_at_pressure(const RpEngineCycleInput *input, const RpGasMixture *gas,
                                     double pressure, const RpRootOptions *options,
                                     RpFrozenTurbineResult *output, RpError *error)
{
    RpFrozenTurbineInput turbine = {0};
    turbine.temperature_k = gas->temperature_k;
    turbine.inlet_pressure_pa = gas->pressure_pa;
    turbine.outlet_pressure_pa = pressure;
    turbine.efficiency = input->turbine_efficiency;
    memcpy(turbine.mole_fractions, gas->mole_fractions, sizeof(turbine.mole_fractions));
    return rp_frozen_turbine_solve(&turbine, options, output, error);
}

static RpStatus solve_return_turbine(const RpEngineCycleInput *input, const RpGasMixture *gas,
                                     double branch_flow, double power, const RpRootOptions *options,
                                     RpFrozenTurbineResult *output, unsigned int *iterations, RpError *error)
{
    double lower = input->chamber_pressure_pa + input->return_pressure_drop_pa;
    double upper = input->preburner_pressure_pa;
    const double demand = power / branch_flow;
    RpFrozenTurbineResult candidate;
    RpStatus status = turbine_at_pressure(input, gas, lower, options, &candidate, error);
    if (status != RP_OK) { return status; }
    if (!rp_isfinite(demand) || candidate.specific_work_j_per_kg < demand) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "ORSC shaft demand exceeds turbine work available above return pressure.");
    }
    if (power == 0.0) { return turbine_at_pressure(input, gas, upper, options, output, error); }
    for (unsigned int i = 0U; i < 80U; ++i) {
        const double residual = branch_flow * candidate.specific_work_j_per_kg - power;
        if (fabs(residual) <= 1e-8 * fmax(1.0, power)) { *output = candidate; *iterations = i; return RP_OK; }
        if (residual > 0.0) { lower = candidate.outlet.pressure_pa; }
        else { upper = candidate.outlet.pressure_pa; }
        const double middle = 0.5 * lower + 0.5 * upper;
        if (middle == lower || middle == upper) { break; }
        status = turbine_at_pressure(input, gas, middle, options, &candidate, error);
        if (status != RP_OK) { return status; }
    }
    return rp_error_set(error, RP_NO_CONVERGENCE, "ORSC turbine-pressure bracket did not close shaft power.");
}

static void gas_elements(const RpGasMixture *gas, double elements[RP_CHO_ELEMENT_COUNT])
{
    for (unsigned int e = 0U; e < RP_CHO_ELEMENT_COUNT; ++e) {
        elements[e] = 0.0;
        for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
            elements[e] += gas->mole_fractions[i] * (double)rp_cho_element_count(i, e) / gas->molar_mass_kg_per_kmol;
        }
    }
}

static RpStatus nozzle(const RpGasMixture *gas, double area_ratio, double ambient,
                        const RpRootOptions *options, RpFrozenNozzleResult *output, RpError *error)
{
    RpFrozenNozzleInput input = {0};
    input.chamber_temperature_k = gas->temperature_k;
    input.chamber_pressure_pa = gas->pressure_pa;
    input.area_ratio = area_ratio;
    input.ambient_pressure_pa = ambient;
    memcpy(input.mole_fractions, gas->mole_fractions, sizeof(input.mole_fractions));
    return rp_nozzle_solve_frozen(&input, options, output, error);
}

static RpStatus finish_balance(const RpEngineCycleInput *input, RpEngineCycleResult *result,
                                double hp_tolerance, const RpRootOptions *options, RpError *error)
{
    RpCycleResult *balance = &result->balance;
    double main_elements[RP_CHO_ELEMENT_COUNT], branch_elements[RP_CHO_ELEMENT_COUNT];
    RpStatus status = nozzle(&result->chamber.gas, input->main_area_ratio, input->ambient_pressure_pa,
                            options, &balance->main_nozzle, error);
    if (status != RP_OK) { return status; }
    balance->main_throat_area_m2 = balance->main_mass_flow_kg_per_s / balance->main_nozzle.throat.mass_flux_kg_per_m2_s;
    balance->main_thrust_n = balance->main_mass_flow_kg_per_s * balance->main_nozzle.effective_velocity_m_per_s;
    if (balance->external_mass_flow_kg_per_s > 0.0) {
        status = nozzle(&balance->turbine.outlet, input->branch_area_ratio, input->ambient_pressure_pa,
                        options, &balance->branch_nozzle, error);
        if (status != RP_OK) { return status; }
        balance->branch_nozzle_active = 1;
        balance->branch_throat_area_m2 = balance->external_mass_flow_kg_per_s / balance->branch_nozzle.throat.mass_flux_kg_per_m2_s;
        balance->branch_thrust_n = balance->external_mass_flow_kg_per_s * balance->branch_nozzle.effective_velocity_m_per_s * input->branch_axial_projection;
    }
    balance->total_thrust_n = balance->main_thrust_n + balance->branch_thrust_n;
    balance->main_effective_velocity_m_per_s = balance->main_thrust_n / balance->main_mass_flow_kg_per_s;
    balance->engine_effective_velocity_m_per_s = balance->total_thrust_n / input->total_mass_flow_kg_per_s;
    balance->engine_specific_impulse_s = balance->engine_effective_velocity_m_per_s / RP_STANDARD_GRAVITY_M_S2;
    balance->mechanical_loss_w = (1.0 - input->shaft_efficiency) * balance->branch_mass_flow_kg_per_s * balance->turbine.specific_work_j_per_kg;
    balance->inlet_enthalpy_rate_w = balance->fuel_mass_flow_kg_per_s * input->fuel.pump.inlet_h_j_per_kg +
        balance->oxidizer_mass_flow_kg_per_s * input->oxidizer.pump.inlet_h_j_per_kg;
    balance->exit_total_enthalpy_rate_w = balance->main_mass_flow_kg_per_s *
        (balance->main_nozzle.exit.gas.h_j_per_kg + 0.5 * pow(balance->main_nozzle.exit.velocity_m_per_s, 2.0));
    if (balance->branch_nozzle_active) {
        balance->exit_total_enthalpy_rate_w += balance->external_mass_flow_kg_per_s *
            (balance->branch_nozzle.exit.gas.h_j_per_kg + 0.5 * pow(balance->branch_nozzle.exit.velocity_m_per_s, 2.0));
    }
    balance->mass_residual_kg_per_s = input->total_mass_flow_kg_per_s - balance->main_mass_flow_kg_per_s - balance->external_mass_flow_kg_per_s;
    balance->shaft_residual_w = input->shaft_efficiency * balance->branch_mass_flow_kg_per_s * balance->turbine.specific_work_j_per_kg -
        balance->pump_power_w - input->auxiliary_power_w;
    balance->energy_residual_w = balance->inlet_enthalpy_rate_w - balance->exit_total_enthalpy_rate_w -
        input->auxiliary_power_w - balance->mechanical_loss_w;
    balance->mass_relative_residual = balance->mass_residual_kg_per_s / input->total_mass_flow_kg_per_s;
    balance->shaft_relative_residual = balance->shaft_residual_w / fmax(1.0, balance->pump_power_w + input->auxiliary_power_w);
    const double energy_scale = fmax(1.0, fabs(balance->inlet_enthalpy_rate_w) + fabs(balance->exit_total_enthalpy_rate_w) +
        input->auxiliary_power_w + balance->mechanical_loss_w);
    balance->energy_relative_residual = balance->energy_residual_w / energy_scale;
    gas_elements(&balance->main_nozzle.exit.gas, main_elements);
    gas_elements(&balance->turbine.outlet, branch_elements);
    for (unsigned int e = 0U; e < RP_CHO_ELEMENT_COUNT; ++e) {
        const double incoming = balance->fuel_mass_flow_kg_per_s * input->fuel.elements_kmol_per_kg[e] +
            balance->oxidizer_mass_flow_kg_per_s * input->oxidizer.elements_kmol_per_kg[e];
        const double outgoing = balance->main_mass_flow_kg_per_s * main_elements[e] + balance->external_mass_flow_kg_per_s * branch_elements[e];
        result->exit_element_relative_residual[e] = (outgoing - incoming) / incoming;
        if (!rp_isfinite(result->exit_element_relative_residual[e]) || fabs(result->exit_element_relative_residual[e]) > 1e-8) {
            return rp_error_set(error, RP_NO_CONVERGENCE, "Cycle exit elemental balance did not close.");
        }
    }
    if (!rp_isfinite(balance->total_thrust_n) || balance->total_thrust_n <= 0.0 ||
        !rp_isfinite(balance->engine_specific_impulse_s) || !rp_isfinite(balance->main_throat_area_m2) || balance->main_throat_area_m2 <= 0.0 ||
        !rp_isfinite(balance->branch_throat_area_m2) || !rp_isfinite(energy_scale) ||
        !rp_isfinite(balance->mass_relative_residual) || !rp_isfinite(balance->shaft_relative_residual) || !rp_isfinite(balance->energy_relative_residual) ||
        !rp_isfinite(result->preburner_enthalpy_residual_w) || !rp_isfinite(result->chamber_enthalpy_residual_w)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite cycle geometry, thrust or conservation residual.");
    }
    if (fabs(balance->mass_relative_residual) > 1e-12 || fabs(balance->shaft_relative_residual) > 2e-8 ||
        fabs(balance->energy_residual_w) > 0.1 + 2.5 * hp_tolerance * input->total_mass_flow_kg_per_s + 2e-8 * (balance->pump_power_w + input->auxiliary_power_w)) {
        return rp_error_set(error, RP_NO_CONVERGENCE, "Adiabatic cycle mass, shaft or energy balance did not close.");
    }
    return RP_OK;
}

RpStatus rp_engine_cycle_solve(const RpEngineCycleInput *input,
                                const RpCombustionOptions *combustion_options,
                                const RpRootOptions *root_options,
                                RpEngineCycleResult *output, RpError *error)
{
    RpEngineCycleResult result = {0};
    RpCycleResult *balance = &result.balance;
    RpChoMixedFeed preburner_feed, main_feed;
    RpStatus status;
    if (input == NULL || output == NULL) { return rp_error_set(error, RP_INVALID_ARGUMENT, "Cycle input and output are required."); }
    status = validate_input(input, error);
    if (status != RP_OK) { return status; }
    status = pump_feeds(input, balance, error);
    if (status != RP_OK) { return status; }
    preburner_feed = fresh_feed(input, balance, 1.0 / (1.0 + input->preburner_oxidizer_fuel_ratio), input->preburner_pressure_pa);
    if (input->staged_combustion && preburner_feed.elements_kmol_per_kg[2] <=
        2.0 * preburner_feed.elements_kmol_per_kg[0] + 0.5 * preburner_feed.elements_kmol_per_kg[1]) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "The all-oxidizer staged topology requires an oxygen-rich preburner inventory.");
    }
    status = rp_cho_equilibrium_hp_mixed(&preburner_feed, combustion_options, &result.preburner, error);
    if (status != RP_OK) { return status; }
    if (input->staged_combustion) {
        balance->branch_oxidizer_mass_flow_kg_per_s = balance->oxidizer_mass_flow_kg_per_s;
        balance->branch_fuel_mass_flow_kg_per_s = balance->oxidizer_mass_flow_kg_per_s / input->preburner_oxidizer_fuel_ratio;
        balance->branch_mass_flow_kg_per_s = balance->branch_fuel_mass_flow_kg_per_s + balance->branch_oxidizer_mass_flow_kg_per_s;
        status = solve_return_turbine(input, &result.preburner.gas, balance->branch_mass_flow_kg_per_s, balance->turbine_power_w,
                                     root_options, &balance->turbine, &result.turbine_pressure_iterations, error);
    } else {
        status = turbine_at_pressure(input, &result.preburner.gas, input->turbine_outlet_pressure_pa, root_options, &balance->turbine, error);
        if (status == RP_OK && balance->turbine_power_w > 0.0) {
            if (balance->turbine.specific_work_j_per_kg <= 0.0) {
                return rp_error_set(error, RP_OUT_OF_DOMAIN, "Positive GG shaft load requires positive turbine work.");
            }
            balance->branch_mass_flow_kg_per_s = balance->turbine_power_w / balance->turbine.specific_work_j_per_kg;
        }
        balance->branch_fuel_mass_flow_kg_per_s = balance->branch_mass_flow_kg_per_s / (1.0 + input->preburner_oxidizer_fuel_ratio);
        balance->branch_oxidizer_mass_flow_kg_per_s = balance->branch_mass_flow_kg_per_s - balance->branch_fuel_mass_flow_kg_per_s;
    }
    if (status != RP_OK) { return status; }
    if (!rp_isfinite(balance->branch_mass_flow_kg_per_s) || balance->branch_mass_flow_kg_per_s > input->maximum_branch_fraction * input->total_mass_flow_kg_per_s ||
        balance->branch_fuel_mass_flow_kg_per_s >= balance->fuel_mass_flow_kg_per_s ||
        (!input->staged_combustion && balance->branch_oxidizer_mass_flow_kg_per_s >= balance->oxidizer_mass_flow_kg_per_s)) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Preburner flow exceeds declared envelope or starves fresh chamber feed.");
    }
    balance->returned_mass_flow_kg_per_s = input->staged_combustion ? balance->branch_mass_flow_kg_per_s : 0.0;
    balance->external_mass_flow_kg_per_s = input->staged_combustion ? 0.0 : balance->branch_mass_flow_kg_per_s;
    balance->main_mass_flow_kg_per_s = input->total_mass_flow_kg_per_s - balance->external_mass_flow_kg_per_s;
    balance->main_fuel_mass_flow_kg_per_s = balance->fuel_mass_flow_kg_per_s - balance->branch_fuel_mass_flow_kg_per_s;
    balance->main_oxidizer_mass_flow_kg_per_s = input->staged_combustion ? 0.0 : balance->oxidizer_mass_flow_kg_per_s - balance->branch_oxidizer_mass_flow_kg_per_s;
    /* Main OF is the effective fuel/oxidizer inventory including return, not
     * fresh oxidizer/fresh fuel (zero for the all-O return topology). */
    balance->main_oxidizer_fuel_ratio = input->staged_combustion ? input->overall_oxidizer_fuel_ratio :
        balance->main_oxidizer_mass_flow_kg_per_s / balance->main_fuel_mass_flow_kg_per_s;
    main_feed = fresh_feed(input, balance, balance->main_fuel_mass_flow_kg_per_s / balance->main_mass_flow_kg_per_s, input->chamber_pressure_pa);
    if (input->staged_combustion) {
        double returned_elements[RP_CHO_ELEMENT_COUNT];
        const double fresh_fraction = balance->main_fuel_mass_flow_kg_per_s / balance->main_mass_flow_kg_per_s;
        const double returned_fraction = balance->returned_mass_flow_kg_per_s / balance->main_mass_flow_kg_per_s;
        gas_elements(&balance->turbine.outlet, returned_elements);
        main_feed.h_j_per_kg = fresh_fraction * balance->fuel_pump.outlet_h_j_per_kg + returned_fraction * balance->turbine.outlet.h_j_per_kg;
        for (unsigned int e = 0U; e < RP_CHO_ELEMENT_COUNT; ++e) {
            main_feed.elements_kmol_per_kg[e] = fresh_fraction * input->fuel.elements_kmol_per_kg[e] + returned_fraction * returned_elements[e];
        }
    }
    result.main_inlet_h_j_per_kg = main_feed.h_j_per_kg;
    memcpy(result.main_elements_kmol_per_kg, main_feed.elements_kmol_per_kg, sizeof(result.main_elements_kmol_per_kg));
    status = rp_cho_equilibrium_hp_mixed(&main_feed, combustion_options, &result.chamber, error);
    if (status != RP_OK) { return status; }
    result.preburner_enthalpy_residual_w = balance->branch_mass_flow_kg_per_s * result.preburner.enthalpy_residual_j_per_kg;
    result.chamber_enthalpy_residual_w = balance->main_mass_flow_kg_per_s * result.chamber.enthalpy_residual_j_per_kg;
    const double hp_tolerance = combustion_options != NULL ? combustion_options->enthalpy_tolerance_j_per_kg :
        rp_combustion_default_options().enthalpy_tolerance_j_per_kg;
    status = finish_balance(input, &result, hp_tolerance, root_options, error);
    if (status != RP_OK) { return status; }
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}
