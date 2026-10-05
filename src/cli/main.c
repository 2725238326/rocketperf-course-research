#include "case_file.h"
#include "cycle_case.h"
#include "rocketperf/numeric.h"
#include "rocketperf/version.h"
#include "rocketperf/thermo.h"
#include "rocketperf/combustion.h"
#include "rocketperf/frozen_nozzle.h"

#include <ctype.h>
#include <errno.h>
#include <locale.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RP_STUDY_GRID_LIMIT 32U

static int parse_decimal_token(const char *start, const char **next, double *output)
{
    const char *cursor = start;
    unsigned int digits = 0U;
    char *end;
    double value;
    if (*cursor == '+' || *cursor == '-') { ++cursor; }
    while (*cursor >= '0' && *cursor <= '9') { ++cursor; ++digits; }
    if (*cursor == '.') {
        ++cursor;
        while (*cursor >= '0' && *cursor <= '9') { ++cursor; ++digits; }
    }
    if (digits == 0U) { return 0; }
    if (*cursor == 'e' || *cursor == 'E') {
        unsigned int exponent_digits = 0U;
        ++cursor;
        if (*cursor == '+' || *cursor == '-') { ++cursor; }
        while (*cursor >= '0' && *cursor <= '9') { ++cursor; ++exponent_digits; }
        if (exponent_digits == 0U) { return 0; }
    }
    if (*cursor != '\0' && *cursor != ',' && !isspace((unsigned char)*cursor)) { return 0; }
    errno = 0;
    value = strtod(start, &end);
    if (errno == ERANGE || end != cursor || !rp_isfinite(value)) { return 0; }
    *next = cursor;
    *output = value;
    return 1;
}

static int parse_grid(const char *text, double *values, size_t *count, int pressure)
{
    const char *cursor = text;
    size_t used = 0U;
    if (text == NULL || values == NULL || count == NULL || *text == '\0') { return 0; }
    while (*cursor != '\0') {
        const char *end;
        double value;
        while (isspace((unsigned char)*cursor)) { ++cursor; }
        if (*cursor == '\0' || *cursor == ',') { return 0; }
        if (!parse_decimal_token(cursor, &end, &value)) { return 0; }
        cursor = end;
        while (isspace((unsigned char)*cursor)) { ++cursor; }
        if (pressure ? value < 0.0 : value < 1.0 || value > 1e4) { return 0; }
        if (used >= RP_STUDY_GRID_LIMIT) { return 0; }
        values[used++] = value;
        if (*cursor == '\0') { break; }
        if (*cursor != ',') { return 0; }
        ++cursor;
        if (*cursor == '\0') { return 0; }
    }
    *count = used;
    return used != 0U;
}

static int study_main(const char *case_path, int option_count, char **options)
{
    static const double default_ratios[] = {1.0, 1.25, 1.6875, 2.0, 4.0, 8.0, 16.0};
    static const double default_pressures[] = {0.0, 25000.0, 50000.0, 100000.0};
    double ratios[RP_STUDY_GRID_LIMIT];
    double pressures[RP_STUDY_GRID_LIMIT];
    RpNozzleStudyPoint points[RP_STUDY_GRID_LIMIT * RP_STUDY_GRID_LIMIT];
    RpNozzleStudyGrid grid;
    RpCase study;
    RpError error = {0};
    size_t ratio_count = sizeof(default_ratios) / sizeof(default_ratios[0]);
    size_t pressure_count = sizeof(default_pressures) / sizeof(default_pressures[0]);
    size_t point_count = 0U;
    RpStatus status;
    int seen_ratios = 0;
    int seen_pressures = 0;
    memcpy(ratios, default_ratios, sizeof(default_ratios));
    memcpy(pressures, default_pressures, sizeof(default_pressures));
    for (int i = 0; i < option_count; ++i) {
        if (strcmp(options[i], "--area-ratios") == 0 && i + 1 < option_count) {
            if (seen_ratios++ || !parse_grid(options[++i], ratios, &ratio_count, 0)) {
                (void)fputs("Usage error: --area-ratios expects comma-separated values in 1...1e4.\n", stderr);
                return 2;
            }
        } else if (strcmp(options[i], "--ambient-pressures") == 0 && i + 1 < option_count) {
            if (seen_pressures++ || !parse_grid(options[++i], pressures, &pressure_count, 1)) {
                (void)fputs("Usage error: --ambient-pressures expects comma-separated finite non-negative Pa values.\n", stderr);
                return 2;
            }
        } else {
            (void)fputs("Usage: rocketperf study area-ratio-ambient CASE.ini [--area-ratios CSV] [--ambient-pressures CSV]\n", stderr);
            return 2;
        }
    }
    status = rp_case_load(case_path, &study, &error);
    if (status == RP_OK) {
        grid.area_ratios = ratios;
        grid.area_ratio_count = ratio_count;
        grid.ambient_pressures_pa = pressures;
        grid.ambient_pressure_count = pressure_count;
        status = rp_nozzle_scan_area_ratio_ambient(&study.input, &grid, points,
                                                   sizeof(points) / sizeof(points[0]),
                                                   &point_count, &error);
    }
    if (status == RP_OK) { status = rp_case_write_study_json(stdout, &study, &grid, points, point_count, &error); }
    if (status == RP_OK && fflush(stdout) != 0) {
        status = rp_error_set(&error, RP_IO_ERROR, "Cannot flush study JSON report.");
    }
    if (status != RP_OK) {
        (void)fprintf(stderr, "%s: %s\n", rp_status_name(status), error.message);
        return status == RP_PARSE_ERROR || status == RP_IO_ERROR ? 3 : 4;
    }
    for (size_t i = 0U; i < point_count; ++i) {
        if (points[i].status != RP_OK && points[i].status != RP_OUT_OF_DOMAIN) {
            (void)fputs("Study calculation failed; inspect per-point diagnostics in stdout.\n", stderr);
            return 4;
        }
    }
    return 0;
}

