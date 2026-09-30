#include "rocketperf/nozzle.h"
#include "rocketperf/version.h"
#include "rocketperf/numeric.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

static unsigned int checks = 0U;
static unsigned int failures = 0U;

static void check(int condition, const char *label, int line)
{
    ++checks;
    if (!condition) {
        ++failures;
        (void)fprintf(stderr, "FAIL line %d: %s\n", line, label);
    }
}

#define CHECK(condition) check((condition), #condition, __LINE__)

static int near(double actual, double expected, double relative_tolerance)
{
    return rp_isfinite(actual) && fabs(actual - expected) <= relative_tolerance * fmax(1.0, fabs(expected));
}

static RpNozzleInput reference_input(void)
{
    const RpNozzleInput input = {1.4, 287.0, 300.0, 1e6, 1.6875, 0.001, 0.0};
    return input;
}

static double square_minus_two(double x, const void *context)
{
    (void)context;
    return x * x - 2.0;
}

static double linear(double x, const void *context)
{
    const double *target = context;
    return x - *target;
}

static double not_finite(double x, const void *context)
{
    (void)x;
    (void)context;
    return NAN;
}

static void test_root(void)
{
    RpRootResult result = {77.0, 88.0, 99U};
    RpError error = {0};
    RpRootOptions options = rp_root_default_options();
    const double endpoint = 2.0;
    CHECK(rp_isfinite(1e300));
    CHECK(!rp_isfinite(NAN));
    CHECK(!rp_isfinite(INFINITY));
    CHECK(rp_root_bisect(square_minus_two, NULL, 1.0, 2.0, NULL, &result, &error) == RP_OK);
    CHECK(near(result.x, 1.4142135623730951, 1e-11));
    CHECK(error.code == RP_OK && error.message[0] == '\0');
    CHECK(rp_root_bisect(linear, &endpoint, 2.0, 4.0, NULL, &result, &error) == RP_OK);
    CHECK(result.x == 2.0 && result.iterations == 0U);
    result.x = 77.0;
    CHECK(rp_root_bisect(square_minus_two, NULL, 2.0, 3.0, NULL, &result, &error) == RP_NOT_BRACKETED);
    CHECK(result.x == 77.0 && error.code == RP_NOT_BRACKETED);
    CHECK(rp_root_bisect(not_finite, NULL, 1.0, 2.0, NULL, &result, NULL) == RP_NUMERIC_ERROR);
    CHECK(rp_root_bisect(NULL, NULL, 1.0, 2.0, NULL, &result, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_root_bisect(square_minus_two, NULL, NAN, 2.0, NULL, &result, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_root_bisect(square_minus_two, NULL, 2.0, 1.0, NULL, &result, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_root_bisect(square_minus_two, NULL, 1.0, 2.0, NULL, NULL, NULL) == RP_INVALID_ARGUMENT);
    options.max_iterations = 1U;
    CHECK(rp_root_bisect(square_minus_two, NULL, 1.0, 2.0, &options, &result, &error) == RP_NO_CONVERGENCE);
    CHECK(result.x == 77.0);
    options.max_iterations = 0U;
    CHECK(rp_root_bisect(square_minus_two, NULL, 1.0, 2.0, &options, &result, &error) == RP_INVALID_ARGUMENT);
    options = rp_root_default_options();
    options.x_absolute_tolerance = INFINITY;
    CHECK(rp_root_bisect(square_minus_two, NULL, 1.0, 2.0, &options, &result, &error) == RP_INVALID_ARGUMENT);
    CHECK(strcmp(rp_status_name(RP_NO_CONVERGENCE), "no_convergence") == 0);
}

static void test_analytic_reference(void)
{
    RpNozzleInput input = reference_input();
    RpNozzleResult result = {0};
    RpError error = {0};
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &result, &error) == RP_OK);
    CHECK(near(result.exit_mach, 2.0, 1e-10));
    CHECK(near(result.exit_temperature_k, 166.66666666666667, 1e-10));
    CHECK(near(result.exit_pressure_pa, 127804.52546295094, 1e-10));
    CHECK(near(result.exit_velocity_m_s, 517.5583702991061, 1e-10));
    CHECK(near(result.characteristic_velocity_m_s, 428.53006428954317, 1e-10));
    CHECK(near(result.mass_flow_kg_s, 2.3335585606062264, 1e-10));
    CHECK(near(result.thrust_n, 1423.4229023436161, 1e-10));
    CHECK(near(result.thrust_coefficient, 1.4234229023436161, 1e-10));
    CHECK(near(result.specific_impulse_s, 62.200599374151, 1e-10));
    CHECK(result.relative_area_residual < 1e-10);
    input.area_ratio = 343.0 / 81.0; /* gamma=7/5, M=3 gives this exact ratio. */
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &result, &error) == RP_OK);
    CHECK(near(result.exit_mach, 3.0, 1e-10));
    input.gamma = 5.0 / 3.0;
    input.area_ratio = 49.0 / 32.0; /* gamma=5/3, M=2. */
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &result, &error) == RP_OK);
    CHECK(near(result.exit_mach, 2.0, 1e-10));
    input.area_ratio = 1.0;
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &result, &error) == RP_OK);
    CHECK(result.exit_mach == 1.0);
}

