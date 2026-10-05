#include "rocketperf/thermo.h"
#include "rocketperf/numeric.h"
#include "reference/nasa9_cantera.h"
#include "rocketperf/liquid_feed.h"
#include "reference/liquid_feed.h"

#include <float.h>
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

static int near(double actual, double expected, double relative, double absolute)
{
    return rp_isfinite(actual) && fabs(actual - expected) <= absolute + relative * fabs(expected);
}

static void test_reference(void)
{
    for (size_t index = 0U; index < sizeof(rp_thermo_references) / sizeof(rp_thermo_references[0]); ++index) {
        const RpThermoReference *reference = &rp_thermo_references[index];
        const RpNasa9Species *species = rp_thermo_find_species(reference->id);
        RpThermoState state;
        RpError error = {RP_IO_ERROR, "old error"};
        CHECK(species != NULL);
        CHECK(rp_nasa9_evaluate(species, reference->temperature_k, &state, &error) == RP_OK);
        CHECK(error.code == RP_OK && error.message[0] == '\0');
        CHECK(near(state.cp_j_per_kg_k, reference->cp, 2e-11, 1e-7));
        CHECK(near(state.h_j_per_kg, reference->h, 2e-11, 1e-6));
        CHECK(near(state.s_j_per_kg_k, reference->s, 2e-11, 1e-7));
    }
}

static void test_integral_relations(void)
{
    static const char *ids[] = {"H2", "O2", "N2", "H2O", "CO", "CO2", "CH4", "H", "O", "OH"};
    static const double temperatures[] = {350.0, 1800.0, 4000.0};
    for (size_t index = 0U; index < sizeof(ids) / sizeof(ids[0]); ++index) {
        const RpNasa9Species *species = rp_thermo_find_species(ids[index]);
        RpThermoState lower, center, upper;
        CHECK(rp_nasa9_validate(species, NULL) == RP_OK);
        for (size_t point = 0U; point < sizeof(temperatures) / sizeof(temperatures[0]); ++point) {
            const double temperature = temperatures[point];
            const double step = temperature * 1e-5;
            CHECK(rp_nasa9_evaluate(species, temperature - step, &lower, NULL) == RP_OK);
            CHECK(rp_nasa9_evaluate(species, temperature, &center, NULL) == RP_OK);
            CHECK(rp_nasa9_evaluate(species, temperature + step, &upper, NULL) == RP_OK);
            CHECK(near((upper.h_j_per_kg - lower.h_j_per_kg) / (2.0 * step), center.cp_j_per_kg_k, 1e-7, 1e-5));
            CHECK(near((upper.s_j_per_kg_k - lower.s_j_per_kg_k) / (2.0 * step), center.cp_j_per_kg_k / temperature, 1e-7, 1e-8));
        }
        for (unsigned int interval = 1U; interval < species->range_count; ++interval) {
            const double boundary = species->ranges[interval].t_min_k;
            CHECK(rp_nasa9_evaluate(species, nextafter(boundary, 0.0), &lower, NULL) == RP_OK);
            CHECK(rp_nasa9_evaluate(species, boundary, &upper, NULL) == RP_OK);
            CHECK(near(lower.cp_j_per_kg_k, upper.cp_j_per_kg_k, 1e-5, 1e-3));
            CHECK(near(lower.h_j_per_kg, upper.h_j_per_kg, 1e-5, 0.1));
            CHECK(near(lower.s_j_per_kg_k, upper.s_j_per_kg_k, 1e-5, 1e-3));
        }
        CHECK(rp_nasa9_evaluate(species, species->ranges[species->range_count - 1U].t_max_k, &center, NULL) == RP_OK);
        CHECK(rp_nasa9_evaluate(species, species->ranges[species->range_count - 1U].t_max_k + 1.0, &center, NULL) == RP_OUT_OF_DOMAIN);
    }
}