static int thermo_main(const char *id, const char *temperature_text)
{
    const RpNasa9Species *species = rp_thermo_find_species(id);
    const char *next;
    double temperature;
    RpThermoState state;
    RpError error;
    RpStatus status;
    if (!parse_decimal_token(temperature_text, &next, &temperature) || *next != '\0') {
        (void)fputs("Usage: rocketperf thermo SPECIES TEMPERATURE_K\n", stderr);
        return 2;
    }
    if (species == NULL) {
        (void)fputs("out_of_domain: Unknown species in the pinned neutral NASA9 dataset.\n", stderr);
        return 4;
    }
    status = rp_nasa9_evaluate(species, temperature, &state, &error);
    if (status != RP_OK) {
        (void)fprintf(stderr, "%s: %s\n", rp_status_name(status), error.message);
        return 4;
    }
    if (printf("{\"schema_version\":1,\"model\":\"nasa9_species_v1\",\"dataset_id\":\"%s\","
               "\"species\":\"%s\",\"temperature_k\":%.17g,\"reference_pressure_pa\":%.17g,"
               "\"molar_mass_kg_per_kmol\":%.17g,\"cp_j_per_kg_k\":%.17g,"
               "\"h_j_per_kg\":%.17g,\"s_j_per_kg_k\":%.17g,"
               "\"limitations\":[\"Single-species standard-state ideal-gas properties, not combustion equilibrium.\"]}\n",
               rp_thermo_dataset_id(), species->id, temperature, rp_thermo_reference_pressure_pa(),
               species->molar_mass_kg_per_kmol, state.cp_j_per_kg_k,
               state.h_j_per_kg, state.s_j_per_kg_k) < 0 || fflush(stdout) != 0) {
        (void)fputs("io_error: Cannot write thermo JSON report.\n", stderr);
        return 3;
    }
    return 0;
}

static int cycle_study_main(const char *path, const char *field_name, const char *csv)
{
    double values[RP_STUDY_GRID_LIMIT];
    size_t count = 0U;
    RpCycleStudyField field;
    RpError error = {0};
    RpStatus status;
    for (field = 0; field < RP_CYCLE_FIELD_COUNT; field = (RpCycleStudyField)(field + 1)) {
        if (strcmp(field_name, rp_cycle_study_field_name(field)) == 0) { break; }
    }
    /* All currently exposed study axes are nonnegative. C solver enforces the
     * narrower physical domain and records each rejected scenario. */
    if (field == RP_CYCLE_FIELD_COUNT || !parse_grid(csv, values, &count, 1)) {
        (void)fputs("Usage: rocketperf study prescribed-cycle CASE.ini FIELD CSV (1..32 finite nonnegative values)\n", stderr);
        return 2;
    }
    status = rp_cycle_case_study(path, field, values, count, stdout, &error);
    if (status == RP_OK && fflush(stdout) != 0) { status = rp_error_set(&error, RP_IO_ERROR, "Cannot flush cycle study."); }
    if (status != RP_OK) {
        (void)fprintf(stderr, "%s: %s\n", rp_status_name(status), error.message);
        return status == RP_IO_ERROR || status == RP_PARSE_ERROR ? 3 : 4;
    }
    return 0;
}

