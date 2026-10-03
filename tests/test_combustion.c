#include "rocketperf/combustion.h"
#include "rocketperf/frozen_nozzle.h"
#include "rocketperf/numeric.h"

#include <math.h>
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
int main(void)
{
    test_tp_hp_reference();
    test_sweep_and_relations();
    test_failures();
    test_mixture_failure_contract();
    test_constant_cp_limit();
    (void)printf("combustion: %u checks, %u failures\n", checks, failures);
    return failures == 0U ? 0 : 1;
}
