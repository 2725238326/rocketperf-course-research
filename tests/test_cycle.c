#include "rocketperf/cycle.h"
#include "rocketperf/cycle_study.h"
#include "rocketperf/engine_cycle.h"
#include "rocketperf/liquid_feed.h"
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
static void test_inlet_assumptions(void)
{
    RpCycleInput input = benchmark();
    RpCycleResult base, changed;
    const double shifts[] = {-1e5, 1e5};
    CHECK(rp_cycle_solve_prescribed(&input, NULL, &base, NULL) == RP_OK);
    for (int side = 0; side < 2; ++side) {
        for (size_t i = 0U; i < sizeof(shifts) / sizeof(shifts[0]); ++i) {
            const double feed = side == 0 ? base.fuel_mass_flow_kg_per_s : base.oxidizer_mass_flow_kg_per_s;
            const double main = side == 0 ? base.main_fuel_mass_flow_kg_per_s : base.main_oxidizer_mass_flow_kg_per_s;
            const double branch = side == 0 ? base.branch_fuel_mass_flow_kg_per_s : base.branch_oxidizer_mass_flow_kg_per_s;
            input = benchmark();
            if (side == 0) { input.fuel_pump.inlet_h_j_per_kg += shifts[i]; }
            else { input.oxidizer_pump.inlet_h_j_per_kg += shifts[i]; }
            CHECK(rp_cycle_solve_prescribed(&input, NULL, &changed, NULL) == RP_OK);
            CHECK(near(changed.pump_power_w, base.pump_power_w, 1e-8));
            CHECK(near(changed.branch_mass_flow_kg_per_s, base.branch_mass_flow_kg_per_s, 1e-12));
            CHECK(near(changed.total_thrust_n, base.total_thrust_n, 1e-8));
            CHECK(near(changed.engine_specific_impulse_s, base.engine_specific_impulse_s, 1e-10));
            CHECK(near(changed.generator_heat_w - base.generator_heat_w, -branch * shifts[i], 1e-6));
            CHECK(near(changed.chamber_heat_w - base.chamber_heat_w, -main * shifts[i], 1e-6));
            CHECK(near(changed.inlet_enthalpy_rate_w - base.inlet_enthalpy_rate_w, feed * shifts[i], 1e-6));
            CHECK(fabs(changed.energy_relative_residual) < 1e-10);
        }
        input = benchmark();
        if (side == 0) { input.fuel_pump.density_kg_per_m3 *= 0.9; }
        else { input.oxidizer_pump.density_kg_per_m3 *= 0.9; }
        CHECK(rp_cycle_solve_prescribed(&input, NULL, &changed, NULL) == RP_OK);
        CHECK(changed.pump_power_w > base.pump_power_w);
        CHECK(changed.branch_mass_flow_kg_per_s > base.branch_mass_flow_kg_per_s);
        CHECK(near(changed.turbine.specific_work_j_per_kg, base.turbine.specific_work_j_per_kg, 1e-6));
        check_cycle(&input, &changed);
    }
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
static void test_study(void)
{
    RpCycleInput input = benchmark();
    RpCycleResult baseline, saved;
    RpCycleStudyPoint points[3], sentinel[3];
    size_t count = 99U;
    const double ratios[] = {10.0, 20.0, 40.0};
    const double projections[] = {0.0, 1.0, 2.0};
    const double invalid[] = {10.0, NAN};
    CHECK(rp_cycle_scan_prescribed(&input, RP_CYCLE_MAIN_AREA_RATIO, ratios, 3U, &baseline, points, 3U, &count, NULL) == RP_OK);
    CHECK(count == 3U && points[0].status == RP_OK && points[1].status == RP_OK && points[2].status == RP_OK);
    CHECK(points[0].metrics.thrust_change_n == 0.0 && !points[0].metrics.elasticity_defined);
    CHECK(points[2].result.total_thrust_n > points[1].result.total_thrust_n);
    CHECK(near(points[2].metrics.main_exit_area_m2, 4.0 * points[0].metrics.main_exit_area_m2, 1e-12));
    CHECK(near(points[2].metrics.main_exit_diameter_m, 2.0 * points[0].metrics.main_exit_diameter_m, 1e-12));
    CHECK(points[2].metrics.branch_flow_change_kg_per_s == 0.0 && points[2].metrics.required_heat_change_w == 0.0);
    CHECK(near(points[2].metrics.isp_secant_elasticity, points[2].metrics.isp_relative_change / 3.0, 1e-12));
    CHECK(rp_cycle_scan_prescribed(&input, RP_CYCLE_BRANCH_PROJECTION, projections, 3U, &baseline, points, 3U, &count, NULL) == RP_OK);
    CHECK(points[0].status == RP_OK && points[1].status == RP_OK && points[2].status == RP_INVALID_ARGUMENT);
    CHECK(near(points[0].metrics.thrust_change_n, -baseline.branch_thrust_n, 1e-8));
    CHECK(points[0].metrics.required_heat_change_w == 0.0 && points[0].metrics.branch_flow_change_kg_per_s == 0.0);
    CHECK(points[2].message[0] != '\0');
    saved = baseline; memset(sentinel, 0x5a, sizeof(sentinel)); memcpy(points, sentinel, sizeof(points));
    CHECK(rp_cycle_scan_prescribed(&input, RP_CYCLE_MAIN_AREA_RATIO, invalid, 2U, &baseline, points, 3U, &count, NULL) == RP_INVALID_ARGUMENT);
    CHECK(count == 0U && memcmp(&baseline, &saved, sizeof(saved)) == 0 && memcmp(points, sentinel, sizeof(points)) == 0);
    CHECK(rp_cycle_scan_prescribed(&input, RP_CYCLE_MAIN_AREA_RATIO, ratios, 3U, &baseline, points, 2U, &count, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_cycle_scan_prescribed(&input, RP_CYCLE_FIELD_COUNT, ratios, 3U, &baseline, points, 3U, &count, NULL) == RP_INVALID_ARGUMENT);
    input.return_fraction = 0.1;
    CHECK(rp_cycle_scan_prescribed(&input, RP_CYCLE_MAIN_AREA_RATIO, ratios, 3U, &baseline, points, 3U, &count, NULL) == RP_OUT_OF_DOMAIN);
    CHECK(count == 0U && memcmp(&baseline, &saved, sizeof(saved)) == 0 && memcmp(points, sentinel, sizeof(points)) == 0);
    for (int f = 0; f < RP_CYCLE_FIELD_COUNT; ++f) {
        CHECK(rp_cycle_study_field_name((RpCycleStudyField)f) != NULL);
        CHECK(rp_isfinite(rp_cycle_study_input_value(&input, (RpCycleStudyField)f)));
    }
    CHECK(rp_cycle_study_field_name(RP_CYCLE_FIELD_COUNT) == NULL);
    CHECK(!rp_isfinite(rp_cycle_study_input_value(NULL, RP_CYCLE_MAIN_AREA_RATIO)));
}
static RpEngineCycleInput adiabatic_benchmark(int staged)
{
    RpEngineCycleInput input = {0};
    RpLiquidFeedState fuel = {0}, oxidizer = {0};
    RpLiquidFeedQuery query = {rp_liquid_feed_dataset_id(), "Methane", RP_LIQUID_SINGLE_PHASE, 120.0, 1e6};
    CHECK(rp_liquid_feed_evaluate(&query, &fuel, NULL) == RP_OK);
    query.fluid_id = "Oxygen"; query.temperature_k = 100.0;
    CHECK(rp_liquid_feed_evaluate(&query, &oxidizer, NULL) == RP_OK);
    input.staged_combustion = staged != 0;
    input.total_mass_flow_kg_per_s = 100.0; input.overall_oxidizer_fuel_ratio = 3.4;
    input.fuel.pump = (RpLiquidPumpInput){0.0, fuel.density_kg_per_m3, 1e6, staged ? 25e6 : 13e6, 0.7, fuel.h_j_per_kg};
    input.oxidizer.pump = (RpLiquidPumpInput){0.0, oxidizer.density_kg_per_m3, 1e6, staged ? 25e6 : 13e6, 0.75, oxidizer.h_j_per_kg};
    input.fuel.basis = input.oxidizer.basis = RP_ENTHALPY_NASA9_CEA_V334;
    input.fuel.elements_kmol_per_kg[0] = 1.0 / rp_thermo_find_species("CH4")->molar_mass_kg_per_kmol;
    input.fuel.elements_kmol_per_kg[1] = 4.0 * input.fuel.elements_kmol_per_kg[0];
    input.oxidizer.elements_kmol_per_kg[2] = 2.0 / rp_thermo_find_species("O2")->molar_mass_kg_per_kmol;
    input.chamber_pressure_pa = 1e7; input.main_area_ratio = 10.0;
    input.preburner_pressure_pa = staged ? 22e6 : 11e6;
    input.preburner_oxidizer_fuel_ratio = staged ? 40.0 : 1.0;
    input.turbine_outlet_pressure_pa = staged ? 0.0 : 8e5;
    input.turbine_efficiency = 0.7; input.shaft_efficiency = 0.95; input.auxiliary_power_w = 1e4;
    input.maximum_branch_fraction = staged ? 0.95 : 0.2;
    input.pump_to_chamber_drop_pa = input.pump_to_preburner_drop_pa = 1e6;
    input.return_pressure_drop_pa = staged ? 1e6 : 0.0;
    input.branch_area_ratio = staged ? 1.0 : 1.5;
    input.branch_axial_projection = staged ? 0.0 : 1.0;
    return input;
}

static void check_adiabatic(const RpEngineCycleInput *input, const RpEngineCycleResult *result)
{
    const RpCycleResult *b = &result->balance;
    const double work = b->turbine.inlet.h_j_per_kg - b->turbine.outlet.h_j_per_kg;
    const double actual_power = b->branch_mass_flow_kg_per_s * work;
    const double main_exit = b->main_mass_flow_kg_per_s * (b->main_nozzle.exit.gas.h_j_per_kg +
        0.5 * pow(b->main_nozzle.exit.velocity_m_per_s, 2.0));
    double branch_exit = 0.0;
    CHECK(near(input->shaft_efficiency * actual_power, b->pump_power_w + input->auxiliary_power_w, 0.1));
    CHECK(near(b->mechanical_loss_w, (1.0 - input->shaft_efficiency) * actual_power, 1e-7));
    CHECK(near(b->main_mass_flow_kg_per_s + b->external_mass_flow_kg_per_s, input->total_mass_flow_kg_per_s, 1e-12));
    CHECK(b->generator_heat_w == 0.0 && b->chamber_heat_w == 0.0);
    CHECK(fabs(result->preburner.enthalpy_residual_j_per_kg) <= 0.01);
    CHECK(fabs(result->chamber.enthalpy_residual_j_per_kg) <= 0.01);
    if (b->branch_nozzle_active) {
        branch_exit = b->external_mass_flow_kg_per_s * (b->branch_nozzle.exit.gas.h_j_per_kg +
            0.5 * pow(b->branch_nozzle.exit.velocity_m_per_s, 2.0));
    }
    CHECK(near(b->exit_total_enthalpy_rate_w, main_exit + branch_exit, 1e-6));
    CHECK(fabs(b->inlet_enthalpy_rate_w - main_exit - branch_exit - input->auxiliary_power_w - b->mechanical_loss_w) < 3.0);
    CHECK(near(b->energy_residual_w, b->inlet_enthalpy_rate_w - main_exit - branch_exit - input->auxiliary_power_w - b->mechanical_loss_w, 1e-6));
    CHECK(near(b->total_thrust_n, b->main_thrust_n + b->branch_thrust_n, 1e-8));
    CHECK(near(b->engine_specific_impulse_s, b->total_thrust_n / input->total_mass_flow_kg_per_s / 9.80665, 1e-10));
    CHECK(near(b->main_throat_area_m2 * b->main_nozzle.throat.mass_flux_kg_per_m2_s, b->main_mass_flow_kg_per_s, 1e-10));
    for (unsigned int e = 0U; e < RP_CHO_ELEMENT_COUNT; ++e) {
        const double incoming = b->fuel_mass_flow_kg_per_s * input->fuel.elements_kmol_per_kg[e] +
            b->oxidizer_mass_flow_kg_per_s * input->oxidizer.elements_kmol_per_kg[e];
        double outgoing = 0.0;
        for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
            outgoing += (double)rp_cho_element_count(i, e) * (b->main_mass_flow_kg_per_s * b->main_nozzle.exit.gas.mole_fractions[i] /
                b->main_nozzle.exit.gas.molar_mass_kg_per_kmol + b->external_mass_flow_kg_per_s * b->turbine.outlet.mole_fractions[i] /
                b->turbine.outlet.molar_mass_kg_per_kmol);
        }
        CHECK(near(outgoing, incoming, 1e-8));
        CHECK(near(result->exit_element_relative_residual[e], (outgoing - incoming) / incoming, 1e-12));
    }
    if (input->staged_combustion) {
        CHECK(b->external_mass_flow_kg_per_s == 0.0 && b->branch_nozzle_active == 0 && b->branch_thrust_n == 0.0);
        CHECK(b->branch_oxidizer_mass_flow_kg_per_s == b->oxidizer_mass_flow_kg_per_s && b->main_oxidizer_mass_flow_kg_per_s == 0.0);
        CHECK(near(b->branch_fuel_mass_flow_kg_per_s, b->oxidizer_mass_flow_kg_per_s / input->preburner_oxidizer_fuel_ratio, 1e-12));
        CHECK(near(b->returned_mass_flow_kg_per_s, b->branch_mass_flow_kg_per_s, 1e-12));
        CHECK(b->turbine.outlet.pressure_pa >= input->chamber_pressure_pa + input->return_pressure_drop_pa);
        CHECK(near(result->main_inlet_h_j_per_kg, (b->inlet_enthalpy_rate_w - input->auxiliary_power_w - b->mechanical_loss_w) /
            input->total_mass_flow_kg_per_s, 0.02));
    } else {
        CHECK(b->returned_mass_flow_kg_per_s == 0.0 && b->external_mass_flow_kg_per_s == b->branch_mass_flow_kg_per_s);
        CHECK(near(b->branch_mass_flow_kg_per_s, (b->pump_power_w + input->auxiliary_power_w) / input->shaft_efficiency / work, 1e-10));
    }
}

static void test_adiabatic(void)
{
    RpEngineCycleInput open = adiabatic_benchmark(0), closed = adiabatic_benchmark(1), changed;
    RpEngineCycleResult gg, sc, other;
    CHECK(rp_engine_cycle_solve(&open, NULL, NULL, &gg, NULL) == RP_OK);
    check_adiabatic(&open, &gg);
    CHECK(rp_engine_cycle_solve(&closed, NULL, NULL, &sc, NULL) == RP_OK);
    check_adiabatic(&closed, &sc);
    changed = closed; changed.preburner_oxidizer_fuel_ratio = 25.0;
    CHECK(rp_engine_cycle_solve(&changed, NULL, NULL, &other, NULL) == RP_OK);
    check_adiabatic(&changed, &other);
    /* In an adiabatic closed cycle at the same load, changing the preburner
     * split cannot create additional chemical energy in the main chamber. */
    CHECK(fabs(other.preburner.gas.temperature_k - sc.preburner.gas.temperature_k) > 100.0);
    CHECK(near(other.main_inlet_h_j_per_kg, sc.main_inlet_h_j_per_kg, 0.02));
    CHECK(near(other.balance.engine_specific_impulse_s, sc.balance.engine_specific_impulse_s, 1e-4));
    changed = open; changed.branch_axial_projection = 0.0;
    CHECK(rp_engine_cycle_solve(&changed, NULL, NULL, &other, NULL) == RP_OK);
    CHECK(near(other.balance.total_thrust_n, gg.balance.main_thrust_n, 1e-7));
    CHECK(other.balance.external_mass_flow_kg_per_s == gg.balance.external_mass_flow_kg_per_s);
    for (int staged = 0; staged < 2; ++staged) {
        const RpEngineCycleInput base = staged ? closed : open;
        const RpEngineCycleResult reference = staged ? sc : gg;
        changed = base; changed.total_mass_flow_kg_per_s *= 3.0; changed.auxiliary_power_w *= 3.0;
        CHECK(rp_engine_cycle_solve(&changed, NULL, NULL, &other, NULL) == RP_OK);
        CHECK(near(other.balance.total_thrust_n, 3.0 * reference.balance.total_thrust_n, 0.001));
        CHECK(near(other.balance.engine_specific_impulse_s, reference.balance.engine_specific_impulse_s, 1e-6));
        changed = base; changed.auxiliary_power_w = 0.0;
        changed.fuel.pump.inlet_pressure_pa = changed.fuel.pump.outlet_pressure_pa;
        changed.oxidizer.pump.inlet_pressure_pa = changed.oxidizer.pump.outlet_pressure_pa;
        CHECK(rp_engine_cycle_solve(&changed, NULL, NULL, &other, NULL) == RP_OK);
        CHECK(other.balance.pump_power_w == 0.0 && other.balance.turbine_power_w == 0.0);
        if (staged) { CHECK(other.balance.turbine.outlet.pressure_pa == changed.preburner_pressure_pa); }
        else { CHECK(other.balance.branch_mass_flow_kg_per_s == 0.0 && other.balance.branch_nozzle_active == 0); }
    }
}

static void test_adiabatic_failures(void)
{
    const RpEngineCycleInput open = adiabatic_benchmark(0), closed = adiabatic_benchmark(1);
    RpEngineCycleInput input;
    RpEngineCycleResult result, sentinel;
    RpCombustionOptions combustion = rp_combustion_default_options();
    RpRootOptions root = rp_root_default_options();
    memset(&sentinel, 0x5a, sizeof(sentinel)); result = sentinel;
    CHECK(rp_engine_cycle_solve(NULL, NULL, NULL, &result, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_engine_cycle_solve(&open, NULL, NULL, NULL, NULL) == RP_INVALID_ARGUMENT);
#define REJECT(base, member, value, expected) \
    input = base; input.member = value; \
    CHECK(rp_engine_cycle_solve(&input, NULL, NULL, &result, NULL) == expected); \
    CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0)
    REJECT(open, total_mass_flow_kg_per_s, NAN, RP_INVALID_ARGUMENT);
    REJECT(open, overall_oxidizer_fuel_ratio, 0.0, RP_INVALID_ARGUMENT);
    REJECT(open, fuel.elements_kmol_per_kg[0], 1.0, RP_INVALID_ARGUMENT);
    REJECT(open, oxidizer.basis, RP_ENTHALPY_UNSPECIFIED, RP_INVALID_ARGUMENT);
    REJECT(open, fuel.pump.mass_flow_kg_per_s, 1.0, RP_INVALID_ARGUMENT);
    REJECT(open, fuel.pump.efficiency, 0.0, RP_INVALID_ARGUMENT);
    REJECT(open, oxidizer.pump.density_kg_per_m3, 0.0, RP_INVALID_ARGUMENT);
    REJECT(open, oxidizer.pump.outlet_pressure_pa, 11e6, RP_OUT_OF_DOMAIN);
    REJECT(open, shaft_efficiency, 1.1, RP_INVALID_ARGUMENT);
    REJECT(open, turbine_efficiency, -1.0, RP_INVALID_ARGUMENT);
    REJECT(open, ambient_pressure_pa, -1.0, RP_INVALID_ARGUMENT);
    REJECT(open, ambient_pressure_pa, 1e8, RP_OUT_OF_DOMAIN);
    REJECT(open, return_pressure_drop_pa, 1.0, RP_INVALID_ARGUMENT);
    REJECT(open, maximum_branch_fraction, 1e-5, RP_OUT_OF_DOMAIN);
    REJECT(open, auxiliary_power_w, 1e9, RP_OUT_OF_DOMAIN);
    REJECT(open, turbine_outlet_pressure_pa, 11e6, RP_OUT_OF_DOMAIN);
    REJECT(open, preburner_oxidizer_fuel_ratio, 0.1, RP_NUMERIC_ERROR);
    REJECT(closed, turbine_outlet_pressure_pa, 11e6, RP_INVALID_ARGUMENT);
    REJECT(closed, branch_axial_projection, 1.0, RP_INVALID_ARGUMENT);
    REJECT(closed, preburner_oxidizer_fuel_ratio, 3.0, RP_OUT_OF_DOMAIN);
    REJECT(closed, preburner_oxidizer_fuel_ratio, 3.6, RP_OUT_OF_DOMAIN);
    REJECT(closed, return_pressure_drop_pa, 12e6, RP_OUT_OF_DOMAIN);
    REJECT(closed, auxiliary_power_w, 1e8, RP_OUT_OF_DOMAIN);
    REJECT(closed, preburner_oxidizer_fuel_ratio, 200.0, RP_NOT_BRACKETED);
    REJECT(closed, maximum_branch_fraction, 0.5, RP_OUT_OF_DOMAIN);
#undef REJECT
    combustion.max_hp_iterations = 1U;
    CHECK(rp_engine_cycle_solve(&open, &combustion, NULL, &result, NULL) == RP_NO_CONVERGENCE);
    root.max_iterations = 1U;
    CHECK(rp_engine_cycle_solve(&closed, NULL, &root, &result, NULL) == RP_NO_CONVERGENCE);
    CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
}

int main(void)
{
    test_pump(); test_turbine(); test_cycle(); test_inlet_assumptions(); test_cycle_failures(); test_study();
    test_adiabatic(); test_adiabatic_failures();
    (void)printf("cycle: %u checks, %u failures\n", checks, failures);
    return failures == 0U ? 0 : 1;
}