static int write_mixture(const RpGasMixture *gas)
{
    if (printf("{\"temperature_k\":%.17g,\"pressure_pa\":%.17g,\"molar_mass_kg_per_kmol\":%.17g,"
               "\"gas_constant_j_per_kg_k\":%.17g,\"cp_frozen_j_per_kg_k\":%.17g,"
               "\"h_j_per_kg\":%.17g,\"s_j_per_kg_k\":%.17g,\"mole_fractions\":{",
               gas->temperature_k, gas->pressure_pa, gas->molar_mass_kg_per_kmol,
               gas->gas_constant_j_per_kg_k, gas->cp_frozen_j_per_kg_k,
               gas->h_j_per_kg, gas->s_j_per_kg_k) < 0) { return 0; }
    for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
        if (printf("%s\"%s\":%.17g", i == 0U ? "" : ",", rp_cho_species_id(i), gas->mole_fractions[i]) < 0) { return 0; }
    }
    return fputs("}}", stdout) >= 0;
}

static int write_station(const RpFrozenFlowStation *station)
{
    return fputs("{\"gas\":", stdout) >= 0 && write_mixture(&station->gas) &&
        printf(",\"velocity_m_per_s\":%.17g,\"mach\":%.17g,\"mass_flux_kg_per_m2_s\":%.17g,"
               "\"energy_residual_j_per_kg\":%.17g,\"entropy_residual_j_per_kg_k\":%.17g}",
               station->velocity_m_per_s, station->mach, station->mass_flux_kg_per_m2_s,
               station->energy_residual_j_per_kg, station->entropy_residual_j_per_kg_k) >= 0;
}