static void test_scaling_and_balance(void)
{
    RpNozzleInput input = reference_input();
    RpNozzleResult vacuum = {0};
    RpNozzleResult ambient = {0};
    RpNozzleResult scaled = {0};
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &vacuum, NULL) == RP_OK);
    input.ambient_pressure_pa = 1e5;
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &ambient, NULL) == RP_OK);
    CHECK(near(vacuum.thrust_n - ambient.thrust_n, 168.75, 1e-10));
    CHECK(vacuum.mass_flow_kg_s == ambient.mass_flow_kg_s);
    input.throat_area_m2 *= 2.0;
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &scaled, NULL) == RP_OK);
    CHECK(near(scaled.thrust_n, 2.0 * ambient.thrust_n, 1e-10));
    CHECK(near(scaled.mass_flow_kg_s, 2.0 * ambient.mass_flow_kg_s, 1e-10));
    CHECK(near(scaled.specific_impulse_s, ambient.specific_impulse_s, 1e-10));
    CHECK(near(scaled.thrust_coefficient, ambient.thrust_coefficient, 1e-10));
    input = reference_input();
    input.ambient_pressure_pa = vacuum.exit_pressure_pa;
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &ambient, NULL) == RP_OK);
    CHECK(near(ambient.thrust_n, ambient.mass_flow_kg_s * ambient.exit_velocity_m_s, 1e-10));

    {
        const double gammas[] = {1.01, 1.1, 1.2, 1.4, 5.0 / 3.0, 2.0};
        const double ratios[] = {1.0, 1.001, 1.6875, 4.0, 10.0, 100.0, 1e4};
        for (size_t i = 0U; i < sizeof(gammas) / sizeof(gammas[0]); ++i) {
            for (size_t j = 0U; j < sizeof(ratios) / sizeof(ratios[0]); ++j) {
                double exit_mass_flow;
                double cp;
                input = reference_input();
                input.gamma = gammas[i];
                input.area_ratio = ratios[j];
                CHECK(rp_nozzle_solve_ideal(&input, NULL, &scaled, NULL) == RP_OK);
                exit_mass_flow = scaled.exit_pressure_pa / (input.gas_constant_j_kg_k * scaled.exit_temperature_k) *
                                 scaled.exit_velocity_m_s * scaled.exit_area_m2;
                cp = input.gamma * input.gas_constant_j_kg_k / (input.gamma - 1.0);
                CHECK(near(exit_mass_flow, scaled.mass_flow_kg_s, 1e-8));
                CHECK(near(cp * scaled.exit_temperature_k + 0.5 * scaled.exit_velocity_m_s * scaled.exit_velocity_m_s,
                           cp * input.stagnation_temperature_k, 1e-10));
            }
        }
    }
}

static void test_invalid_inputs(void)
{
    RpNozzleInput input = reference_input();
    RpNozzleResult result = {0};
    RpRootOptions options = rp_root_default_options();
    result.thrust_n = 123.0;
    CHECK(rp_nozzle_solve_ideal(NULL, NULL, &result, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_nozzle_solve_ideal(&input, NULL, NULL, NULL) == RP_INVALID_ARGUMENT);
    input.gamma = NAN;
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    CHECK(result.thrust_n == 123.0);
    input = reference_input(); input.gamma = 1.0;
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = reference_input(); input.gas_constant_j_kg_k = 0.0;
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = reference_input(); input.stagnation_temperature_k = -1.0;
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = reference_input(); input.stagnation_pressure_pa = INFINITY;
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = reference_input(); input.area_ratio = 0.5;
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = reference_input(); input.area_ratio = 1e5;
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = reference_input(); input.throat_area_m2 = 0.0;
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = reference_input(); input.ambient_pressure_pa = -1.0;
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = reference_input(); input.ambient_pressure_pa = 2e5;
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    input = reference_input(); input.area_ratio = 2.0; options.max_iterations = 1U;
    CHECK(rp_nozzle_solve_ideal(&input, &options, &result, NULL) == RP_NO_CONVERGENCE);
    CHECK(result.thrust_n == 123.0);
    input = reference_input(); input.stagnation_temperature_k = 1e308;
    CHECK(rp_nozzle_solve_ideal(&input, NULL, &result, NULL) == RP_NUMERIC_ERROR);
}

int main(void)
{
    test_root();
    test_analytic_reference();
    test_scaling_and_balance();
    test_invalid_inputs();
    (void)printf("core: %u checks, %u failures\n", checks, failures);
    return failures == 0U ? 0 : 1;
}
