#include "rocketperf/cycle.h"
#include "rocketperf/numeric.h"

#include <math.h>
#include <stddef.h>
#include <string.h>

/* Staged-combustion (topping) closure of the prescribed-state cycle.
 *
 * Difference from prescribed.c: the preburner gas is NOT exhausted overboard.
 * It expands through the turbine and is injected into the main chamber, so the
 * whole propellant flow leaves through the main nozzle and no branch nozzle
 * exists. The chamber state stays PRESCRIBED, so this remains energy
 * bookkeeping, not an adiabatic cycle closure.
 *
 * Input validation is deliberately mirrored from prescribed.c so each closure
 * reads on its own; the staged-only rules are the full turbine return and the
 * injection pressure requirement. */

static RpStatus staged_nozzle(const RpGasMixture *gas, double area, double ambient,
                              const RpRootOptions *options,
                              RpFrozenNozzleResult *output, RpError *error)
{
    RpFrozenNozzleInput input = {0};
    input.chamber_temperature_k = gas->temperature_k;
    input.chamber_pressure_pa = gas->pressure_pa;
    memcpy(input.mole_fractions, gas->mole_fractions, sizeof(input.mole_fractions));
    input.area_ratio = area; input.ambient_pressure_pa = ambient;
    return rp_nozzle_solve_frozen(&input, options, output, error);
}

