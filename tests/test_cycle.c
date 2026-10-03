#include "rocketperf/cycle.h"
#include "rocketperf/numeric.h"

#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

static unsigned int checks = 0U;
static unsigned int failures = 0U;
static void check(int condition, const char *label, int line)
{
    ++checks;
    if (!condition) { ++failures; (void)fprintf(stderr, "FAIL line %d: %s\n", line, label); }
}
#define CHECK(condition) check((condition), #condition, __LINE__)
static int near(double actual, double expected, double tolerance)
{
    return rp_isfinite(actual) && fabs(actual - expected) <= tolerance;
}
static RpCycleInput benchmark(void)
{
    RpCycleInput input = {0};
    input.total_mass_flow_kg_per_s = 100.0;
    input.overall_oxidizer_fuel_ratio = 3.4;
    input.fuel_pump = (RpLiquidPumpInput){0.0, 422.0, 2e5, 7e6, 0.7, -4650000.0};
    input.oxidizer_pump = (RpLiquidPumpInput){0.0, 1141.0, 2e5, 7e6, 0.75, 0.0};
    input.chamber_pressure_pa = 5e6; input.chamber_temperature_k = 3300.0;
    input.main_area_ratio = 10.0;
    input.generator_oxidizer_fuel_ratio = 1.0; input.generator_temperature_k = 1800.0;
    input.turbine_inlet_pressure_pa = 6e6; input.turbine_outlet_pressure_pa = 5e5;
    input.turbine_efficiency = 0.7; input.shaft_efficiency = 0.95;
    input.auxiliary_power_w = 10000.0; input.maximum_branch_fraction = 0.25;
    input.branch_area_ratio = 2.0; input.branch_axial_projection = 1.0;
    return input;
}
static void test_pump(void)
{
    RpLiquidPumpInput input = {10.0, 1000.0, 1e5, 1.1e6, 0.8, -1e6};
    RpLiquidPumpResult result, sentinel;
    CHECK(rp_liquid_pump_solve(&input, &result, NULL) == RP_OK);
    CHECK(near(result.specific_work_j_per_kg, 1250.0, 1e-10));
    CHECK(near(result.shaft_power_w, 12500.0, 1e-8));
    CHECK(near(result.outlet_h_j_per_kg, -998750.0, 1e-8));
    CHECK(fabs(result.energy_residual_w) < 1e-8);
    input.mass_flow_kg_per_s = 0.0;
    CHECK(rp_liquid_pump_solve(&input, &result, NULL) == RP_OK);
    CHECK(result.shaft_power_w == 0.0 && result.energy_residual_w == 0.0);
    input.outlet_pressure_pa = input.inlet_pressure_pa;
    CHECK(rp_liquid_pump_solve(&input, &result, NULL) == RP_OK);
    CHECK(result.specific_work_j_per_kg == 0.0);
    memset(&sentinel, 0x5a, sizeof(sentinel)); result = sentinel;
    CHECK(rp_liquid_pump_solve(NULL, &result, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_liquid_pump_solve(&input, NULL, NULL) == RP_INVALID_ARGUMENT);
    input.efficiency = 0.0; CHECK(rp_liquid_pump_solve(&input, &result, NULL) == RP_INVALID_ARGUMENT);
    input.efficiency = 1.1; CHECK(rp_liquid_pump_solve(&input, &result, NULL) == RP_INVALID_ARGUMENT);
    input.efficiency = 0.8; input.density_kg_per_m3 = NAN;
    CHECK(rp_liquid_pump_solve(&input, &result, NULL) == RP_INVALID_ARGUMENT);
    input.density_kg_per_m3 = 1000.0; input.mass_flow_kg_per_s = -1.0;
    CHECK(rp_liquid_pump_solve(&input, &result, NULL) == RP_INVALID_ARGUMENT);
    input.mass_flow_kg_per_s = 1.0; input.outlet_pressure_pa = 1.0;
    CHECK(rp_liquid_pump_solve(&input, &result, NULL) == RP_INVALID_ARGUMENT);
    input.outlet_pressure_pa = 1e308; input.density_kg_per_m3 = 1e-100;
    CHECK(rp_liquid_pump_solve(&input, &result, NULL) == RP_NUMERIC_ERROR);
    CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
}
static void test_turbine(void)
{
    /* Atomic H has exactly cp/R=2.5 below 1000 K in the pinned dataset.
     * T_s=T_in*(p_out/p_in)^(R/cp) is independent of the root solver. */
    RpFrozenTurbineInput input = {0};
    RpFrozenTurbineResult ideal, actual, sentinel;
    const double cp = 2.5 * RP_UNIVERSAL_GAS_CONSTANT_J_KMOL_K /
        rp_thermo_find_species("H")->molar_mass_kg_per_kmol;
    const double expected_t = 700.0 * pow(0.25, 0.4);
    RpRootOptions options = rp_root_default_options();
    input.temperature_k = 700.0; input.inlet_pressure_pa = 1e6;
    input.outlet_pressure_pa = 2.5e5; input.efficiency = 1.0;
    input.mole_fractions[6] = 1.0;
    CHECK(rp_frozen_turbine_solve(&input, NULL, &ideal, NULL) == RP_OK);
    CHECK(near(ideal.outlet.temperature_k, expected_t, 1e-7));
    CHECK(near(ideal.specific_work_j_per_kg, cp * (700.0 - expected_t), 0.01));
    CHECK(fabs(ideal.entropy_generation_j_per_kg_k) < 1e-7);
    input.efficiency = 0.6;
    CHECK(rp_frozen_turbine_solve(&input, NULL, &actual, NULL) == RP_OK);
    CHECK(near(actual.outlet.temperature_k, 700.0 - 0.6 * (700.0 - expected_t), 1e-7));
    CHECK(near(actual.specific_work_j_per_kg, 0.6 * ideal.specific_work_j_per_kg, 0.01));
    CHECK(actual.outlet.temperature_k > ideal.outlet.temperature_k);
    CHECK(actual.entropy_generation_j_per_kg_k > 0.0);
    input.outlet_pressure_pa = input.inlet_pressure_pa;
    CHECK(rp_frozen_turbine_solve(&input, NULL, &actual, NULL) == RP_OK);
    CHECK(actual.specific_work_j_per_kg == 0.0);
    memset(&sentinel, 0x5a, sizeof(sentinel)); actual = sentinel;
    CHECK(rp_frozen_turbine_solve(NULL, NULL, &actual, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_frozen_turbine_solve(&input, NULL, NULL, NULL) == RP_INVALID_ARGUMENT);
    input.outlet_pressure_pa = 2e6;
    CHECK(rp_frozen_turbine_solve(&input, NULL, &actual, NULL) == RP_INVALID_ARGUMENT);
    input.outlet_pressure_pa = 2.5e5; input.efficiency = 1.01;
    CHECK(rp_frozen_turbine_solve(&input, NULL, &actual, NULL) == RP_INVALID_ARGUMENT);
    input.efficiency = 0.0; CHECK(rp_frozen_turbine_solve(&input, NULL, &actual, NULL) == RP_INVALID_ARGUMENT);
    input.efficiency = 0.6; input.temperature_k = NAN;
    CHECK(rp_frozen_turbine_solve(&input, NULL, &actual, NULL) == RP_INVALID_ARGUMENT);
    input.temperature_k = 700.0; input.outlet_pressure_pa = 1.0;
    CHECK(rp_frozen_turbine_solve(&input, NULL, &actual, NULL) == RP_NOT_BRACKETED);
    input.outlet_pressure_pa = 2.5e5; options.max_iterations = 1U;
    CHECK(rp_frozen_turbine_solve(&input, &options, &actual, NULL) == RP_NO_CONVERGENCE);
    options.x_absolute_tolerance = NAN;
    CHECK(rp_frozen_turbine_solve(&input, &options, &actual, NULL) == RP_INVALID_ARGUMENT);
    CHECK(memcmp(&actual, &sentinel, sizeof(actual)) == 0);
}
static void check_cycle(const RpCycleInput *input, const RpCycleResult *result)
{
    const double fuel = input->total_mass_flow_kg_per_s / (1.0 + input->overall_oxidizer_fuel_ratio);
    const double oxidizer = input->total_mass_flow_kg_per_s - fuel;
    const double pump = fuel * (input->fuel_pump.outlet_pressure_pa - input->fuel_pump.inlet_pressure_pa) /
        (input->fuel_pump.density_kg_per_m3 * input->fuel_pump.efficiency) +
        oxidizer * (input->oxidizer_pump.outlet_pressure_pa - input->oxidizer_pump.inlet_pressure_pa) /
        (input->oxidizer_pump.density_kg_per_m3 * input->oxidizer_pump.efficiency);
    const double turbine_drop = result->turbine.inlet.h_j_per_kg - result->turbine.outlet.h_j_per_kg;
    const double branch = (pump + input->auxiliary_power_w) / input->shaft_efficiency / turbine_drop;
    const double main_exit = result->main_mass_flow_kg_per_s * (result->main_nozzle.exit.gas.h_j_per_kg +
        0.5 * pow(result->main_nozzle.exit.velocity_m_per_s, 2.0));
    const double branch_exit = result->external_mass_flow_kg_per_s * (result->branch_nozzle.exit.gas.h_j_per_kg +
        0.5 * pow(result->branch_nozzle.exit.velocity_m_per_s, 2.0));
    CHECK(near(result->pump_power_w, pump, 1e-6));
    CHECK(near(result->branch_mass_flow_kg_per_s, branch, 1e-10));
    CHECK(near(result->main_fuel_mass_flow_kg_per_s + result->branch_fuel_mass_flow_kg_per_s, fuel, 1e-12));
    CHECK(near(result->main_oxidizer_mass_flow_kg_per_s + result->branch_oxidizer_mass_flow_kg_per_s, oxidizer, 1e-12));
    CHECK(near(result->main_oxidizer_fuel_ratio, result->main_oxidizer_mass_flow_kg_per_s / result->main_fuel_mass_flow_kg_per_s, 1e-12));
    CHECK(near(result->main_mass_flow_kg_per_s + result->external_mass_flow_kg_per_s, input->total_mass_flow_kg_per_s, 1e-12));
    CHECK(result->returned_mass_flow_kg_per_s == 0.0);
    CHECK(near(result->branch_thrust_n, result->external_mass_flow_kg_per_s *
        (result->branch_nozzle.exit.velocity_m_per_s + (result->branch_nozzle.exit.gas.pressure_pa - input->ambient_pressure_pa) *
        input->branch_area_ratio / result->branch_nozzle.throat.mass_flux_kg_per_m2_s) * input->branch_axial_projection, 1e-6));
    CHECK(near(result->engine_specific_impulse_s, (result->main_thrust_n + result->branch_thrust_n) /
        input->total_mass_flow_kg_per_s / 9.80665, 1e-10));
    CHECK(near(result->inlet_enthalpy_rate_w, fuel * input->fuel_pump.inlet_h_j_per_kg + oxidizer * input->oxidizer_pump.inlet_h_j_per_kg, 1e-6));
    CHECK(near(result->exit_total_enthalpy_rate_w, main_exit + branch_exit, 1e-6));
    CHECK(fabs(result->inlet_enthalpy_rate_w + result->generator_heat_w + result->chamber_heat_w -
        main_exit - branch_exit - input->auxiliary_power_w - result->mechanical_loss_w) < 0.01);
    CHECK(fabs(result->mass_relative_residual) < 1e-12);
    CHECK(fabs(result->shaft_relative_residual) < 1e-8);
    CHECK(fabs(result->energy_relative_residual) < 1e-10);
}
static void test_cycle(void)
{
    RpCycleInput input = benchmark();
    RpCycleResult result, sideways, zero;
    RpError error;
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &result, &error) == RP_OK);
    if (error.code != RP_OK) { (void)fprintf(stderr, "%s\n", error.message); return; }
    CHECK(result.branch_nozzle_active && result.branch_mass_flow_kg_per_s > 0.0);
    check_cycle(&input, &result);
    (void)printf("Cycle: branch=%.9f kg/s, pump=%.9f W, F=%.9f N, Isp=%.9f s, energy=%.9g W\n",
        result.branch_mass_flow_kg_per_s, result.pump_power_w, result.total_thrust_n,
        result.engine_specific_impulse_s, result.energy_residual_w);
    input.branch_axial_projection = 0.0;
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &sideways, NULL) == RP_OK);
    CHECK(sideways.branch_thrust_n == 0.0);
    CHECK(near(sideways.branch_mass_flow_kg_per_s, result.branch_mass_flow_kg_per_s, 1e-12));
    CHECK(near(sideways.exit_total_enthalpy_rate_w, result.exit_total_enthalpy_rate_w, 1e-6));
    CHECK(near(result.total_thrust_n - sideways.total_thrust_n, result.branch_thrust_n, 1e-6));
    input = benchmark(); input.fuel_pump.inlet_pressure_pa = input.fuel_pump.outlet_pressure_pa;
    input.oxidizer_pump.inlet_pressure_pa = input.oxidizer_pump.outlet_pressure_pa; input.auxiliary_power_w = 0.0;
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &zero, NULL) == RP_OK);
    CHECK(zero.branch_mass_flow_kg_per_s == 0.0 && zero.branch_thrust_n == 0.0 && !zero.branch_nozzle_active);
    CHECK(zero.main_mass_flow_kg_per_s == input.total_mass_flow_kg_per_s);
    CHECK(near(zero.main_oxidizer_fuel_ratio, input.overall_oxidizer_fuel_ratio, 1e-14));
    CHECK(near(zero.engine_effective_velocity_m_per_s, zero.main_nozzle.effective_velocity_m_per_s, 1e-10));
    CHECK(fabs(zero.energy_relative_residual) < 1e-10);
    input.turbine_outlet_pressure_pa = input.turbine_inlet_pressure_pa;
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &zero, NULL) == RP_OK);
    CHECK(zero.turbine.specific_work_j_per_kg == 0.0 && zero.branch_mass_flow_kg_per_s == 0.0);
    for (unsigned int i = 0U; i < 6U; ++i) {
        RpCycleInput varied = benchmark();
        varied.turbine_efficiency = 0.5 + 0.1 * (double)i;
        CHECK(rp_cycle_solve_prescribed(&varied, NULL, &sideways, NULL) == RP_OK);
        check_cycle(&varied, &sideways);
    }
    /* Uniform flow scaling preserves intensive states and doubles extensive output. */
    input = benchmark(); input.total_mass_flow_kg_per_s *= 2.0; input.auxiliary_power_w *= 2.0;
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &sideways, NULL) == RP_OK);
    CHECK(near(sideways.total_thrust_n, 2.0 * result.total_thrust_n, 1e-5));
    CHECK(near(sideways.engine_specific_impulse_s, result.engine_specific_impulse_s, 1e-10));
}
static void test_cycle_failures(void)
{
    RpCycleInput input = benchmark();
    RpCycleResult result, sentinel;
    RpRootOptions options = rp_root_default_options();
    memset(&sentinel, 0x5a, sizeof(sentinel)); result = sentinel;
    CHECK(rp_cycle_solve_prescribed(NULL, NULL, &result, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_cycle_solve_prescribed(&input, NULL, NULL, NULL) == RP_INVALID_ARGUMENT);
    input.return_fraction = 0.5; CHECK(rp_cycle_solve_prescribed(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = benchmark(); input.return_pressure_drop_pa = 1.0;
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = benchmark(); input.maximum_branch_fraction = 1e-6;
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = benchmark(); input.fuel_pump.outlet_pressure_pa = 4e6;
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = benchmark(); input.turbine_outlet_pressure_pa = input.turbine_inlet_pressure_pa;
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = benchmark(); input.auxiliary_power_w = 1e10;
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = benchmark(); input.maximum_branch_fraction = 0.9;
    input.generator_oxidizer_fuel_ratio = 0.1; input.auxiliary_power_w = 1e8;
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = benchmark(); input.chamber_temperature_k = 999.0;
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = benchmark(); input.ambient_pressure_pa = 1e6;
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = benchmark(); input.fuel_pump.mass_flow_kg_per_s = 1.0;
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &result, NULL) == RP_INVALID_ARGUMENT);
    input = benchmark(); input.overall_oxidizer_fuel_ratio = NAN;
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &result, NULL) == RP_INVALID_ARGUMENT);
    input = benchmark(); input.total_mass_flow_kg_per_s = 0.0;
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &result, NULL) == RP_INVALID_ARGUMENT);
    input = benchmark(); input.branch_axial_projection = 1.01;
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &result, NULL) == RP_INVALID_ARGUMENT);
    input = benchmark(); options.max_iterations = 1U;
    CHECK(rp_cycle_solve_prescribed(&input, &options, &result, NULL) == RP_NO_CONVERGENCE);
    CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
    {
#define OFFSET(member) offsetof(RpCycleInput, member)
#define PUMP_OFFSET(name, member) (offsetof(RpCycleInput, name) + offsetof(RpLiquidPumpInput, member))
        const size_t offsets[] = {
            OFFSET(total_mass_flow_kg_per_s), OFFSET(overall_oxidizer_fuel_ratio),
            OFFSET(chamber_pressure_pa), OFFSET(chamber_temperature_k), OFFSET(main_area_ratio),
            OFFSET(generator_oxidizer_fuel_ratio), OFFSET(generator_temperature_k),
            OFFSET(turbine_inlet_pressure_pa), OFFSET(turbine_outlet_pressure_pa), OFFSET(turbine_efficiency),
            OFFSET(shaft_efficiency), OFFSET(auxiliary_power_w), OFFSET(maximum_branch_fraction),
            OFFSET(return_fraction), OFFSET(return_pressure_drop_pa), OFFSET(branch_area_ratio),
            OFFSET(branch_axial_projection), OFFSET(ambient_pressure_pa),
            PUMP_OFFSET(fuel_pump, density_kg_per_m3), PUMP_OFFSET(fuel_pump, inlet_pressure_pa),
            PUMP_OFFSET(fuel_pump, outlet_pressure_pa), PUMP_OFFSET(fuel_pump, efficiency), PUMP_OFFSET(fuel_pump, inlet_h_j_per_kg),
            PUMP_OFFSET(oxidizer_pump, density_kg_per_m3), PUMP_OFFSET(oxidizer_pump, inlet_pressure_pa),
            PUMP_OFFSET(oxidizer_pump, outlet_pressure_pa), PUMP_OFFSET(oxidizer_pump, efficiency), PUMP_OFFSET(oxidizer_pump, inlet_h_j_per_kg)
        };
        const double invalid = NAN;
        for (size_t k = 0U; k < sizeof(offsets) / sizeof(offsets[0]); ++k) {
            input = benchmark();
            memcpy((unsigned char *)&input + offsets[k], &invalid, sizeof(invalid));
            CHECK(rp_cycle_solve_prescribed(&input, NULL, &result, NULL) != RP_OK);
            CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
        }
#undef OFFSET
#undef PUMP_OFFSET
    }
}
int main(void)
{
    test_pump(); test_turbine(); test_cycle(); test_cycle_failures();
    (void)printf("cycle: %u checks, %u failures\n", checks, failures);
    return failures == 0U ? 0 : 1;
}