static void test_formula_and_reference_basis(void)
{
    RpNasa9Range interval = {200.0, 1000.0, {0.0}, 0.0, 0.0};
    RpNasa9Species species = {"analytic_fixture", RP_UNIVERSAL_GAS_CONSTANT_J_KMOL_K, 1U, &interval};
    RpThermoState state;
    const double temperature = 400.0;
    const double cp_terms[9] = {1.0 / (temperature * temperature), 1.0 / temperature, 1.0, temperature,
                               temperature * temperature, pow(temperature, 3.0), pow(temperature, 4.0), 0.0, 0.0};
    const double h_terms[9] = {-1.0 / temperature, log(temperature), temperature, pow(temperature, 2.0) / 2.0,
                              pow(temperature, 3.0) / 3.0, pow(temperature, 4.0) / 4.0, pow(temperature, 5.0) / 5.0, 1.0, 0.0};
    const double s_terms[9] = {-1.0 / (2.0 * temperature * temperature), -1.0 / temperature, log(temperature),
                              temperature, pow(temperature, 2.0) / 2.0, pow(temperature, 3.0) / 3.0,
                              pow(temperature, 4.0) / 4.0, 0.0, 1.0};
    for (unsigned int index = 0U; index < 9U; ++index) {
        memset(interval.coefficients, 0, sizeof(interval.coefficients));
        interval.coefficients[2] = 3.5;
        interval.coefficients[index] += 1.0;
        CHECK(rp_nasa9_evaluate(&species, temperature, &state, NULL) == RP_OK);
        CHECK(near(state.cp_j_per_kg_k, 3.5 + cp_terms[index], 1e-12, 1e-12));
        CHECK(near(state.h_j_per_kg, 3.5 * temperature + h_terms[index], 1e-12, 1e-10));
        CHECK(near(state.s_j_per_kg_k, 3.5 * log(temperature) + s_terms[index], 1e-12, 1e-10));
    }
    memset(interval.coefficients, 0, sizeof(interval.coefficients));
    interval.coefficients[2] = 3.5;
    interval.coefficients[7] = -3.5 * 298.15;
    CHECK(rp_nasa9_evaluate(&species, 298.15, &state, NULL) == RP_OK);
    CHECK(near(state.h_j_per_kg, 0.0, 0.0, 1e-12));
    interval.h_offset_j_per_kg = 123.0;
    interval.s_offset_j_per_kg_k = -17.0;
    CHECK(rp_nasa9_evaluate(&species, 298.15, &state, NULL) == RP_OK);
    CHECK(near(state.h_j_per_kg, 123.0, 0.0, 1e-12));
    CHECK(near(state.s_j_per_kg_k, 3.5 * log(298.15) - 17.0, 0.0, 1e-12));
}

static void test_real_formation_enthalpy(void)
{
    static const char *ids[] = {"H2", "O2", "N2", "H2O", "CO", "CO2", "CH4", "H", "O", "OH"};
    /* Header Hf values are J/mol; b1 already contains this reference. */
    static const double expected[] = {0.0, 0.0, 0.0, -241826.0, -110535.196,
                                      -393510.0, -74600.0, 217998.828, 249175.003, 37278.206};
    for (size_t index = 0U; index < sizeof(ids) / sizeof(ids[0]); ++index) {
        const RpNasa9Species *species = rp_thermo_find_species(ids[index]);
        RpThermoState state;
        CHECK(species != NULL);
        CHECK(rp_nasa9_evaluate(species, 298.15, &state, NULL) == RP_OK);
        CHECK(near(state.h_j_per_kg * species->molar_mass_kg_per_kmol / 1000.0,
                   expected[index], 0.0, 0.01));
    }
}

