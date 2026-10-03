#include "rocketperf/cycle.h"
#include "rocketperf/numeric.h"

#include <math.h>
#include <stddef.h>

RpStatus rp_liquid_pump_solve(const RpLiquidPumpInput *input,
                              RpLiquidPumpResult *output, RpError *error)
{
    RpLiquidPumpResult result = {0};
    if (input == NULL || output == NULL || !rp_isfinite(input->mass_flow_kg_per_s) || input->mass_flow_kg_per_s < 0.0 ||
        !rp_isfinite(input->density_kg_per_m3) || input->density_kg_per_m3 <= 0.0 ||
        !rp_isfinite(input->inlet_pressure_pa) || input->inlet_pressure_pa <= 0.0 ||
        !rp_isfinite(input->outlet_pressure_pa) || input->outlet_pressure_pa < input->inlet_pressure_pa ||
        !rp_isfinite(input->efficiency) || input->efficiency <= 0.0 || input->efficiency > 1.0 ||
        !rp_isfinite(input->inlet_h_j_per_kg)) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid constant-density pump flow, density, pressures, enthalpy or efficiency.");
    }
    result.specific_work_j_per_kg = (input->outlet_pressure_pa - input->inlet_pressure_pa) / input->density_kg_per_m3 / input->efficiency;
    result.shaft_power_w = input->mass_flow_kg_per_s * result.specific_work_j_per_kg;
    result.outlet_h_j_per_kg = input->inlet_h_j_per_kg + result.specific_work_j_per_kg;
    result.energy_residual_w = input->mass_flow_kg_per_s * (result.outlet_h_j_per_kg - input->inlet_h_j_per_kg) - result.shaft_power_w;
    if (!rp_isfinite(result.specific_work_j_per_kg) || !rp_isfinite(result.shaft_power_w) ||
        !rp_isfinite(result.outlet_h_j_per_kg) || !rp_isfinite(result.energy_residual_w)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite pump state or power.");
    }
    if (fabs(result.energy_residual_w) > 1e-8 * fmax(1.0, result.shaft_power_w)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Pump enthalpy increment lost numerical precision.");
    }
    *output = result; rp_error_clear(error); return RP_OK;
}

typedef struct {
    const double *fractions;
    double pressure;
    double target;
    int entropy;
} TurbineRoot;

static double turbine_equation(double temperature, const void *opaque)
{
    const TurbineRoot *context = opaque;
    RpGasMixture gas = {0};
    if (rp_cho_mixture_evaluate(context->fractions, temperature, context->pressure, &gas, NULL) != RP_OK) { return NAN; }
    return (context->entropy ? gas.s_j_per_kg_k : gas.h_j_per_kg) - context->target;
}

RpStatus rp_frozen_turbine_solve(const RpFrozenTurbineInput *input,
                                 const RpRootOptions *options,
                                 RpFrozenTurbineResult *output, RpError *error)
{
    const RpRootOptions defaults = {1e-9, 1e-12, 1e-9, 200U};
    const RpRootOptions policy = options != NULL ? *options : defaults;
    RpFrozenTurbineResult result = {0};
    RpRootResult root = {0};
    TurbineRoot context;
    double minimum_temperature = 0.0;
    double ideal_drop;
    RpStatus status;
    if (input == NULL || output == NULL || !rp_isfinite(input->efficiency) || input->efficiency <= 0.0 || input->efficiency > 1.0 ||
        !rp_isfinite(input->outlet_pressure_pa) || input->outlet_pressure_pa <= 0.0 ||
        !rp_isfinite(input->inlet_pressure_pa) || input->outlet_pressure_pa > input->inlet_pressure_pa ||
        !rp_isfinite(policy.x_absolute_tolerance) || policy.x_absolute_tolerance <= 0.0 ||
        !rp_isfinite(policy.x_relative_tolerance) || policy.x_relative_tolerance < 0.0 ||
        !rp_isfinite(policy.f_absolute_tolerance) || policy.f_absolute_tolerance < 0.0 || policy.max_iterations == 0U || policy.max_iterations > 100000U) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid frozen turbine pressures, efficiency, options or output.");
    }
    status = rp_cho_mixture_evaluate(input->mole_fractions, input->temperature_k, input->inlet_pressure_pa, &result.inlet, error);
    if (status != RP_OK) { return status; }
    if (input->outlet_pressure_pa == input->inlet_pressure_pa) {
        result.outlet = result.inlet; result.isentropic_outlet = result.inlet;
        *output = result; rp_error_clear(error); return RP_OK;
    }
    for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
        if (input->mole_fractions[i] > 0.0) {
            minimum_temperature = fmax(minimum_temperature, rp_thermo_find_species(rp_cho_species_id(i))->ranges[0].t_min_k);
        }
    }
    if (input->temperature_k <= minimum_temperature) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "No turbine expansion interval in the NASA9 temperature domain.");
    }
    context.fractions = input->mole_fractions; context.pressure = input->outlet_pressure_pa;
    context.target = result.inlet.s_j_per_kg_k; context.entropy = 1;
    status = rp_root_bisect(turbine_equation, &context, minimum_temperature, input->temperature_k, &policy, &root, error);
    if (status != RP_OK) { return status; }
    status = rp_cho_mixture_evaluate(input->mole_fractions, root.x, input->outlet_pressure_pa, &result.isentropic_outlet, error);
    if (status != RP_OK) { return status; }
    ideal_drop = result.inlet.h_j_per_kg - result.isentropic_outlet.h_j_per_kg;
    if (!rp_isfinite(ideal_drop) || ideal_drop <= 0.0) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Non-positive isentropic turbine work.");
    }
    context.target = result.inlet.h_j_per_kg - input->efficiency * ideal_drop; context.entropy = 0;
    if (input->efficiency == 1.0) { result.outlet = result.isentropic_outlet; }
    else {
        status = rp_root_bisect(turbine_equation, &context, result.isentropic_outlet.temperature_k, input->temperature_k, &policy, &root, error);
        if (status != RP_OK) { return status; }
        status = rp_cho_mixture_evaluate(input->mole_fractions, root.x, input->outlet_pressure_pa, &result.outlet, error);
        if (status != RP_OK) { return status; }
    }
    result.specific_work_j_per_kg = result.inlet.h_j_per_kg - result.outlet.h_j_per_kg;
    result.efficiency_residual_j_per_kg = result.specific_work_j_per_kg - input->efficiency * ideal_drop;
    result.entropy_generation_j_per_kg_k = result.outlet.s_j_per_kg_k - result.inlet.s_j_per_kg_k;
    if (!rp_isfinite(result.specific_work_j_per_kg) || result.specific_work_j_per_kg <= 0.0 ||
        !rp_isfinite(result.efficiency_residual_j_per_kg) || !rp_isfinite(result.entropy_generation_j_per_kg_k)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite actual turbine work or entropy.");
    }
    if (fabs(result.isentropic_outlet.s_j_per_kg_k - result.inlet.s_j_per_kg_k) > 1e-7 ||
        fabs(result.efficiency_residual_j_per_kg) > 0.01 || result.entropy_generation_j_per_kg_k < -1e-7) {
        return rp_error_set(error, RP_NO_CONVERGENCE, "Turbine physical residual exceeds tolerance.");
    }
    *output = result; rp_error_clear(error); return RP_OK;
}
