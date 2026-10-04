#include "rocketperf/frozen_nozzle.h"
#include "rocketperf/numeric.h"

#include <math.h>
#include <stddef.h>

typedef struct {
    RpGasMixture chamber;
    double throat_flux;
    double area_ratio;
} FrozenContext;

static RpStatus flow_station(const FrozenContext *context, double temperature,
                              RpFrozenFlowStation *output, RpError *error)
{
    RpFrozenFlowStation station = {0};
    RpGasMixture at_chamber_pressure;
    RpStatus status = rp_cho_mixture_evaluate(context->chamber.mole_fractions, temperature,
                                              context->chamber.pressure_pa, &at_chamber_pressure, error);
    double pressure;
    double kinetic_energy;
    double gamma;
    double sound_squared;
    if (status != RP_OK) { return status; }
    pressure = context->chamber.pressure_pa * exp((at_chamber_pressure.s_j_per_kg_k -
               context->chamber.s_j_per_kg_k) / context->chamber.gas_constant_j_per_kg_k);
    if (!rp_isfinite(pressure) || pressure <= 0.0) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Frozen nozzle pressure underflow or overflow.");
    }
    status = rp_cho_mixture_evaluate(context->chamber.mole_fractions, temperature, pressure, &station.gas, error);
    if (status != RP_OK) { return status; }
    kinetic_energy = context->chamber.h_j_per_kg - station.gas.h_j_per_kg;
    if (kinetic_energy < 0.0 || !rp_isfinite(kinetic_energy)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Negative or non-finite frozen nozzle kinetic energy.");
    }
    gamma = station.gas.cp_frozen_j_per_kg_k /
        (station.gas.cp_frozen_j_per_kg_k - station.gas.gas_constant_j_per_kg_k);
    sound_squared = gamma * station.gas.gas_constant_j_per_kg_k * temperature;
    station.velocity_m_per_s = sqrt(2.0 * kinetic_energy);
    station.mach = station.velocity_m_per_s / sqrt(sound_squared);
    station.mass_flux_kg_per_m2_s = pressure / (station.gas.gas_constant_j_per_kg_k * temperature) * station.velocity_m_per_s;
    station.energy_residual_j_per_kg = station.gas.h_j_per_kg +
        0.5 * station.velocity_m_per_s * station.velocity_m_per_s - context->chamber.h_j_per_kg;
    station.entropy_residual_j_per_kg_k = station.gas.s_j_per_kg_k - context->chamber.s_j_per_kg_k;
    if (!rp_isfinite(sound_squared) || sound_squared <= 0.0 || !rp_isfinite(station.mach) ||
        !rp_isfinite(station.mass_flux_kg_per_m2_s) || !rp_isfinite(station.energy_residual_j_per_kg) ||
        !rp_isfinite(station.entropy_residual_j_per_kg_k)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite frozen flow station.");
    }
    *output = station;
    return RP_OK;
}

static double sonic_equation(double temperature, const void *opaque)
{
    const FrozenContext *context = opaque;
    RpFrozenFlowStation station = {0};
    if (flow_station(context, temperature, &station, NULL) != RP_OK) { return NAN; }
    return station.mach * station.mach - 1.0;
}

static double area_equation(double temperature, const void *opaque)
{
    const FrozenContext *context = opaque;
    RpFrozenFlowStation station = {0};
    if (flow_station(context, temperature, &station, NULL) != RP_OK || station.mass_flux_kg_per_m2_s <= 0.0) { return NAN; }
    return station.mass_flux_kg_per_m2_s * context->area_ratio / context->throat_flux - 1.0;
}

