/* Development-side baseline probe; production equations are linked unchanged.
 * Optional counted source is generated under build/work2 with exact anchors. */
#include "rocketperf/combustion.h"
#include "rocketperf/liquid_combustion.h"
#include "work2_baseline_counters.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#endif

RpBaselineCounters rp_baseline_counters = {0};

static double wall_seconds(void)
{
#ifdef _WIN32
    LARGE_INTEGER frequency, counter;
    (void)QueryPerformanceFrequency(&frequency);
    (void)QueryPerformanceCounter(&counter);
    return (double)counter.QuadPart / (double)frequency.QuadPart;
#else
    struct timespec value;
    (void)timespec_get(&value, TIME_UTC);
    return (double)value.tv_sec + (double)value.tv_nsec / 1e9;
#endif
}

static double cpu_seconds(void)
{
#ifdef _WIN32
    FILETIME created, exited, kernel, user;
    ULARGE_INTEGER k, u;
    if (!GetProcessTimes(GetCurrentProcess(), &created, &exited, &kernel, &user)) { return -1.0; }
    k.LowPart = kernel.dwLowDateTime; k.HighPart = kernel.dwHighDateTime;
    u.LowPart = user.dwLowDateTime; u.HighPart = user.dwHighDateTime;
    return ((double)k.QuadPart + (double)u.QuadPart) / 1e7;
#else
    return (double)clock() / (double)CLOCKS_PER_SEC;
#endif
}

static void json_text(const char *value)
{
    (void)putchar('"');
    for (; *value != '\0'; ++value) {
        const unsigned char byte = (unsigned char)*value;
        if (byte == '"' || byte == '\\') { (void)putchar('\\'); }
        if (byte < 32U) { (void)printf("\\u%04x", (unsigned int)byte); }
        else { (void)putchar((int)byte); }
    }
    (void)putchar('"');
}

static RpStatus bisect_hp(const RpCh4O2Feed *feed, const RpCombustionOptions *options,
                         RpCombustionResult *output, unsigned int *calls, RpError *error)
{
    double lower = options->hp_lower_temperature_k;
    double upper = options->hp_upper_temperature_k;
    RpCombustionResult low, high, state;
    RpStatus status;
    ++*calls;
    status = rp_ch4_o2_equilibrium_tp(feed, lower, options, &low, error);
    if (status != RP_OK) { return status; }
    ++*calls;
    status = rp_ch4_o2_equilibrium_tp(feed, upper, options, &high, error);
    if (status != RP_OK) { return status; }
    if ((low.enthalpy_residual_j_per_kg < 0.0) == (high.enthalpy_residual_j_per_kg < 0.0)) {
        return rp_error_set(error, RP_NOT_BRACKETED, "Independent bisection has no bracket.");
    }
    for (unsigned int i = 1U; i <= 100U; ++i) {
        const double middle = 0.5 * lower + 0.5 * upper;
        ++*calls;
        status = rp_ch4_o2_equilibrium_tp(feed, middle, options, &state, error);
        if (status != RP_OK) { return status; }
        if (fabs(state.enthalpy_residual_j_per_kg) <= options->enthalpy_tolerance_j_per_kg) {
            state.hp_iterations = i;
            *output = state;
            return RP_OK;
        }
        if ((state.enthalpy_residual_j_per_kg < 0.0) == (low.enthalpy_residual_j_per_kg < 0.0)) {
            lower = middle;
            low = state;
        } else { upper = middle; }
    }
    return rp_error_set(error, RP_NO_CONVERGENCE, "Independent bisection budget exhausted.");
}

