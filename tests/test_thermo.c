#include "rocketperf/thermo.h"
#include "rocketperf/numeric.h"
#include <math.h>
#include <stdio.h>
static unsigned int checks = 0U;
static unsigned int failures = 0U;
static void check(int condition, const char *label, int line) { ++checks; if (!condition) { ++failures; (void)fprintf(stderr, "FAIL line %d: %s\n", line, label); } }
#define CHECK(condition) check((condition), #condition, __LINE__)
static int near(double actual, double expected, double tolerance) { return rp_isfinite(actual) && fabs(actual - expected) <= tolerance; }
int main(void)
{
    const RpNasa9Range ranges[2] = {
        {200.0, 1000.0, {0.0, 0.0, 3.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0}, 0.0, 0.0},
        {1000.0, 6000.0, {0.0, 0.0, 3.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0}, 0.0, 0.0}
    };
    const RpNasa9Species species = {"fixture_gas", 28.0134, 2U, ranges};
    RpThermoState state = {0.0, 0.0, 0.0};
    RpError error = {0};
    const double r = 8314.46261815324 / 28.0134;
    CHECK(rp_nasa9_evaluate(&species, 300.0, &state, &error) == RP_OK);
    CHECK(error.code == RP_OK);
    CHECK(near(state.cp_j_per_kg_k, 3.5 * r, 1e-12));
    CHECK(near(state.h_j_per_kg, 3.5 * r * 300.0, 1e-9));
    CHECK(near(state.s_j_per_kg_k, 3.5 * r * log(300.0), 1e-9));
    CHECK(rp_nasa9_evaluate(&species, 1000.0, &state, &error) == RP_OK);
    CHECK(near(state.cp_j_per_kg_k, 3.7 * r, 1e-12));
    CHECK(rp_nasa9_evaluate(&species, 6000.1, &state, &error) == RP_OUT_OF_DOMAIN);
    CHECK(rp_nasa9_evaluate(&species, NAN, &state, &error) == RP_INVALID_ARGUMENT);
    CHECK(rp_nasa9_evaluate(&species, 300.0, NULL, &error) == RP_INVALID_ARGUMENT);
    CHECK(rp_nasa9_evaluate(NULL, 300.0, &state, &error) == RP_INVALID_ARGUMENT);
    (void)printf("thermo: %u checks, %u failures\n", checks, failures);
    return failures == 0U ? 0 : 1;
}