static int combustion_main(int count, char **arguments)
{
    double values[8] = {0};
    const char *mode = count > 0 ? arguments[0] : "";
    const int tp = strcmp(mode, "tp") == 0;
    const int hp = strcmp(mode, "hp") == 0;
    const int frozen = strcmp(mode, "frozen") == 0;
    const int fixed_tp = strcmp(mode, "frozen-tp") == 0;
    const int hp_h = strcmp(mode, "hp-h") == 0;
    const int fixed_h = strcmp(mode, "frozen-h") == 0;
    const int explicit_h = hp_h || fixed_h;
    const int fixed = fixed_tp || fixed_h;
    const int assigned_tp = tp || fixed_tp;
    RpCh4O2Feed feed = {0};
    RpCh4O2EnthalpyFeed inlet = {0};
    double inlet_enthalpy = 0.0;
    RpCombustionResult result;
    RpFrozenNozzleResult nozzle;
    RpFrozenNozzleFixedResult geometry;
    RpError error;
    RpStatus status;
    int written;
    if ((!tp && !hp && !frozen && !fixed && !hp_h) ||
        count != (tp ? 6 : hp ? 5 : fixed_tp ? 9 : hp_h ? 7 : fixed_h ? 10 : 7)) { goto usage; }
    for (int i = explicit_h ? 3 : 1; i < count; ++i) {
        const char *next;
        if (!parse_decimal_token(arguments[i], &next, &values[i - (explicit_h ? 3 : 1)]) || *next != '\0') { goto usage; }
    }
    if (explicit_h) {
        inlet.pressure_pa = values[0]; inlet.oxidizer_fuel_mass_ratio = values[1];
        inlet.fuel_h_j_per_kg = values[2]; inlet.oxidizer_h_j_per_kg = values[3];
        /* Unknown phase/basis are rejected by the public C inlet contract. */
        inlet.phase = strcmp(arguments[2], "gas") == 0 ? RP_FEED_GAS : RP_FEED_LIQUID;
        inlet.basis = strcmp(arguments[1], "nasa9-cea-v3.3.4") == 0 ?
            RP_ENTHALPY_NASA9_CEA_V334 : RP_ENTHALPY_UNSPECIFIED;
        status = rp_ch4_o2_inlet_enthalpy(&inlet, &inlet_enthalpy, &error);
        if (status == RP_OK) { status = rp_ch4_o2_equilibrium_hp_enthalpy(&inlet, NULL, &result, &error); }
    } else {
        feed.pressure_pa = values[assigned_tp ? 1 : 0];
        feed.oxidizer_fuel_mass_ratio = values[assigned_tp ? 2 : 1];
        feed.fuel_temperature_k = values[assigned_tp ? 3 : 2];
        feed.oxidizer_temperature_k = values[assigned_tp ? 4 : 3];
        feed.phase = RP_FEED_GAS;
        status = assigned_tp ? rp_ch4_o2_equilibrium_tp(&feed, values[0], NULL, &result, &error) :
                      rp_ch4_o2_equilibrium_hp(&feed, NULL, &result, &error);
    }
    if (status == RP_OK && (frozen || fixed)) {
        RpFrozenNozzleInput input = {0};
        input.chamber_temperature_k = result.gas.temperature_k;
        input.chamber_pressure_pa = result.gas.pressure_pa;
        memcpy(input.mole_fractions, result.gas.mole_fractions, sizeof(input.mole_fractions));
        input.area_ratio = values[fixed_tp ? 5 : 4]; input.ambient_pressure_pa = values[fixed_tp ? 6 : 5];
        if (fixed) {
            status = rp_nozzle_solve_frozen_fixed_area(&input, values[fixed_tp ? 7 : 6], NULL, &geometry, &error);
            if (status == RP_OK) { nozzle = geometry.nozzle; }
        } else { status = rp_nozzle_solve_frozen(&input, NULL, &nozzle, &error); }
    }
    if (status != RP_OK) {
        (void)fprintf(stderr, "%s: %s\n", rp_status_name(status), error.message);
        return 4;
    }
    if (explicit_h) {
        written = printf("{\"schema_version\":1,\"model\":\"%s\",\"mode\":\"%s\",\"dataset_id\":\"%s\","
                         "\"inputs\":{\"feed_phase\":\"gas\",\"enthalpy_basis\":\"nasa9-cea-v3.3.4\","
                         "\"pressure_pa\":%.17g,\"oxidizer_fuel_mass_ratio\":%.17g,"
                         "\"fuel_h_j_per_kg\":%.17g,\"oxidizer_h_j_per_kg\":%.17g",
                         fixed_h ? "ch4_o2_hp_enthalpy_frozen_fixed_area_v1" : "ch4_o2_hp_enthalpy_v1",
                         mode, rp_thermo_dataset_id(), inlet.pressure_pa, inlet.oxidizer_fuel_mass_ratio,
                         inlet.fuel_h_j_per_kg, inlet.oxidizer_h_j_per_kg) >= 0;
    } else {
        written = printf("{\"schema_version\":1,\"model\":\"%s\",\"mode\":\"%s\",\"dataset_id\":\"%s\","
                     "\"inputs\":{\"feed_phase\":\"gas\",\"pressure_pa\":%.17g,\"oxidizer_fuel_mass_ratio\":%.17g,"
                     "\"fuel_temperature_k\":%.17g,\"oxidizer_temperature_k\":%.17g",
                     fixed ? "ch4_o2_tp_frozen_fixed_area_v1" : frozen ? "ch4_o2_chamber_frozen_v1" : "ch4_o2_gas_equilibrium_v1", mode, rp_thermo_dataset_id(),
                         feed.pressure_pa, feed.oxidizer_fuel_mass_ratio, feed.fuel_temperature_k, feed.oxidizer_temperature_k) >= 0;
    }
    if (written && assigned_tp) { written = printf(",\"temperature_k\":%.17g", values[0]) >= 0; }
    if (written && frozen) { written = printf(",\"area_ratio\":%.17g,\"ambient_pressure_pa\":%.17g", values[4], values[5]) >= 0; }
    if (written && fixed) { written = printf(",\"area_ratio\":%.17g,\"ambient_pressure_pa\":%.17g,\"throat_area_m2\":%.17g",
                                            values[fixed_tp ? 5 : 4], values[fixed_tp ? 6 : 5], values[fixed_tp ? 7 : 6]) >= 0; }
    written = written && fputs("}", stdout) >= 0;
    if (written && explicit_h) {
        written = printf(",\"boundary\":{\"inlet_mixture_h_j_per_kg\":%.17g,\"heat_transfer_j_per_kg\":0}",
                         inlet_enthalpy) >= 0;
    }
    written = written && fputs(",\"chamber\":", stdout) >= 0 && write_mixture(&result.gas) &&
        printf(",\"diagnostics\":{\"element_relative_residual\":[%.17g,%.17g,%.17g],\"equilibrium_residual\":%.17g,"
               "\"enthalpy_residual_j_per_kg\":%.17g,\"equilibrium_iterations\":%u,\"hp_iterations\":%u}",
               result.element_relative_residual[0], result.element_relative_residual[1], result.element_relative_residual[2],
               result.equilibrium_residual, result.enthalpy_residual_j_per_kg,
               result.equilibrium_iterations, result.hp_iterations) >= 0;
    if (written && (frozen || fixed)) {
        written = fputs(",\"nozzle\":{\"freeze_location\":\"chamber\",\"throat\":", stdout) >= 0 &&
            write_station(&nozzle.throat) && fputs(",\"exit\":", stdout) >= 0 && write_station(&nozzle.exit) &&
            printf(",\"cstar_m_per_s\":%.17g,\"vacuum_effective_velocity_m_per_s\":%.17g,"
                   "\"effective_velocity_m_per_s\":%.17g,\"thrust_coefficient\":%.17g,"
                   "\"continuity_relative_residual\":%.17g,\"sonic_relative_residual\":%.17g}",
                   nozzle.cstar_m_per_s, nozzle.vacuum_effective_velocity_m_per_s,
                   nozzle.effective_velocity_m_per_s, nozzle.thrust_coefficient,
                   nozzle.continuity_relative_residual, nozzle.sonic_relative_residual) >= 0;
    }
    if (written && fixed) {
        written = printf(",\"geometry\":{\"throat_area_m2\":%.17g,\"exit_area_m2\":%.17g,"
                         "\"mass_flow_kg_per_s\":%.17g,\"thrust_n\":%.17g,\"specific_impulse_s\":%.17g}",
                         geometry.throat_area_m2, geometry.exit_area_m2, geometry.mass_flow_kg_per_s,
                         geometry.thrust_n, geometry.specific_impulse_s) >= 0;
    }
    written = written && fputs(",\"limitations\":[\"Restricted nine-species ideal gas; no ions, condensed phases or soot.\","
                               "\"Gas-feed method calculation, not flight engine performance.\","
                               "\"Frozen nozzle is chamber-frozen, inviscid and without shocks or separation.\"", stdout) >= 0;
    if (written && fixed) {
        written = fputs(",\"Fixed-area performance is single-nozzle only, not feed-system or full-cycle closure.\"", stdout) >= 0;
    }
    if (written && explicit_h) {
        written = fputs(",\"Inlet basis is caller-declared; no liquid properties, inlet kinetic energy or shaft work.\"", stdout) >= 0;
    }
    written = written && fputs("]}\n", stdout) >= 0;
    if (!written || fflush(stdout) != 0) {
        (void)fputs("io_error: Cannot write combustion JSON report.\n", stderr); return 3;
    }
    return 0;
usage:
    (void)fputs("Usage (gas feed, SI): rocketperf combustion tp T_K P_PA OF TF_K TO_K\n"
                "                     rocketperf combustion hp P_PA OF TF_K TO_K\n"
                "                     rocketperf combustion frozen P_PA OF TF_K TO_K AREA_RATIO AMBIENT_PA\n"
                "                     rocketperf combustion frozen-tp T_K P_PA OF TF_K TO_K AREA_RATIO AMBIENT_PA THROAT_M2\n"
                "                     rocketperf combustion hp-h nasa9-cea-v3.3.4 gas P_PA OF HF_JKG HO_JKG\n"
                "                     rocketperf combustion frozen-h nasa9-cea-v3.3.4 gas P_PA OF HF_JKG HO_JKG AREA_RATIO AMBIENT_PA THROAT_M2\n", stderr);
    return 2;
}