static RpStatus solve(const char *mode, const RpCh4O2Feed *feed, double temperature,
                      const RpCombustionOptions *options, RpCombustionResult *output,
                      unsigned int *outer_calls, RpError *error)
{
    if (strcmp(mode, "tp") == 0) {
        return rp_ch4_o2_equilibrium_tp(feed, temperature, options, output, error);
    }
    if (strcmp(mode, "bisect") == 0) { return bisect_hp(feed, options, output, outer_calls, error); }
    if (strcmp(mode, "anchor") == 0) {
        const RpCh4O2AnchorFeed inlet = {feed->pressure_pa, feed->oxidizer_fuel_mass_ratio,
            "CH4(L)", "O2(L)", 111.643, 90.170, RP_FEED_LIQUID};
        return rp_ch4_o2_equilibrium_hp_anchor(&inlet, options, output, error);
    }
    if (strcmp(mode, "rp1") == 0) {
        const RpKeroseneAnchorFeed inlet = {rp_kerosene_dataset_id(),
            {feed->pressure_pa, feed->oxidizer_fuel_mass_ratio, "RP-1", "O2(L)", 298.15, 90.170, RP_FEED_LIQUID}};
        return rp_kerosene_equilibrium_hp_anchor(&inlet, options, output, error);
    }
    if (strcmp(mode, "liquid") == 0) {
        const RpContinuousLiquidFeed inlet = {rp_liquid_feed_dataset_id(), rp_liquid_feed_enthalpy_basis_id(),
            RP_LIQUID_SINGLE_PHASE, RP_LIQUID_SINGLE_PHASE, 120.0, 1e7, 100.0, 1e7,
            feed->pressure_pa, feed->oxidizer_fuel_mass_ratio};
        RpContinuousLiquidHpResult result;
        const RpStatus status = rp_ch4_o2_continuous_liquid_hp(&inlet, options, &result, error);
        if (status == RP_OK) { *output = result.chamber; }
        return status;
    }
    if (strcmp(mode, "explicit") == 0 || strncmp(mode, "mixed-", 6U) == 0) {
        RpThermoState fuel, oxidizer;
        RpStatus status = rp_nasa9_evaluate(rp_thermo_find_species("CH4"), 298.15, &fuel, error);
        const double ratio = feed->oxidizer_fuel_mass_ratio;
        if (status != RP_OK) { return status; }
        status = rp_nasa9_evaluate(rp_thermo_find_species("O2"), 298.15, &oxidizer, error);
        if (status != RP_OK) { return status; }
        if (strcmp(mode, "explicit") == 0) {
            const RpCh4O2EnthalpyFeed inlet = {feed->pressure_pa, ratio, fuel.h_j_per_kg,
                oxidizer.h_j_per_kg, RP_FEED_GAS, RP_ENTHALPY_NASA9_CEA_V334};
            return rp_ch4_o2_equilibrium_hp_enthalpy(&inlet, options, output, error);
        } else {
            RpChoMixedFeed inlet = {feed->pressure_pa, (fuel.h_j_per_kg + ratio * oxidizer.h_j_per_kg) / (1.0 + ratio),
                {1.0 / (16.04246 * (1.0 + ratio)), 4.0 / (16.04246 * (1.0 + ratio)),
                 2.0 * ratio / (31.9988 * (1.0 + ratio))}, RP_ENTHALPY_NASA9_CEA_V334};
            if (strcmp(mode, "mixed-scale") == 0) {
                for (unsigned int e = 0U; e < 3U; ++e) { inlet.elements_kmol_per_kg[e] *= temperature; }
            }
            if (strcmp(mode, "mixed-zero") == 0) { inlet.elements_kmol_per_kg[0] = 0.0; }
            if (strcmp(mode, "mixed-basis") == 0) { inlet.basis = RP_ENTHALPY_UNSPECIFIED; }
            return rp_cho_equilibrium_hp_mixed(&inlet, options, output, error);
        }
    }
    if (strcmp(mode, "hp") != 0) { return rp_error_set(error, RP_INVALID_ARGUMENT, "Unknown probe mode."); }
    return rp_ch4_o2_equilibrium_hp(feed, options, output, error);
}

static double number(const char *text)
{
    char *end;
    const double value = strtod(text, &end);
    if (end == text || *end != '\0') { (void)fprintf(stderr, "Invalid probe argument.\n"); exit(2); }
    return value;
}

