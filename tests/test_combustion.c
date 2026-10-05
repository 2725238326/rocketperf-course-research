#include "rocketperf/combustion.h"
#include "rocketperf/frozen_nozzle.h"
#include "rocketperf/numeric.h"

#include <math.h>
#include <float.h>
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
static int near(double actual, double expected, double absolute)
{
    return rp_isfinite(actual) && fabs(actual - expected) <= absolute;
}
static RpCh4O2Feed reference_feed(void)
{
    const RpCh4O2Feed feed = {1e7, 3.4, 298.15, 298.15, RP_FEED_GAS};
    return feed;
}
static RpFrozenNozzleInput nozzle_input(const RpGasMixture *gas, double area)
{
    RpFrozenNozzleInput input = {0};
    input.chamber_temperature_k = gas->temperature_k;
    input.chamber_pressure_pa = gas->pressure_pa;
    memcpy(input.mole_fractions, gas->mole_fractions, sizeof(input.mole_fractions));
    input.area_ratio = area;
    return input;
}
static void check_elements(const RpCombustionResult *result, const RpCh4O2Feed *feed)
{
    double atoms[3] = {0};
    double mass = 0.0;
    double sum = 0.0;
    const double fuel_mw = rp_thermo_find_species("CH4")->molar_mass_kg_per_kmol;
    const double oxygen_mw = rp_thermo_find_species("O2")->molar_mass_kg_per_kmol;
    for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
        const double y = result->gas.mole_fractions[i];
        CHECK(y > 0.0 && y <= 1.0);
        sum += y;
        mass += y * rp_thermo_find_species(rp_cho_species_id(i))->molar_mass_kg_per_kmol;
        for (unsigned int e = 0U; e < 3U; ++e) { atoms[e] += y * (double)rp_cho_element_count(i, e); }
    }
    CHECK(near(sum, 1.0, 1e-14));
    CHECK(near(atoms[1] / atoms[0], 4.0, 2e-8));
    CHECK(near(atoms[2] / atoms[0], 2.0 * feed->oxidizer_fuel_mass_ratio * fuel_mw / oxygen_mw, 2e-8));
    CHECK(near(atoms[0] / mass, 1.0 / (fuel_mw * (1.0 + feed->oxidizer_fuel_mass_ratio)), 1e-10));
    for (unsigned int e = 0U; e < 3U; ++e) { CHECK(fabs(result->element_relative_residual[e]) < 2e-10); }
    CHECK(result->equilibrium_residual <= 1e-10);
    {
        /* Six independent reaction directions span the nine-species CHO nullspace.
         * Recompute chemical potentials from the public result, not solver lambdas. */
        const double reactions[6][9] = {
            {-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0, 0.0, 0.0},
            {0.0, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0, 0.0},
            {1.0, 0.5, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0},
            {0.0, 0.5, 0.0, 1.0, -1.0, 0.0, 0.0, 0.0, 0.0},
            {3.0, 0.0, -1.0, 1.0, 0.0, -1.0, 0.0, 0.0, 0.0},
            {0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, -1.0}
        };
        double potentials[9];
        for (unsigned int i = 0U; i < 9U; ++i) {
            const RpNasa9Species *species = rp_thermo_find_species(rp_cho_species_id(i));
            RpThermoState state;
            CHECK(rp_nasa9_evaluate(species, result->gas.temperature_k, &state, NULL) == RP_OK);
            potentials[i] = species->molar_mass_kg_per_kmol *
                (state.h_j_per_kg / result->gas.temperature_k - state.s_j_per_kg_k) / RP_UNIVERSAL_GAS_CONSTANT_J_KMOL_K +
                log(result->gas.mole_fractions[i]) + log(feed->pressure_pa / rp_thermo_reference_pressure_pa());
        }
        for (unsigned int r = 0U; r < 6U; ++r) {
            double affinity = 0.0;
            for (unsigned int e = 0U; e < 3U; ++e) {
                double balance = 0.0;
                for (unsigned int i = 0U; i < 9U; ++i) { balance += reactions[r][i] * (double)rp_cho_element_count(i, e); }
                CHECK(near(balance, 0.0, 1e-14));
            }
            for (unsigned int i = 0U; i < 9U; ++i) { affinity += reactions[r][i] * potentials[i]; }
            CHECK(fabs(affinity) < 1e-8);
        }
    }
}
static void test_tp_hp_reference(void)
{
    const RpCh4O2Feed feed = reference_feed();
    const double tp_y[9] = {0.060950, 0.001873, 0.589564, 0.142890, 0.186741, 0.0, 0.003904, 0.0004898, 0.013587};
    const double hp_y[9] = {0.084502, 0.025567, 0.473455, 0.183464, 0.120622, 0.0, 0.025013, 0.011962, 0.075416};
    RpCombustionResult result;
    RpError error;
    CHECK(rp_ch4_o2_equilibrium_tp(&feed, 3000.0, NULL, &result, &error) == RP_OK);
    if (error.code != RP_OK) { (void)fprintf(stderr, "%s\n", error.message); return; }
    check_elements(&result, &feed);
    CHECK(near(result.gas.h_j_per_kg, -4562051.0, 3.0));
    CHECK(near(result.gas.s_j_per_kg_k, 11142.4, 0.1));
    CHECK(near(result.gas.molar_mass_kg_per_kmol, 23.26756, 2e-5));
    for (unsigned int i = 0U; i < 9U; ++i) { CHECK(near(result.gas.mole_fractions[i], tp_y[i], 2e-6)); }
    CHECK(rp_ch4_o2_equilibrium_hp(&feed, NULL, &result, &error) == RP_OK);
    if (error.code != RP_OK) { (void)fprintf(stderr, "%s\n", error.message); return; }
    check_elements(&result, &feed);
    CHECK(near(result.gas.temperature_k, 3673.61, 0.02));
    CHECK(near(result.gas.h_j_per_kg, -1056854.0, 3.0));
    CHECK(near(result.gas.molar_mass_kg_per_kmol, 21.46443, 2e-5));
    CHECK(fabs(result.enthalpy_residual_j_per_kg) <= 0.01);
    for (unsigned int i = 0U; i < 9U; ++i) { CHECK(near(result.gas.mole_fractions[i], hp_y[i], 2e-6)); }
    (void)printf("HP: T=%.9f K, h_residual=%.9g J/kg\n", result.gas.temperature_k, result.enthalpy_residual_j_per_kg);
    for (unsigned int i = 0U; i < 2U; ++i) {
        const double areas[2] = {10.0, 40.0};
        const double temperatures[2] = {1691.56, 1173.07};
        const double pressures[2] = {119870.0, 18730.0};
        const double vacuum[2] = {3192.26, 3435.41};
        RpFrozenNozzleInput input = nozzle_input(&result.gas, areas[i]);
        RpFrozenNozzleResult nozzle;
        CHECK(rp_nozzle_solve_frozen(&input, NULL, &nozzle, &error) == RP_OK);
        if (error.code != RP_OK) { (void)fprintf(stderr, "%s\n", error.message); continue; }
        CHECK(near(nozzle.throat.gas.temperature_k, 3339.54, 0.03));
        CHECK(near(nozzle.throat.gas.pressure_pa, 5641760.0, 30.0));
        CHECK(near(nozzle.cstar_m_per_s, 1839.39, 0.03));
        CHECK(near(nozzle.exit.gas.temperature_k, temperatures[i], 0.03));
        CHECK(near(nozzle.exit.gas.pressure_pa, pressures[i], 10.0));
        CHECK(near(nozzle.vacuum_effective_velocity_m_per_s, vacuum[i], 0.03));
        CHECK(fabs(nozzle.continuity_relative_residual) < 1e-8);
        CHECK(fabs(nozzle.sonic_relative_residual) < 1e-8);
        CHECK(fabs(nozzle.exit.energy_residual_j_per_kg) < 1e-5);
        CHECK(fabs(nozzle.exit.entropy_residual_j_per_kg_k) < 1e-7);
        CHECK(memcmp(nozzle.chamber.mole_fractions, nozzle.exit.gas.mole_fractions, sizeof(input.mole_fractions)) == 0);
        CHECK(nozzle.exit.gas.cp_frozen_j_per_kg_k < nozzle.chamber.cp_frozen_j_per_kg_k);
        (void)printf("Frozen A=%.0f: T=%.9f K, p=%.9f Pa, cstar=%.9f, Ivac=%.9f m/s\n",
                     areas[i], nozzle.exit.gas.temperature_k, nozzle.exit.gas.pressure_pa,
                     nozzle.cstar_m_per_s, nozzle.vacuum_effective_velocity_m_per_s);
        input.ambient_pressure_pa = nozzle.exit.gas.pressure_pa;
        CHECK(rp_nozzle_solve_frozen(&input, NULL, &nozzle, &error) == RP_OK);
        CHECK(near(nozzle.effective_velocity_m_per_s, nozzle.exit.velocity_m_per_s, 1e-8));
    }
}
static void test_sweep_and_relations(void)
{
    static const double pressures[] = {1e5, 1e6, 1e7};
    static const double ratios[] = {2.0, 3.4, 5.0};
    static const double temperatures[] = {1000.0, 2000.0, 4000.0, 6000.0};
    for (unsigned int p = 0U; p < 3U; ++p) {
        for (unsigned int r = 0U; r < 3U; ++r) {
            RpCh4O2Feed feed = reference_feed();
            feed.pressure_pa = pressures[p]; feed.oxidizer_fuel_mass_ratio = ratios[r];
            for (unsigned int t = 0U; t < 4U; ++t) {
                RpCombustionResult result;
                RpStatus status = rp_ch4_o2_equilibrium_tp(&feed, temperatures[t], NULL, &result, NULL);
                CHECK(status == RP_OK);
                if (status == RP_OK) { check_elements(&result, &feed); }
            }
            {
                RpCombustionResult hp;
                const RpStatus status = rp_ch4_o2_equilibrium_hp(&feed, NULL, &hp, NULL);
                CHECK(status == RP_OK);
                if (status == RP_OK) {
                    check_elements(&hp, &feed);
                    CHECK(fabs(hp.enthalpy_residual_j_per_kg) <= 0.01);
                }
            }
        }
    }
    {
        const double y[9] = {0.1, 0.1, 0.4, 0.2, 0.2, 0.0, 0.0, 0.0, 0.0};
        RpGasMixture lower, center, upper;
        CHECK(rp_cho_mixture_evaluate(y, 1999.98, 1e7, &lower, NULL) == RP_OK);
        CHECK(rp_cho_mixture_evaluate(y, 2000.0, 1e7, &center, NULL) == RP_OK);
        CHECK(rp_cho_mixture_evaluate(y, 2000.02, 1e7, &upper, NULL) == RP_OK);
        CHECK(near((upper.h_j_per_kg - lower.h_j_per_kg) / 0.04, center.cp_frozen_j_per_kg_k, 1e-4));
        CHECK(near((upper.s_j_per_kg_k - lower.s_j_per_kg_k) / 0.04, center.cp_frozen_j_per_kg_k / 2000.0, 1e-6));
        CHECK(rp_cho_mixture_evaluate(y, 2000.0, 1e6, &lower, NULL) == RP_OK);
        CHECK(near(lower.h_j_per_kg, center.h_j_per_kg, 1e-8));
        CHECK(near(lower.s_j_per_kg_k - center.s_j_per_kg_k, center.gas_constant_j_per_kg_k * log(10.0), 1e-8));
    }
}
static void test_failures(void)
{
    RpCh4O2Feed feed = reference_feed();
    RpCombustionResult sentinel;
    RpCombustionResult result;
    RpCombustionOptions options = rp_combustion_default_options();
    memset(&sentinel, 0x5a, sizeof(sentinel)); result = sentinel;
    CHECK(rp_ch4_o2_equilibrium_tp(NULL, 3000.0, NULL, &result, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_ch4_o2_equilibrium_tp(&feed, NAN, NULL, &result, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_ch4_o2_equilibrium_tp(&feed, 999.0, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    CHECK(rp_ch4_o2_equilibrium_tp(&feed, 6000.1, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
    feed.phase = RP_FEED_LIQUID;
    CHECK(rp_ch4_o2_equilibrium_hp(&feed, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    feed = reference_feed(); feed.oxidizer_fuel_mass_ratio = -1.0;
    CHECK(rp_ch4_o2_equilibrium_hp(&feed, NULL, &result, NULL) == RP_INVALID_ARGUMENT);
    feed = reference_feed(); feed.fuel_temperature_k = 100.0;
    CHECK(rp_ch4_o2_equilibrium_hp(&feed, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    feed = reference_feed(); options.max_equilibrium_iterations = 1U;
    CHECK(rp_ch4_o2_equilibrium_hp(&feed, &options, &result, NULL) == RP_NO_CONVERGENCE);
    options = rp_combustion_default_options(); options.max_hp_iterations = 1U;
    CHECK(rp_ch4_o2_equilibrium_hp(&feed, &options, &result, NULL) == RP_NO_CONVERGENCE);
    options = rp_combustion_default_options(); options.hp_lower_temperature_k = 5000.0;
    CHECK(rp_ch4_o2_equilibrium_hp(&feed, &options, &result, NULL) == RP_NOT_BRACKETED);
    options.equilibrium_tolerance = NAN;
    CHECK(rp_ch4_o2_equilibrium_tp(&feed, 3000.0, &options, &result, NULL) == RP_INVALID_ARGUMENT);
    CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
    CHECK(rp_ch4_o2_equilibrium_hp(&feed, NULL, &result, NULL) == RP_OK);
    {
        RpFrozenNozzleInput input = nozzle_input(&result.gas, 40.0);
        RpFrozenNozzleResult nozzle_sentinel;
        RpFrozenNozzleResult nozzle;
        RpRootOptions roots = rp_root_default_options();
        memset(&nozzle_sentinel, 0x5a, sizeof(nozzle_sentinel)); nozzle = nozzle_sentinel;
        input.ambient_pressure_pa = 1e5;
        CHECK(rp_nozzle_solve_frozen(&input, NULL, &nozzle, NULL) == RP_OUT_OF_DOMAIN);
        input.ambient_pressure_pa = 0.0; input.mole_fractions[0] = -0.1;
        CHECK(rp_nozzle_solve_frozen(&input, NULL, &nozzle, NULL) == RP_INVALID_ARGUMENT);
        input = nozzle_input(&result.gas, 40.0); input.chamber_temperature_k = 199.0;
        CHECK(rp_nozzle_solve_frozen(&input, NULL, &nozzle, NULL) == RP_OUT_OF_DOMAIN);
        input = nozzle_input(&result.gas, 40.0); roots.max_iterations = 1U;
        CHECK(rp_nozzle_solve_frozen(&input, &roots, &nozzle, NULL) == RP_NO_CONVERGENCE);
        input.area_ratio = NAN;
        CHECK(rp_nozzle_solve_frozen(&input, NULL, &nozzle, NULL) == RP_INVALID_ARGUMENT);
        CHECK(memcmp(&nozzle, &nozzle_sentinel, sizeof(nozzle)) == 0);
        input = nozzle_input(&result.gas, 1.0);
        CHECK(rp_nozzle_solve_frozen(&input, NULL, &nozzle, NULL) == RP_OK);
        CHECK(near(nozzle.exit.mach, 1.0, 1e-8));
        CHECK(rp_nozzle_solve_frozen(NULL, NULL, &nozzle, NULL) == RP_INVALID_ARGUMENT);
        CHECK(rp_nozzle_solve_frozen(&input, NULL, NULL, NULL) == RP_INVALID_ARGUMENT);
    }
}
static void test_mixture_failure_contract(void)
{
    RpGasMixture sentinel;
    RpGasMixture result;
    double y[9] = {0.1, 0.1, 0.4, 0.2, 0.2, 0.0, 0.0, 0.0, 0.0};
    double enthalpy = 123.0;
    RpCh4O2Feed feed = reference_feed();
    memset(&sentinel, 0x5a, sizeof(sentinel)); result = sentinel;
    CHECK(rp_cho_mixture_evaluate(NULL, 3000.0, 1e7, &result, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_cho_mixture_evaluate(y, 3000.0, NAN, &result, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_cho_mixture_evaluate(y, INFINITY, 1e7, &result, NULL) == RP_INVALID_ARGUMENT);
    y[0] = NAN;
    CHECK(rp_cho_mixture_evaluate(y, 3000.0, 1e7, &result, NULL) == RP_INVALID_ARGUMENT);
    y[0] = 0.2;
    CHECK(rp_cho_mixture_evaluate(y, 3000.0, 1e7, &result, NULL) == RP_INVALID_ARGUMENT);
    y[0] = 0.1;
    CHECK(rp_cho_mixture_evaluate(y, 199.0, 1e7, &result, NULL) == RP_OUT_OF_DOMAIN);
    CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
    feed.phase = RP_FEED_LIQUID;
    CHECK(rp_ch4_o2_feed_enthalpy(&feed, &enthalpy, NULL) == RP_OUT_OF_DOMAIN);
    CHECK(enthalpy == 123.0);
    CHECK(rp_cho_species_id(9U) == NULL);
    CHECK(rp_cho_element_count(9U, 0U) == 0U);
}
static void test_constant_cp_limit(void)
{
    /* Pinned atomic H has exactly cp/R=2.5 below 1000 K.
     * Use a closed Mach-2 solution, independent of either nozzle root solver. */
    const double gamma = 5.0 / 3.0;
    const double mach = 2.0;
    const double ratio = 1.0 + 0.5 * (gamma - 1.0) * mach * mach;
    const double area = pow(2.0 * ratio / (gamma + 1.0), (gamma + 1.0) / (2.0 * (gamma - 1.0))) / mach;
    const double gas_constant = RP_UNIVERSAL_GAS_CONSTANT_J_KMOL_K / rp_thermo_find_species("H")->molar_mass_kg_per_kmol;
    RpFrozenNozzleInput input = {0};
    RpFrozenNozzleResult result;
    input.chamber_temperature_k = 700.0;
    input.chamber_pressure_pa = 1e6;
    input.mole_fractions[6] = 1.0;
    input.area_ratio = area;
    CHECK(rp_nozzle_solve_frozen(&input, NULL, &result, NULL) == RP_OK);
    CHECK(near(result.exit.mach, mach, 1e-8));
    CHECK(near(result.exit.gas.temperature_k, 700.0 / ratio, 1e-7));
    CHECK(near(result.exit.gas.pressure_pa, 1e6 * pow(ratio, -gamma / (gamma - 1.0)), 1e-3));
    CHECK(near(result.exit.velocity_m_per_s, mach * sqrt(gamma * gas_constant * 700.0 / ratio), 1e-5));
    CHECK(near(result.throat.gas.temperature_k, 700.0 * 2.0 / (gamma + 1.0), 1e-7));
    CHECK(near(result.cstar_m_per_s, sqrt(gas_constant * 700.0 / gamma) * pow((gamma + 1.0) / 2.0, (gamma + 1.0) / (2.0 * (gamma - 1.0))), 1e-5));
    input.area_ratio = 1e4;
    CHECK(rp_nozzle_solve_frozen(&input, NULL, &result, NULL) == RP_NOT_BRACKETED);
}
static void test_fixed_geometry(void)
{
    const double gamma = 5.0 / 3.0;
    const double rg = RP_UNIVERSAL_GAS_CONSTANT_J_KMOL_K / rp_thermo_find_species("H")->molar_mass_kg_per_kmol;
    const double cstar = sqrt(rg * 700.0 / gamma) * pow((gamma + 1.0) / 2.0, (gamma + 1.0) / (2.0 * (gamma - 1.0)));
    RpFrozenNozzleInput input = {0};
    RpFrozenNozzleFixedResult result, doubled, sentinel;
    RpRootOptions roots = rp_root_default_options();
    const double bad_areas[] = {0.0, -1.0, NAN, INFINITY};
    input.chamber_temperature_k = 700.0; input.chamber_pressure_pa = 1e6;
    input.mole_fractions[6] = 1.0; input.area_ratio = 1.2;
    CHECK(rp_nozzle_solve_frozen_fixed_area(&input, 0.01, NULL, &result, NULL) == RP_OK);
    CHECK(near(result.mass_flow_kg_per_s, 1e6 * 0.01 / cstar, 1e-9));
    CHECK(near(result.exit_area_m2, 0.012, 1e-15));
    CHECK(near(result.thrust_n, result.mass_flow_kg_per_s * result.nozzle.exit.velocity_m_per_s +
               result.nozzle.exit.gas.pressure_pa * result.exit_area_m2, 1e-7));
    CHECK(near(result.specific_impulse_s, result.thrust_n / (result.mass_flow_kg_per_s * 9.80665), 1e-10));
    CHECK(rp_nozzle_solve_frozen_fixed_area(&input, 0.02, NULL, &doubled, NULL) == RP_OK);
    CHECK(near(doubled.mass_flow_kg_per_s, 2.0 * result.mass_flow_kg_per_s, 1e-10));
    CHECK(near(doubled.thrust_n, 2.0 * result.thrust_n, 1e-7));
    CHECK(near(doubled.specific_impulse_s, result.specific_impulse_s, 1e-12));
    input.chamber_pressure_pa = 2e6;
    CHECK(rp_nozzle_solve_frozen_fixed_area(&input, 0.01, NULL, &doubled, NULL) == RP_OK);
    CHECK(near(doubled.mass_flow_kg_per_s, 2.0 * result.mass_flow_kg_per_s, 1e-9));
    input.chamber_pressure_pa = 1e6; input.ambient_pressure_pa = 10000.0;
    CHECK(rp_nozzle_solve_frozen_fixed_area(&input, 0.01, NULL, &doubled, NULL) == RP_OK);
    CHECK(near(doubled.mass_flow_kg_per_s, result.mass_flow_kg_per_s, 1e-10));
    CHECK(near(result.thrust_n - doubled.thrust_n, 10000.0 * result.exit_area_m2, 1e-7));
    memset(&sentinel, 0x5a, sizeof(sentinel)); result = sentinel;
    for (size_t i = 0U; i < sizeof(bad_areas) / sizeof(bad_areas[0]); ++i) {
        CHECK(rp_nozzle_solve_frozen_fixed_area(&input, bad_areas[i], NULL, &result, NULL) == RP_INVALID_ARGUMENT);
        CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
    }
    CHECK(rp_nozzle_solve_frozen_fixed_area(NULL, 0.01, NULL, &result, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_nozzle_solve_frozen_fixed_area(&input, 0.01, NULL, NULL, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_nozzle_solve_frozen_fixed_area(&input, DBL_MAX, NULL, &result, NULL) == RP_NUMERIC_ERROR);
    CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
    input.chamber_pressure_pa = 100.0; input.ambient_pressure_pa = 0.0;
    CHECK(rp_nozzle_solve_frozen_fixed_area(&input, DBL_TRUE_MIN, NULL, &result, NULL) == RP_NUMERIC_ERROR);
    CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
    input.chamber_pressure_pa = 1e6;
    input.ambient_pressure_pa = 1e6;
    CHECK(rp_nozzle_solve_frozen_fixed_area(&input, 0.01, NULL, &result, NULL) == RP_OUT_OF_DOMAIN);
    CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
    input.ambient_pressure_pa = 0.0; roots.max_iterations = 1U;
    CHECK(rp_nozzle_solve_frozen_fixed_area(&input, 0.01, &roots, &result, NULL) == RP_NO_CONVERGENCE);
    CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
}
static RpCh4O2EnthalpyFeed enthalpy_feed(const RpCh4O2Feed *feed)
{
    RpThermoState fuel, oxidizer;
    RpCh4O2EnthalpyFeed inlet = {0};
    CHECK(rp_nasa9_evaluate(rp_thermo_find_species("CH4"), feed->fuel_temperature_k, &fuel, NULL) == RP_OK);
    CHECK(rp_nasa9_evaluate(rp_thermo_find_species("O2"), feed->oxidizer_temperature_k, &oxidizer, NULL) == RP_OK);
    inlet.pressure_pa = feed->pressure_pa;
    inlet.oxidizer_fuel_mass_ratio = feed->oxidizer_fuel_mass_ratio;
    inlet.fuel_h_j_per_kg = fuel.h_j_per_kg;
    inlet.oxidizer_h_j_per_kg = oxidizer.h_j_per_kg;
    inlet.phase = RP_FEED_GAS;
    inlet.basis = RP_ENTHALPY_NASA9_CEA_V334;
    return inlet;
}
static void test_explicit_enthalpy(void)
{
    const double temperatures[][2] = {{298.15,298.15},{200.0,200.0},{450.0,900.0},{1000.0,500.0}};
    for (unsigned int i = 0U; i < 4U; ++i) {
        RpCh4O2Feed feed = reference_feed();
        RpCh4O2EnthalpyFeed inlet;
        RpCombustionResult old, result;
        double old_h, new_h;
        feed.fuel_temperature_k = temperatures[i][0]; feed.oxidizer_temperature_k = temperatures[i][1];
        inlet = enthalpy_feed(&feed);
        CHECK(rp_ch4_o2_feed_enthalpy(&feed, &old_h, NULL) == RP_OK);
        CHECK(rp_ch4_o2_inlet_enthalpy(&inlet, &new_h, NULL) == RP_OK);
        CHECK(old_h == new_h);
        CHECK(near(new_h, (inlet.fuel_h_j_per_kg + 3.4 * inlet.oxidizer_h_j_per_kg) / 4.4, 1e-8));
        CHECK(rp_ch4_o2_equilibrium_hp(&feed, NULL, &old, NULL) == RP_OK);
        CHECK(rp_ch4_o2_equilibrium_hp_enthalpy(&inlet, NULL, &result, NULL) == RP_OK);
        CHECK(old.gas.temperature_k == result.gas.temperature_k);
        CHECK(old.gas.h_j_per_kg == result.gas.h_j_per_kg);
        CHECK(old.enthalpy_residual_j_per_kg == result.enthalpy_residual_j_per_kg);
        CHECK(old.hp_iterations == result.hp_iterations);
        CHECK(memcmp(old.gas.mole_fractions, result.gas.mole_fractions, sizeof(old.gas.mole_fractions)) == 0);
        CHECK(fabs(result.enthalpy_residual_j_per_kg) <= 0.01);
        check_elements(&result, &feed);
        if (i == 0U) {
            RpCombustionOptions policy = rp_combustion_default_options();
            RpFrozenNozzleInput input = nozzle_input(&result.gas, 10.0);
            RpFrozenNozzleFixedResult fixed;
            const double root = result.gas.temperature_k;
            CHECK(near(inlet.fuel_h_j_per_kg, -4650159.6379939355, 1e-7));
            CHECK(near(inlet.oxidizer_h_j_per_kg, -0.00040024263231910033, 1e-7));
            CHECK(rp_nozzle_solve_frozen_fixed_area(&input, 0.01, NULL, &fixed, NULL) == RP_OK);
            CHECK(near(fixed.mass_flow_kg_per_s, input.chamber_pressure_pa * 0.01 / fixed.nozzle.cstar_m_per_s, 1e-9));
            CHECK(near(fixed.thrust_n, fixed.mass_flow_kg_per_s * fixed.nozzle.exit.velocity_m_per_s +
                       fixed.nozzle.exit.gas.pressure_pa * fixed.exit_area_m2, 1e-7));
            CHECK(fabs(fixed.nozzle.exit.energy_residual_j_per_kg) < 1e-5);
            policy.hp_lower_temperature_k = root;
            CHECK(rp_ch4_o2_equilibrium_hp_enthalpy(&inlet, &policy, &result, NULL) == RP_OK);
            CHECK(result.gas.temperature_k == root && result.hp_iterations == 0U);
            policy = rp_combustion_default_options(); policy.hp_upper_temperature_k = root;
            CHECK(rp_ch4_o2_equilibrium_hp_enthalpy(&inlet, &policy, &result, NULL) == RP_OK);
            CHECK(result.gas.temperature_k == root && result.hp_iterations == 0U);
        }
    }
    {
        const RpCh4O2Feed feed = reference_feed();
        RpCh4O2EnthalpyFeed inlet = enthalpy_feed(&feed);
        RpCombustionResult cold, hot;
        CHECK(rp_ch4_o2_equilibrium_hp_enthalpy(&inlet, NULL, &cold, NULL) == RP_OK);
        inlet.fuel_h_j_per_kg += 1e5;
        CHECK(rp_ch4_o2_equilibrium_hp_enthalpy(&inlet, NULL, &hot, NULL) == RP_OK);
        CHECK(hot.gas.temperature_k > cold.gas.temperature_k);
        CHECK(near(hot.gas.h_j_per_kg - cold.gas.h_j_per_kg, 1e5 / 4.4, 0.02));
    }
    {
        RpCh4O2Feed feed = reference_feed();
        RpCh4O2EnthalpyFeed inlet;
        double h = 0.0;
        feed.fuel_temperature_k = 6000.0; feed.oxidizer_temperature_k = 6000.0;
        inlet = enthalpy_feed(&feed);
        CHECK(rp_ch4_o2_inlet_enthalpy(&inlet, &h, NULL) == RP_OK);
        CHECK(near(h, (inlet.fuel_h_j_per_kg + 3.4 * inlet.oxidizer_h_j_per_kg) / 4.4, 1e-8));
        inlet.fuel_h_j_per_kg = nextafter(inlet.fuel_h_j_per_kg, INFINITY);
        CHECK(rp_ch4_o2_inlet_enthalpy(&inlet, &h, NULL) == RP_OUT_OF_DOMAIN);
        feed.fuel_temperature_k = 200.0; feed.oxidizer_temperature_k = 200.0;
        inlet = enthalpy_feed(&feed);
        inlet.oxidizer_h_j_per_kg = nextafter(inlet.oxidizer_h_j_per_kg, -INFINITY);
        CHECK(rp_ch4_o2_inlet_enthalpy(&inlet, &h, NULL) == RP_OUT_OF_DOMAIN);
    }
}
static void test_explicit_enthalpy_failures(void)
{
    const RpCh4O2Feed feed = reference_feed();
    const RpCh4O2EnthalpyFeed good = enthalpy_feed(&feed);
    RpCh4O2EnthalpyFeed inlet;
    RpCombustionResult result, sentinel;
    RpCombustionOptions policy;
    double h = 123.0;
    memset(&sentinel, 0x5a, sizeof(sentinel));
    for (unsigned int i = 0U; i < 18U; ++i) {
        RpStatus expected = RP_OUT_OF_DOMAIN;
        inlet = good; result = sentinel;
        switch (i) {
            case 0U: inlet.pressure_pa = NAN; expected = RP_INVALID_ARGUMENT; break;
            case 1U: inlet.pressure_pa = 0.0; expected = RP_INVALID_ARGUMENT; break;
            case 2U: inlet.oxidizer_fuel_mass_ratio = INFINITY; expected = RP_INVALID_ARGUMENT; break;
            case 3U: inlet.fuel_h_j_per_kg = NAN; expected = RP_INVALID_ARGUMENT; break;
            case 4U: inlet.oxidizer_h_j_per_kg = INFINITY; expected = RP_INVALID_ARGUMENT; break;
            case 5U: inlet.phase = RP_FEED_LIQUID; break;
            case 6U: inlet.phase = (RpFeedPhase)9; break;
            case 7U: inlet.basis = RP_ENTHALPY_UNSPECIFIED; break;
            case 8U: inlet.basis = (RpEnthalpyBasis)9; break;
            case 9U: inlet.pressure_pa = 99.0; break;
            case 10U: inlet.pressure_pa = 1e9 + 1.0; break;
            case 11U: inlet.oxidizer_fuel_mass_ratio = 0.09; break;
            case 12U: inlet.oxidizer_fuel_mass_ratio = 20.01; break;
            case 13U: inlet.fuel_h_j_per_kg = -DBL_MAX; break;
            case 14U: inlet.fuel_h_j_per_kg = DBL_MAX; break;
            case 15U: inlet.oxidizer_h_j_per_kg = -DBL_MAX; break;
            case 16U: inlet.oxidizer_h_j_per_kg = DBL_MAX; break;
            default: inlet.oxidizer_fuel_mass_ratio = -1.0; expected = RP_INVALID_ARGUMENT; break;
        }
        CHECK(rp_ch4_o2_inlet_enthalpy(&inlet, &h, NULL) == expected);
        CHECK(h == 123.0);
        CHECK(rp_ch4_o2_equilibrium_hp_enthalpy(&inlet, NULL, &result, NULL) == expected);
        CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
    }
    result = sentinel;
    CHECK(rp_ch4_o2_inlet_enthalpy(NULL, &h, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_ch4_o2_inlet_enthalpy(&good, NULL, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_ch4_o2_equilibrium_hp_enthalpy(NULL, NULL, &result, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_ch4_o2_equilibrium_hp_enthalpy(&good, NULL, NULL, NULL) == RP_INVALID_ARGUMENT);
    policy = rp_combustion_default_options(); policy.hp_lower_temperature_k = 999.0;
    CHECK(rp_ch4_o2_equilibrium_hp_enthalpy(&good, &policy, &result, NULL) == RP_INVALID_ARGUMENT);
    policy = rp_combustion_default_options(); policy.hp_upper_temperature_k = 6001.0;
    CHECK(rp_ch4_o2_equilibrium_hp_enthalpy(&good, &policy, &result, NULL) == RP_INVALID_ARGUMENT);
    policy = rp_combustion_default_options(); policy.hp_upper_temperature_k = 3500.0;
    CHECK(rp_ch4_o2_equilibrium_hp_enthalpy(&good, &policy, &result, NULL) == RP_NOT_BRACKETED);
    policy = rp_combustion_default_options(); policy.max_equilibrium_iterations = 1U;
    CHECK(rp_ch4_o2_equilibrium_hp_enthalpy(&good, &policy, &result, NULL) == RP_NO_CONVERGENCE);
    policy = rp_combustion_default_options(); policy.max_hp_iterations = 1U;
    CHECK(rp_ch4_o2_equilibrium_hp_enthalpy(&good, &policy, &result, NULL) == RP_NO_CONVERGENCE);
    CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
}
static RpCh4O2AnchorFeed anchor_feed(void)
{
    const RpCh4O2AnchorFeed feed = {1e7, 3.4, "CH4(L)", "O2(L)", 111.643, 90.170, RP_FEED_LIQUID};
    return feed;
}
static void test_liquid_anchor(void)
{
    RpCh4O2AnchorFeed feed = anchor_feed();
    RpAnchorInlet inlet;
    RpCombustionResult result;
    const RpCh4O2Feed gas = reference_feed();
    RpCombustionResult gas_result;
    CHECK(strcmp(rp_anchor_dataset_id(), "cea-v3.3.4-ch4l-o2l-assigned-v1") == 0);
    CHECK(rp_ch4_o2_anchor_inlet(&feed, &inlet, NULL) == RP_OK);
    CHECK(near(inlet.fuel_h_j_per_kg, -89233000.0 / 16.04246, 1e-8));
    CHECK(near(inlet.oxidizer_h_j_per_kg, -12979000.0 / 31.9988, 1e-8));
    CHECK(near(inlet.mixture_h_j_per_kg,
               (-89233000.0 / 16.04246 - 3.4 * 12979000.0 / 31.9988) / 4.4, 1e-8));
    CHECK(near(inlet.element_inventory_kmol_per_kg[0], 1.0 / (16.04246 * 4.4), 1e-16));
    CHECK(near(inlet.element_inventory_kmol_per_kg[1], 4.0 / (16.04246 * 4.4), 1e-16));
    CHECK(near(inlet.element_inventory_kmol_per_kg[2], 6.8 / (31.9988 * 4.4), 1e-16));
    CHECK(rp_ch4_o2_equilibrium_hp_anchor(&feed, NULL, &result, NULL) == RP_OK);
    CHECK(fabs(result.enthalpy_residual_j_per_kg) <= 0.01);
    CHECK(near(result.gas.h_j_per_kg, inlet.mixture_h_j_per_kg, 0.01));
    check_elements(&result, &gas);
    CHECK(rp_ch4_o2_equilibrium_hp(&gas, NULL, &gas_result, NULL) == RP_OK);
    CHECK(result.gas.temperature_k < gas_result.gas.temperature_k);
    {
        RpFrozenNozzleInput input = nozzle_input(&result.gas, 10.0);
        RpFrozenNozzleFixedResult base, doubled;
        CHECK(rp_nozzle_solve_frozen_fixed_area(&input, 0.01, NULL, &base, NULL) == RP_OK);
        CHECK(rp_nozzle_solve_frozen_fixed_area(&input, 0.02, NULL, &doubled, NULL) == RP_OK);
        CHECK(near(doubled.thrust_n, 2.0 * base.thrust_n, 1e-7));
        CHECK(near(doubled.mass_flow_kg_per_s, 2.0 * base.mass_flow_kg_per_s, 1e-10));
        CHECK(base.specific_impulse_s == doubled.specific_impulse_s);
    }
    for (unsigned int i = 0U; i < 3U; ++i) {
        feed.oxidizer_fuel_mass_ratio = 2.6 + 0.8 * (double)i;
        CHECK(rp_ch4_o2_anchor_inlet(&feed, &inlet, NULL) == RP_OK);
        CHECK(rp_ch4_o2_equilibrium_hp_anchor(&feed, NULL, &result, NULL) == RP_OK);
        CHECK(near(result.gas.h_j_per_kg, inlet.mixture_h_j_per_kg, 0.01));
        {
            RpCh4O2Feed elemental_feed = gas;
            elemental_feed.oxidizer_fuel_mass_ratio = feed.oxidizer_fuel_mass_ratio;
            check_elements(&result, &elemental_feed);
        }
    }
}
static void test_liquid_anchor_failures(void)
{
    const RpCh4O2AnchorFeed good = anchor_feed();
    RpCh4O2AnchorFeed feed;
    RpCombustionResult result, sentinel;
    RpAnchorInlet inlet, inlet_sentinel;
    RpCombustionOptions policy;
    memset(&sentinel, 0x5a, sizeof(sentinel));
    memset(&inlet_sentinel, 0x5a, sizeof(inlet_sentinel));
    for (unsigned int i = 0U; i < 21U; ++i) {
        RpStatus expected = RP_OUT_OF_DOMAIN;
        feed = good; result = sentinel; inlet = inlet_sentinel;
        switch (i) {
            case 0U: feed.pressure_pa = NAN; expected = RP_INVALID_ARGUMENT; break;
            case 1U: feed.pressure_pa = 0.0; expected = RP_INVALID_ARGUMENT; break;
            case 2U: feed.oxidizer_fuel_mass_ratio = INFINITY; expected = RP_INVALID_ARGUMENT; break;
            case 3U: feed.fuel_temperature_k = NAN; expected = RP_INVALID_ARGUMENT; break;
            case 4U: feed.oxidizer_temperature_k = INFINITY; expected = RP_INVALID_ARGUMENT; break;
            case 5U: feed.phase = RP_FEED_GAS; break;
            case 6U: feed.phase = (RpFeedPhase)9; break;
            case 7U: feed.fuel_anchor_id = "CH4"; break;
            case 8U: feed.oxidizer_anchor_id = "O2"; break;
            case 9U: feed.fuel_anchor_id = "RP-1"; break;
            case 10U: feed.fuel_temperature_k = nextafter(good.fuel_temperature_k, INFINITY); break;
            case 11U: feed.oxidizer_temperature_k = nextafter(good.oxidizer_temperature_k, -INFINITY); break;
            case 12U: feed.pressure_pa = 99.0; break;
            case 13U: feed.pressure_pa = 1e9 + 1.0; break;
            case 14U: feed.oxidizer_fuel_mass_ratio = 0.09; break;
            case 15U: feed.oxidizer_fuel_mass_ratio = 20.01; break;
            case 16U: feed.fuel_anchor_id = NULL; expected = RP_INVALID_ARGUMENT; break;
            case 17U: feed.oxidizer_anchor_id = NULL; expected = RP_INVALID_ARGUMENT; break;
            case 18U: feed.oxidizer_temperature_k = 0.0; expected = RP_INVALID_ARGUMENT; break;
            case 19U: feed.oxidizer_fuel_mass_ratio = -1.0; expected = RP_INVALID_ARGUMENT; break;
            default: feed.fuel_anchor_id = "O2(L)"; feed.oxidizer_anchor_id = "CH4(L)"; break;
        }
        CHECK(rp_ch4_o2_anchor_inlet(&feed, &inlet, NULL) == expected);
        CHECK(memcmp(&inlet, &inlet_sentinel, sizeof(inlet)) == 0);
        CHECK(rp_ch4_o2_equilibrium_hp_anchor(&feed, NULL, &result, NULL) == expected);
        CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
    }
    result = sentinel;
    CHECK(rp_ch4_o2_anchor_inlet(NULL, &inlet, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_ch4_o2_anchor_inlet(&good, NULL, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_ch4_o2_equilibrium_hp_anchor(NULL, NULL, &result, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_ch4_o2_equilibrium_hp_anchor(&good, NULL, NULL, NULL) == RP_INVALID_ARGUMENT);
    policy = rp_combustion_default_options(); policy.hp_lower_temperature_k = 999.0;
    CHECK(rp_ch4_o2_equilibrium_hp_anchor(&good, &policy, &result, NULL) == RP_INVALID_ARGUMENT);
    policy = rp_combustion_default_options(); policy.hp_upper_temperature_k = 6001.0;
    CHECK(rp_ch4_o2_equilibrium_hp_anchor(&good, &policy, &result, NULL) == RP_INVALID_ARGUMENT);
    policy = rp_combustion_default_options(); policy.hp_upper_temperature_k = 3000.0;
    CHECK(rp_ch4_o2_equilibrium_hp_anchor(&good, &policy, &result, NULL) == RP_NOT_BRACKETED);
    policy = rp_combustion_default_options(); policy.max_equilibrium_iterations = 1U;
    CHECK(rp_ch4_o2_equilibrium_hp_anchor(&good, &policy, &result, NULL) == RP_NO_CONVERGENCE);
    policy = rp_combustion_default_options(); policy.max_hp_iterations = 1U;
    CHECK(rp_ch4_o2_equilibrium_hp_anchor(&good, &policy, &result, NULL) == RP_NO_CONVERGENCE);
    CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
    {
        RpCh4O2Feed old = {1e7, 3.4, 111.643, 90.170, RP_FEED_LIQUID};
        double h = 123.0;
        CHECK(rp_ch4_o2_feed_enthalpy(&old, &h, NULL) == RP_OUT_OF_DOMAIN);
        old.phase = RP_FEED_GAS;
        CHECK(rp_ch4_o2_feed_enthalpy(&old, &h, NULL) == RP_OUT_OF_DOMAIN);
        CHECK(h == 123.0);
    }
}
int main(void)
{
    test_tp_hp_reference();
    test_sweep_and_relations();
    test_failures();
    test_mixture_failure_contract();
    test_constant_cp_limit();
    test_fixed_geometry();
    test_explicit_enthalpy();
    test_explicit_enthalpy_failures();
    test_liquid_anchor();
    test_liquid_anchor_failures();
    (void)printf("combustion: %u checks, %u failures\n", checks, failures);
    return failures == 0U ? 0 : 1;
}