static int cli_main(int argc, char **argv)
{
    RpCase study;
    RpNozzleResult result;
    RpError error = {0};
    RpStatus status;
    (void)setlocale(LC_NUMERIC, "C");
    if (argc == 2 && strcmp(argv[1], "--version") == 0) {
        (void)printf("rocketperf %s\n", RP_VERSION);
        return 0;
    }
    if (argc == 2 && strcmp(argv[1], "--help") == 0) {
        (void)puts("       rocketperf cycle prescribed CASE.ini (prescribed thermal states, no return)");
        (void)puts("       rocketperf combustion tp T_K P_PA OF TF_K TO_K (gas feed)");
        (void)puts("       rocketperf combustion hp P_PA OF TF_K TO_K (gas feed)");
        (void)puts("       rocketperf combustion frozen P_PA OF TF_K TO_K AREA_RATIO AMBIENT_PA");
        (void)puts("       rocketperf combustion frozen-tp T_K P_PA OF TF_K TO_K AREA_RATIO AMBIENT_PA THROAT_M2");
        (void)puts("       rocketperf combustion hp-h nasa9-cea-v3.3.4 gas P_PA OF HF_JKG HO_JKG");
        (void)puts("       rocketperf combustion frozen-h nasa9-cea-v3.3.4 gas P_PA OF HF_JKG HO_JKG AREA_RATIO AMBIENT_PA THROAT_M2");
        (void)puts("       rocketperf thermo SPECIES TEMPERATURE_K (p_ref=100000 Pa, no equilibrium)");
        (void)puts("       rocketperf study prescribed-cycle CASE.ini FIELD CSV (finite-step study, not engine optimization)");
        (void)puts("Usage: rocketperf run CASE.ini\n       rocketperf study area-ratio-ambient CASE.ini [--area-ratios CSV] [--ambient-pressures CSV]\n       rocketperf --version\nThe L0 model accepts synthetic benchmarks/research scenarios, not verified engine datasets.");
        return 0;
    }
    if (argc == 4 && strcmp(argv[1], "thermo") == 0) {
        return thermo_main(argv[2], argv[3]);
    }
    if (argc >= 2 && strcmp(argv[1], "combustion") == 0) {
        return combustion_main(argc - 2, &argv[2]);
    }
    if (argc >= 2 && strcmp(argv[1], "cycle") == 0) {
        if (argc != 4 || strcmp(argv[2], "prescribed") != 0) {
            (void)fputs("Usage: rocketperf cycle prescribed CASE.ini\n", stderr); return 2;
        }
        status = rp_cycle_case_run(argv[3], stdout, &error);
        if (status == RP_OK && fflush(stdout) != 0) { status = rp_error_set(&error, RP_IO_ERROR, "Cannot flush cycle report."); }
        if (status != RP_OK) {
            (void)fprintf(stderr, "%s: %s\n", rp_status_name(status), error.message);
            return status == RP_PARSE_ERROR || status == RP_IO_ERROR ? 3 : 4;
        }
        return 0;
    }
    if (argc >= 4 && strcmp(argv[1], "study") == 0 && strcmp(argv[2], "area-ratio-ambient") == 0) {
        return study_main(argv[3], argc - 4, &argv[4]);
    }
    if (argc >= 3 && strcmp(argv[1], "study") == 0 && strcmp(argv[2], "prescribed-cycle") == 0) {
        if (argc != 6) { (void)fputs("Usage: rocketperf study prescribed-cycle CASE.ini FIELD CSV\n", stderr); return 2; }
        return cycle_study_main(argv[3], argv[4], argv[5]);
    }
    if (argc != 3 || strcmp(argv[1], "run") != 0) {
        (void)fputs("Usage: rocketperf run CASE.ini (or --help / --version)\n", stderr);
        return 2;
    }
    status = rp_case_load(argv[2], &study, &error);
    if (status == RP_OK) { status = rp_nozzle_solve_ideal(&study.input, NULL, &result, &error); }
    if (status == RP_OK) { status = rp_case_write_json(stdout, &study, &result, &error); }
    if (status == RP_OK && fflush(stdout) != 0) {
        status = rp_error_set(&error, RP_IO_ERROR, "Cannot flush JSON report.");
    }
    if (status != RP_OK) {
        (void)fprintf(stderr, "%s: %s\n", rp_status_name(status), error.message);
        return status == RP_PARSE_ERROR || status == RP_IO_ERROR ? 3 : 4;
    }
    return 0;
}

#ifdef _WIN32
#include <windows.h>
#include <stdlib.h>

int wmain(int argc, wchar_t **wide_argv);
int wmain(int argc, wchar_t **wide_argv)
{
    char **argv = calloc((size_t)argc + 1U, sizeof(*argv));
    int code = 3;
    if (argv == NULL) { (void)fputs("io_error: Cannot allocate arguments.\n", stderr); return code; }
    for (int i = 0; i < argc; ++i) {
        const int size = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, wide_argv[i], -1, NULL, 0, NULL, NULL);
        if (size <= 0 || (argv[i] = malloc((size_t)size)) == NULL ||
            WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, wide_argv[i], -1, argv[i], size, NULL, NULL) == 0) {
            (void)fputs("io_error: Cannot encode arguments as UTF-8.\n", stderr);
            goto cleanup;
        }
    }
    code = cli_main(argc, argv);
cleanup:
    for (int i = 0; i < argc; ++i) { free(argv[i]); }
    free(argv);
    return code;
}
#else
int main(int argc, char **argv)
{
    return cli_main(argc, argv);
}
#endif