int main(int argc, char **argv)
{
    RpCh4O2Feed feed = {1e7, 3.4, 298.15, 298.15, RP_FEED_GAS};
    RpCombustionOptions policy = rp_combustion_default_options();
    RpCombustionResult output, sentinel;
    RpError error = {RP_OK, ""};
    RpStatus status = RP_INVALID_ARGUMENT;
    unsigned int outer_calls = 0U;
    unsigned int completed = 0U;
    double started, elapsed, cpu_started, cpu_elapsed;
    unsigned int repetitions;
    if (argc != 12) { (void)fprintf(stderr, "mode p of T eqtol htol maxeq maxhp lower upper repetitions\n"); return 2; }
    feed.pressure_pa = number(argv[2]); feed.oxidizer_fuel_mass_ratio = number(argv[3]);
    policy.equilibrium_tolerance = number(argv[5]); policy.enthalpy_tolerance_j_per_kg = number(argv[6]);
    policy.max_equilibrium_iterations = (unsigned int)number(argv[7]);
    policy.max_hp_iterations = (unsigned int)number(argv[8]);
    policy.hp_lower_temperature_k = number(argv[9]); policy.hp_upper_temperature_k = number(argv[10]);
    repetitions = (unsigned int)number(argv[11]);
    if (repetitions == 0U || repetitions > 10000U) { return 2; }
    memset(&sentinel, 0x5a, sizeof(sentinel));
    started = wall_seconds(); cpu_started = cpu_seconds();
    for (unsigned int i = 0U; i < repetitions; ++i) {
        output = sentinel;
        status = solve(argv[1], &feed, number(argv[4]), &policy, &output, &outer_calls, &error);
        ++completed;
        if (status != RP_OK) { break; }
    }
    elapsed = wall_seconds() - started; cpu_elapsed = cpu_seconds() - cpu_started;
    (void)printf("{\"status\":%d,\"status_name\":", (int)status); json_text(rp_status_name(status));
    (void)printf(",\"error\":"); json_text(error.message);
    (void)printf(",\"failure_output_unchanged\":%s,\"repetitions_completed\":%u,\"outer_tp_calls\":%u,\"kernel_wall_seconds\":%.17g,\"kernel_cpu_seconds\":%.17g",
        memcmp(&output, &sentinel, sizeof(output)) == 0 ? "true" : "false", completed, outer_calls, elapsed, cpu_elapsed);
    (void)printf(",\"counts\":{");
#define COUNT(field) (void)printf("\"" #field "\":%llu,", rp_baseline_counters.field)
    COUNT(tp_calls); COUNT(temperature_solves); COUNT(gibbs_vectors); COUNT(equilibrium_nasa9_calls);
    COUNT(residual_jacobian_evaluations); COUNT(newton_steps); COUNT(linear_solves);
    COUNT(line_search_trials); COUNT(backtrack_reductions); COUNT(warm_attempts); COUNT(warm_successes);
    COUNT(cold_starts); COUNT(cold_fallbacks); COUNT(hp_trials);
#undef COUNT
    (void)printf("\"mixture_evaluations\":%llu}", rp_baseline_counters.mixture_evaluations);
    if (status == RP_OK) {
        (void)printf(",\"gas\":{\"temperature_k\":%.17g,\"pressure_pa\":%.17g,\"molar_mass_kg_per_kmol\":%.17g,\"gas_constant_j_per_kg_k\":%.17g,\"cp_frozen_j_per_kg_k\":%.17g,\"h_j_per_kg\":%.17g,\"s_j_per_kg_k\":%.17g,\"mole_fractions\":[",
            output.gas.temperature_k, output.gas.pressure_pa, output.gas.molar_mass_kg_per_kmol,
            output.gas.gas_constant_j_per_kg_k, output.gas.cp_frozen_j_per_kg_k,
            output.gas.h_j_per_kg, output.gas.s_j_per_kg_k);
        for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) { (void)printf("%s%.17g", i == 0U ? "" : ",", output.gas.mole_fractions[i]); }
        (void)printf("]},\"element_residuals\":[%.17g,%.17g,%.17g],\"equilibrium_residual\":%.17g,\"enthalpy_residual_j_per_kg\":%.17g,\"final_equilibrium_iterations\":%u,\"hp_iterations\":%u,\"graphite_activity\":%.17g",
            output.element_relative_residual[0], output.element_relative_residual[1], output.element_relative_residual[2],
            output.equilibrium_residual, output.enthalpy_residual_j_per_kg, output.equilibrium_iterations,
            output.hp_iterations, output.graphite_activity);
    }
    (void)printf("}\n");
    /* Rejections are data, transport errors are process failures. */
    return 0;
}