RpStatus rp_cycle_solve_staged(const RpCycleInput *input,
                               const RpRootOptions *options,
                               RpCycleResult *output, RpError *error)
{
    RpCycleResult result = {0};
    RpLiquidPumpInput fuel;
    RpLiquidPumpInput oxidizer;
    RpCh4O2Feed preburner_feed;
    RpCh4O2Feed chamber_feed;
    RpCombustionResult preburner = {0};
    RpCombustionResult chamber = {0};
    RpFrozenTurbineInput turbine = {0};
    double pump_power;
    double branch_fuel;
    double branch_oxidizer;
    double injected_enthalpy_rate;
    double inlet_enthalpy_rate;
    double exit_enthalpy_rate;
    double scale;
    RpStatus status;
    if (input == NULL || output == NULL || !rp_isfinite(input->total_mass_flow_kg_per_s) || input->total_mass_flow_kg_per_s <= 0.0 ||
        !rp_isfinite(input->overall_oxidizer_fuel_ratio) || input->overall_oxidizer_fuel_ratio <= 0.0 ||
        !rp_isfinite(input->generator_oxidizer_fuel_ratio) || input->generator_oxidizer_fuel_ratio <= 0.0 ||
        !rp_isfinite(input->shaft_efficiency) || input->shaft_efficiency <= 0.0 || input->shaft_efficiency > 1.0 ||
        !rp_isfinite(input->auxiliary_power_w) || input->auxiliary_power_w < 0.0 ||
        !rp_isfinite(input->maximum_branch_fraction) || input->maximum_branch_fraction <= 0.0 || input->maximum_branch_fraction >= 1.0 ||
        !rp_isfinite(input->return_fraction) || input->return_fraction < 0.0 || input->return_fraction > 1.0 ||
        !rp_isfinite(input->return_pressure_drop_pa) || input->return_pressure_drop_pa < 0.0 ||
        !rp_isfinite(input->branch_axial_projection) || input->branch_axial_projection < 0.0 || input->branch_axial_projection > 1.0 ||
        !rp_isfinite(input->ambient_pressure_pa) || input->ambient_pressure_pa < 0.0 ||
        !rp_isfinite(input->main_area_ratio) || input->main_area_ratio < 1.0 || input->main_area_ratio > 1e4 ||
        !rp_isfinite(input->branch_area_ratio) || input->branch_area_ratio < 1.0 || input->branch_area_ratio > 1e4 ||
        input->fuel_pump.mass_flow_kg_per_s != 0.0 || input->oxidizer_pump.mass_flow_kg_per_s != 0.0) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid staged-cycle flow, efficiencies, routing or pump flow overrides.");
    }
    if (input->return_fraction != 1.0) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Staged combustion requires a full turbine return (return_fraction == 1).");
    }
    result.fuel_mass_flow_kg_per_s = input->total_mass_flow_kg_per_s / (1.0 + input->overall_oxidizer_fuel_ratio);
    result.oxidizer_mass_flow_kg_per_s = input->total_mass_flow_kg_per_s - result.fuel_mass_flow_kg_per_s;
    if (result.fuel_mass_flow_kg_per_s <= 0.0 || result.oxidizer_mass_flow_kg_per_s <= 0.0) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Feed split lost positive-flow precision.");
    }
    fuel = input->fuel_pump; oxidizer = input->oxidizer_pump;
    fuel.mass_flow_kg_per_s = result.fuel_mass_flow_kg_per_s;
    oxidizer.mass_flow_kg_per_s = result.oxidizer_mass_flow_kg_per_s;
    status = rp_liquid_pump_solve(&fuel, &result.fuel_pump, error);
    if (status != RP_OK) { return status; }
    status = rp_liquid_pump_solve(&oxidizer, &result.oxidizer_pump, error);
    if (status != RP_OK) { return status; }
    preburner_feed = (RpCh4O2Feed){input->turbine_inlet_pressure_pa, input->generator_oxidizer_fuel_ratio, 298.15, 298.15, RP_FEED_GAS};
    status = rp_ch4_o2_equilibrium_tp(&preburner_feed, input->generator_temperature_k, NULL, &preburner, error);
    if (status != RP_OK) { return status; }
    turbine.temperature_k = preburner.gas.temperature_k; turbine.inlet_pressure_pa = preburner.gas.pressure_pa;
    turbine.outlet_pressure_pa = input->turbine_outlet_pressure_pa; turbine.efficiency = input->turbine_efficiency;
    memcpy(turbine.mole_fractions, preburner.gas.mole_fractions, sizeof(turbine.mole_fractions));
    status = rp_frozen_turbine_solve(&turbine, options, &result.turbine, error);
    if (status != RP_OK) { return status; }
    pump_power = result.fuel_pump.shaft_power_w + result.oxidizer_pump.shaft_power_w;
    result.turbine_power_w = (pump_power + input->auxiliary_power_w) / input->shaft_efficiency;
    if (!rp_isfinite(result.turbine_power_w)) { return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite shaft demand."); }
    if (result.turbine_power_w > 0.0) {
        if (result.turbine.specific_work_j_per_kg <= 0.0) {
            return rp_error_set(error, RP_OUT_OF_DOMAIN, "Positive shaft load cannot be met by a zero-work turbine.");
        }
        result.branch_mass_flow_kg_per_s = result.turbine_power_w / result.turbine.specific_work_j_per_kg;
    }
    if (!rp_isfinite(result.branch_mass_flow_kg_per_s)) { return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite preburner flow."); }
    if (result.branch_mass_flow_kg_per_s > input->maximum_branch_fraction * input->total_mass_flow_kg_per_s) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Shaft demand exceeds the declared preburner-flow envelope.");
    }
    branch_fuel = result.branch_mass_flow_kg_per_s / (1.0 + input->generator_oxidizer_fuel_ratio);
    branch_oxidizer = result.branch_mass_flow_kg_per_s - branch_fuel;
    if (branch_fuel >= result.fuel_mass_flow_kg_per_s || branch_oxidizer >= result.oxidizer_mass_flow_kg_per_s) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Preburner diversion starves a pump-feed stream.");
    }
    if (fuel.outlet_pressure_pa < input->chamber_pressure_pa || oxidizer.outlet_pressure_pa < input->chamber_pressure_pa ||
        fuel.outlet_pressure_pa < input->turbine_inlet_pressure_pa || oxidizer.outlet_pressure_pa < input->turbine_inlet_pressure_pa) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Pump delivery pressure cannot reach a declared chamber/preburner state.");
    }
    if (input->turbine_outlet_pressure_pa < input->chamber_pressure_pa + input->return_pressure_drop_pa) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Turbine discharge pressure cannot inject into the chamber across the declared return drop.");
    }
    result.branch_fuel_mass_flow_kg_per_s = branch_fuel;
    result.branch_oxidizer_mass_flow_kg_per_s = branch_oxidizer;
    result.returned_mass_flow_kg_per_s = result.branch_mass_flow_kg_per_s;
    result.external_mass_flow_kg_per_s = 0.0;
    result.main_mass_flow_kg_per_s = input->total_mass_flow_kg_per_s;
    result.main_fuel_mass_flow_kg_per_s = result.fuel_mass_flow_kg_per_s;
    result.main_oxidizer_mass_flow_kg_per_s = result.oxidizer_mass_flow_kg_per_s;
    result.main_oxidizer_fuel_ratio = input->overall_oxidizer_fuel_ratio;
    chamber_feed = (RpCh4O2Feed){input->chamber_pressure_pa, result.main_oxidizer_fuel_ratio, 298.15, 298.15, RP_FEED_GAS};
    status = rp_ch4_o2_equilibrium_tp(&chamber_feed, input->chamber_temperature_k, NULL, &chamber, error);
    if (status != RP_OK) { return status; }
    status = staged_nozzle(&chamber.gas, input->main_area_ratio, input->ambient_pressure_pa, options,
                           &result.main_nozzle, error);
    if (status != RP_OK) { return status; }
    result.branch_nozzle_active = 0;
    result.branch_thrust_n = 0.0;
    result.branch_throat_area_m2 = 0.0;
    result.generator_heat_w = result.branch_mass_flow_kg_per_s * preburner.gas.h_j_per_kg -
        branch_fuel * result.fuel_pump.outlet_h_j_per_kg - branch_oxidizer * result.oxidizer_pump.outlet_h_j_per_kg;
    injected_enthalpy_rate = result.branch_mass_flow_kg_per_s * result.turbine.outlet.h_j_per_kg +
        (result.fuel_mass_flow_kg_per_s - branch_fuel) * result.fuel_pump.outlet_h_j_per_kg +
        (result.oxidizer_mass_flow_kg_per_s - branch_oxidizer) * result.oxidizer_pump.outlet_h_j_per_kg;
    result.chamber_heat_w = result.main_mass_flow_kg_per_s * chamber.gas.h_j_per_kg - injected_enthalpy_rate;
    result.pump_power_w = pump_power;
    result.mechanical_loss_w = (1.0 - input->shaft_efficiency) * result.turbine_power_w;
    result.main_throat_area_m2 = result.main_mass_flow_kg_per_s / result.main_nozzle.throat.mass_flux_kg_per_m2_s;
    result.main_thrust_n = result.main_mass_flow_kg_per_s * result.main_nozzle.effective_velocity_m_per_s;
    result.total_thrust_n = result.main_thrust_n + result.branch_thrust_n;
    result.main_effective_velocity_m_per_s = result.main_nozzle.effective_velocity_m_per_s;
    result.engine_effective_velocity_m_per_s = result.total_thrust_n / input->total_mass_flow_kg_per_s;
    result.engine_specific_impulse_s = result.engine_effective_velocity_m_per_s / 9.80665;
    result.mass_residual_kg_per_s = input->total_mass_flow_kg_per_s - result.main_mass_flow_kg_per_s - result.external_mass_flow_kg_per_s;
    result.shaft_residual_w = input->shaft_efficiency * result.branch_mass_flow_kg_per_s * result.turbine.specific_work_j_per_kg - pump_power - input->auxiliary_power_w;
    inlet_enthalpy_rate = fuel.mass_flow_kg_per_s * fuel.inlet_h_j_per_kg + oxidizer.mass_flow_kg_per_s * oxidizer.inlet_h_j_per_kg;
    exit_enthalpy_rate = result.main_mass_flow_kg_per_s * (result.main_nozzle.exit.gas.h_j_per_kg +
        0.5 * result.main_nozzle.exit.velocity_m_per_s * result.main_nozzle.exit.velocity_m_per_s);
    result.inlet_enthalpy_rate_w = inlet_enthalpy_rate;
    result.exit_total_enthalpy_rate_w = exit_enthalpy_rate;
    result.energy_residual_w = inlet_enthalpy_rate + result.generator_heat_w + result.chamber_heat_w -
        exit_enthalpy_rate - input->auxiliary_power_w - result.mechanical_loss_w;
    result.mass_relative_residual = result.mass_residual_kg_per_s / input->total_mass_flow_kg_per_s;
    result.shaft_relative_residual = result.shaft_residual_w / fmax(1.0, pump_power + input->auxiliary_power_w);
    scale = fmax(1.0, fabs(inlet_enthalpy_rate) + fabs(result.generator_heat_w) + fabs(result.chamber_heat_w) + fabs(exit_enthalpy_rate));
    result.energy_relative_residual = result.energy_residual_w / scale;
    if (!rp_isfinite(result.total_thrust_n) || result.total_thrust_n <= 0.0 || !rp_isfinite(result.engine_specific_impulse_s) ||
        !rp_isfinite(result.main_throat_area_m2) || result.main_throat_area_m2 <= 0.0 ||
        !rp_isfinite(result.generator_heat_w) || !rp_isfinite(result.chamber_heat_w) || !rp_isfinite(result.energy_residual_w) ||
        !rp_isfinite(scale) || !rp_isfinite(result.mass_relative_residual) || !rp_isfinite(result.shaft_relative_residual) ||
        !rp_isfinite(result.energy_relative_residual)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite staged-cycle energy, geometry, thrust or residual.");
    }
    if (fabs(result.mass_relative_residual) > 1e-12 || fabs(result.shaft_relative_residual) > 1e-8 || fabs(result.energy_relative_residual) > 1e-10) {
        return rp_error_set(error, RP_NO_CONVERGENCE, "Staged-cycle mass, shaft or energy residual exceeds tolerance.");
    }
    *output = result; rp_error_clear(error); return RP_OK;
}