static void test_failures(void)
{
    RpNasa9Range ranges[2] = {
        {200.0, 1000.0, {0.0, 0.0, 3.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0}, 0.0, 0.0},
        {1000.0, 6000.0, {0.0, 0.0, 3.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0}, 0.0, 0.0}
    };
    RpNasa9Species species = {"boundary_fixture", 28.0134, 2U, ranges};
    const RpThermoState sentinel = {7.0, 8.0, 9.0};
    RpThermoState state = sentinel;
    RpError error;
    static const double invalid[] = {0.0, -1.0, NAN, INFINITY, -INFINITY};
    CHECK(rp_nasa9_evaluate(&species, nextafter(1000.0, 0.0), &state, &error) == RP_OK);
    CHECK(near(state.cp_j_per_kg_k, 3.5 * RP_UNIVERSAL_GAS_CONSTANT_J_KMOL_K / 28.0134, 1e-12, 1e-12));
    CHECK(rp_nasa9_evaluate(&species, 1000.0, &state, &error) == RP_OK);
    CHECK(near(state.cp_j_per_kg_k, 3.7 * RP_UNIVERSAL_GAS_CONSTANT_J_KMOL_K / 28.0134, 1e-12, 1e-12));
    state = sentinel;
    for (size_t index = 0U; index < sizeof(invalid) / sizeof(invalid[0]); ++index) {
        CHECK(rp_nasa9_evaluate(&species, invalid[index], &state, &error) == RP_INVALID_ARGUMENT);
        CHECK(memcmp(&state, &sentinel, sizeof(state)) == 0);
    }
    CHECK(rp_nasa9_evaluate(NULL, 300.0, &state, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_nasa9_evaluate(&species, 300.0, NULL, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_nasa9_evaluate(&species, 199.0, &state, NULL) == RP_OUT_OF_DOMAIN);
    CHECK(memcmp(&state, &sentinel, sizeof(state)) == 0);
    ranges[1].coefficients[0] = NAN;
    CHECK(rp_nasa9_evaluate(&species, 300.0, &state, NULL) == RP_INVALID_ARGUMENT);
    ranges[1].coefficients[0] = 0.0;
    ranges[1].t_min_k = 999.0;
    CHECK(rp_nasa9_validate(&species, NULL) == RP_INVALID_ARGUMENT);
    ranges[1].t_min_k = 1001.0;
    CHECK(rp_nasa9_validate(&species, NULL) == RP_INVALID_ARGUMENT);
    ranges[1].t_min_k = 1000.0;
    ranges[0].coefficients[2] = -1.0;
    CHECK(rp_nasa9_evaluate(&species, 300.0, &state, NULL) == RP_NUMERIC_ERROR);
    CHECK(memcmp(&state, &sentinel, sizeof(state)) == 0);
    ranges[0].coefficients[2] = 3.5;
    species.molar_mass_kg_per_kmol = DBL_MIN;
    CHECK(rp_nasa9_evaluate(&species, 300.0, &state, NULL) == RP_NUMERIC_ERROR);
    CHECK(memcmp(&state, &sentinel, sizeof(state)) == 0);
    species.molar_mass_kg_per_kmol = 0.0;
    CHECK(rp_nasa9_validate(&species, NULL) == RP_INVALID_ARGUMENT);
    species.molar_mass_kg_per_kmol = 28.0134;
    species.range_count = RP_NASA9_MAX_RANGES + 1U;
    CHECK(rp_nasa9_validate(&species, NULL) == RP_INVALID_ARGUMENT);
    CHECK(rp_thermo_find_species("fixture_gas") == NULL);
    CHECK(rp_thermo_find_species(NULL) == NULL);
    CHECK(rp_thermo_reference_pressure_pa() == 100000.0);
}

static void test_liquid_reference(void)
{
    for (size_t i = 0U; i < sizeof(rp_liquid_references) / sizeof(rp_liquid_references[0]); ++i) {
        const RpLiquidReference *r = &rp_liquid_references[i];
        const RpLiquidFeedQuery query = {rp_liquid_feed_dataset_id(), r->fluid,
                                         RP_LIQUID_SINGLE_PHASE, r->temperature, r->pressure};
        RpLiquidFeedState result;
        RpError error = {RP_IO_ERROR, "old error"};
        /* Reproduce the pinned CEA kg/kmol -> kg/mol conversion, not a separately
         * rounded decimal literal (the methane quotient differs by one ULP). */
        const double mass = (strcmp(r->fluid, "Methane") == 0 ? 16.04246 : 31.9988) / 1000.0;
        const double eos_mass = strcmp(r->fluid, "Methane") == 0 ? 0.0160428 : 0.0319988;
        CHECK(rp_liquid_feed_evaluate(&query, &result, &error) == RP_OK);
        CHECK(error.code == RP_OK && error.message[0] == '\0');
        CHECK(near(result.density_kg_per_m3, r->density, r->node ? 2e-13 : 0.0005, 1e-9));
        CHECK(near(result.h_j_per_mol, r->h_molar, 0.0, r->node ? 1e-8 : 5.0));
        CHECK(result.eos_molar_mass_kg_per_mol == eos_mass);
        CHECK(result.chemical_molar_mass_kg_per_mol == mass);
        CHECK(near(result.h_j_per_kg * mass, result.h_j_per_mol, 2e-13, 1e-9));
    }
}

static void test_liquid_rejections(void)
{
    RpLiquidFeedQuery query = {rp_liquid_feed_dataset_id(), "Methane",
                               RP_LIQUID_SINGLE_PHASE, 120.0, 1e7};
    const RpLiquidFeedState sentinel = {1.0, 2.0, 3.0, 4.0, 5.0};
    RpLiquidFeedState result = sentinel;
    RpError error = {0};
    const double invalid[] = {0.0, -1.0, NAN, INFINITY, -INFINITY};
    CHECK(rp_liquid_feed_evaluate(NULL, &result, &error) == RP_INVALID_ARGUMENT);
    CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
    CHECK(rp_liquid_feed_evaluate(&query, NULL, NULL) == RP_INVALID_ARGUMENT);
    for (size_t i = 0U; i < sizeof(invalid) / sizeof(invalid[0]); ++i) {
        query.temperature_k = invalid[i];
        CHECK(rp_liquid_feed_evaluate(&query, &result, &error) == RP_INVALID_ARGUMENT);
        CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
        query.temperature_k = 120.0;
        query.pressure_pa = invalid[i];
        CHECK(rp_liquid_feed_evaluate(&query, &result, &error) == RP_INVALID_ARGUMENT);
        CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
        query.pressure_pa = 1e7;
    }
    query.dataset_id = NULL;
    CHECK(rp_liquid_feed_evaluate(&query, &result, NULL) == RP_INVALID_ARGUMENT);
    query.dataset_id = "arbitrary-enthalpy-zero";
    CHECK(rp_liquid_feed_evaluate(&query, &result, &error) == RP_OUT_OF_DOMAIN);
    CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
    query.dataset_id = rp_liquid_feed_dataset_id();
    query.fluid_id = NULL;
    CHECK(rp_liquid_feed_evaluate(&query, &result, NULL) == RP_INVALID_ARGUMENT);
    query.fluid_id = "RP-1";
    CHECK(rp_liquid_feed_evaluate(&query, &result, &error) == RP_OUT_OF_DOMAIN);
    CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
    query.fluid_id = "Methane";
    for (int phase = -1; phase <= 3; ++phase) {
        if (phase == RP_LIQUID_SINGLE_PHASE) { continue; }
        query.phase = (RpLiquidFeedPhase)phase;
        CHECK(rp_liquid_feed_evaluate(&query, &result, &error) == RP_OUT_OF_DOMAIN);
        CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
    }
    query.phase = RP_LIQUID_SINGLE_PHASE;
    for (size_t f = 0U; f < 2U; ++f) {
        const double lower = f == 0U ? 100.0 : 80.0;
        const double upper = f == 0U ? 140.0 : 110.0;
        const double outside[] = {nextafter(lower, 0.0), nextafter(upper, INFINITY)};
        query.fluid_id = f == 0U ? "Methane" : "Oxygen";
        for (size_t i = 0U; i < 2U; ++i) {
            query.temperature_k = outside[i];
            CHECK(rp_liquid_feed_evaluate(&query, &result, &error) == RP_OUT_OF_DOMAIN);
            CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
        }
        query.temperature_k = lower;
        query.pressure_pa = nextafter(1e6, 0.0);
        CHECK(rp_liquid_feed_evaluate(&query, &result, &error) == RP_OUT_OF_DOMAIN);
        CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
        query.pressure_pa = nextafter(20e6, INFINITY);
        CHECK(rp_liquid_feed_evaluate(&query, &result, &error) == RP_OUT_OF_DOMAIN);
        CHECK(memcmp(&result, &sentinel, sizeof(result)) == 0);
        query.pressure_pa = 1e7;
    }
    CHECK(strlen(rp_liquid_feed_reference_sha256()) == 64U);
}

int main(void)
{
    test_reference();
    test_integral_relations();
    test_formula_and_reference_basis();
    test_real_formation_enthalpy();
    test_failures();
    test_liquid_reference();
    test_liquid_rejections();
    (void)printf("thermo: %u checks, %u failures\n", checks, failures);
    return failures == 0U ? 0 : 1;
}