RpStatus rp_nozzle_solve_frozen(const RpFrozenNozzleInput *input,
                                const RpRootOptions *options,
                                RpFrozenNozzleResult *output, RpError *error)
{
    const RpRootOptions defaults = {1e-8, 1e-12, 1e-11, 200U};
    const RpRootOptions policy = options != NULL ? *options : defaults;
    RpFrozenNozzleResult result = {0};
    FrozenContext context = {0};
    RpRootResult root;
    RpStatus status;
    double minimum_temperature = 0.0;
    if (input == NULL || output == NULL || !rp_isfinite(input->area_ratio) || input->area_ratio < 1.0 ||
        input->area_ratio > 1e4 || !rp_isfinite(input->ambient_pressure_pa) || input->ambient_pressure_pa < 0.0) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid frozen nozzle input, area ratio or ambient pressure.");
    }
    status = rp_cho_mixture_evaluate(input->mole_fractions, input->chamber_temperature_k,
                                     input->chamber_pressure_pa, &context.chamber, error);
    if (status != RP_OK) { return status; }
    for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
        if (input->mole_fractions[i] > 0.0) {
            const RpNasa9Species *species = rp_thermo_find_species(rp_cho_species_id(i));
            minimum_temperature = fmax(minimum_temperature, species->ranges[0].t_min_k);
        }
    }
    if (input->chamber_temperature_k <= minimum_temperature) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "No frozen expansion interval inside the NASA9 temperature domain.");
    }
    status = rp_root_bisect(sonic_equation, &context, minimum_temperature, input->chamber_temperature_k, &policy, &root, error);
    if (status != RP_OK) { return status; }
    status = flow_station(&context, root.x, &result.throat, error);
    if (status != RP_OK) { return status; }
    context.throat_flux = result.throat.mass_flux_kg_per_m2_s;
    context.area_ratio = input->area_ratio;
    if (input->area_ratio == 1.0) { result.exit = result.throat; }
    else {
        status = rp_root_bisect(area_equation, &context, minimum_temperature, root.x, &policy, &root, error);
        if (status != RP_OK) { return status; }
        status = flow_station(&context, root.x, &result.exit, error);
        if (status != RP_OK) { return status; }
    }
    if (input->ambient_pressure_pa > result.exit.gas.pressure_pa) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Overexpanded frozen nozzle is outside the supported no-shock domain.");
    }
    result.chamber = context.chamber;
    result.cstar_m_per_s = input->chamber_pressure_pa / context.throat_flux;
    result.vacuum_effective_velocity_m_per_s = result.exit.velocity_m_per_s +
        result.exit.gas.pressure_pa * input->area_ratio / context.throat_flux;
    result.effective_velocity_m_per_s = result.exit.velocity_m_per_s +
        (result.exit.gas.pressure_pa - input->ambient_pressure_pa) * input->area_ratio / context.throat_flux;
    result.thrust_coefficient = result.effective_velocity_m_per_s / result.cstar_m_per_s;
    result.continuity_relative_residual = area_equation(result.exit.gas.temperature_k, &context);
    result.sonic_relative_residual = result.throat.mach * result.throat.mach - 1.0;
    if (!rp_isfinite(result.cstar_m_per_s) || result.cstar_m_per_s <= 0.0 ||
        !rp_isfinite(result.effective_velocity_m_per_s) || result.effective_velocity_m_per_s <= 0.0 ||
        !rp_isfinite(result.vacuum_effective_velocity_m_per_s) || !rp_isfinite(result.thrust_coefficient) ||
        !rp_isfinite(result.continuity_relative_residual) || !rp_isfinite(result.sonic_relative_residual)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite frozen nozzle output.");
    }
    if (fabs(result.continuity_relative_residual) > 1e-8 || fabs(result.sonic_relative_residual) > 1e-8 ||
        fabs(result.exit.energy_residual_j_per_kg) > 1e-5 || fabs(result.throat.energy_residual_j_per_kg) > 1e-5 ||
        fabs(result.exit.entropy_residual_j_per_kg_k) > 1e-7 || fabs(result.throat.entropy_residual_j_per_kg_k) > 1e-7 ||
        result.exit.mach < 1.0 - 1e-8) {
        return rp_error_set(error, RP_NO_CONVERGENCE, "Frozen nozzle physical residual exceeds tolerance.");
    }
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}

RpStatus rp_nozzle_solve_frozen_fixed_area(const RpFrozenNozzleInput *input,
                                           double throat_area_m2,
                                           const RpRootOptions *options,
                                           RpFrozenNozzleFixedResult *output,
                                           RpError *error)
{
    RpFrozenNozzleFixedResult result = {0};
    RpStatus status;
    if (output == NULL || !rp_isfinite(throat_area_m2) || throat_area_m2 <= 0.0) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Fixed throat area must be finite and positive.");
    }
    status = rp_nozzle_solve_frozen(input, options, &result.nozzle, error);
    if (status != RP_OK) { return status; }
    result.throat_area_m2 = throat_area_m2;
    result.exit_area_m2 = throat_area_m2 * input->area_ratio;
    result.mass_flow_kg_per_s = throat_area_m2 * result.nozzle.throat.mass_flux_kg_per_m2_s;
    result.thrust_n = result.mass_flow_kg_per_s * result.nozzle.effective_velocity_m_per_s;
    result.specific_impulse_s = result.nozzle.effective_velocity_m_per_s / 9.80665;
    if (!rp_isfinite(result.exit_area_m2) || result.exit_area_m2 <= 0.0 ||
        !rp_isfinite(result.mass_flow_kg_per_s) || result.mass_flow_kg_per_s <= 0.0 ||
        !rp_isfinite(result.thrust_n) || result.thrust_n <= 0.0 ||
        !rp_isfinite(result.specific_impulse_s) || result.specific_impulse_s <= 0.0) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Fixed-geometry nozzle dimensions or performance overflow/underflow.");
    }
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}
