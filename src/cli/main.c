#include "arguments.h"
#include "combustion_commands.h"
#include "combustion_report.h"
#include "case_file.h"
#include "cycle_case.h"
#include "propellant_case.h"
#include "rocketperf/numeric.h"
#include "rocketperf/version.h"
#include "rocketperf/thermo.h"
#include "rocketperf/combustion.h"
#include "rocketperf/frozen_nozzle.h"
#include "rocketperf/liquid_feed.h"
#include "rocketperf/liquid_nozzle.h"
#include "rocketperf/propellant_study.h"

#include <ctype.h>
#include <errno.h>
#include <locale.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RP_STUDY_GRID_LIMIT 32U

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
        if (!rp_cli_parse_decimal(cursor, &end, &value)) { return 0; }
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
    if (!rp_cli_parse_decimal(temperature_text, &next, &temperature) || *next != '\0') {
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

static int liquid_feed_main(int count, char **args)
{
    RpLiquidFeedQuery query;
    RpLiquidFeedState state;
    RpError error = {0};
    RpStatus status;
    const char *next;
    if (count != 5 ||
        !rp_cli_parse_decimal(args[3], &next, &query.temperature_k) || *next != '\0' ||
        !rp_cli_parse_decimal(args[4], &next, &query.pressure_pa) || *next != '\0') {
        (void)fputs("Usage: rocketperf liquid-feed DATASET Methane|Oxygen liquid T_K P_PA\n", stderr);
        return 2;
    }
    query.dataset_id = args[0];
    query.fluid_id = args[1];
    query.phase = strcmp(args[2], "liquid") == 0 ? RP_LIQUID_SINGLE_PHASE :
        strcmp(args[2], "two-phase") == 0 ? RP_LIQUID_TWO_PHASE : RP_LIQUID_GAS;
    status = rp_liquid_feed_evaluate(&query, &state, &error);
    if (status != RP_OK) {
        (void)fprintf(stderr, "%s: %s\n", rp_status_name(status), error.message);
        return 4;
    }
    if (printf(
        "{\"schema_version\":1,\"model\":\"single_phase_liquid_table_v1\",\"dataset_id\":\"%s\",\"status\":\"ok\","
        "\"inputs\":{\"fluid\":\"%s\",\"phase\":\"liquid\",\"temperature_k\":%.17g,\"pressure_pa\":%.17g},"
        "\"results\":{\"density_kg_per_m3\":%.17g,\"h_j_per_mol\":%.17g,\"h_j_per_kg\":%.17g,"
        "\"eos_molar_mass_kg_per_mol\":%.17g,\"chemical_molar_mass_kg_per_mol\":%.17g},"
        "\"provenance\":{\"reference_manifest_sha256\":\"%s\",\"enthalpy_basis\":\"heos710-cea334-ideal-zero-298.15-v1\","
        "\"density_mass_basis\":\"CoolProp7.1.0 EOS molar mass\",\"input_role\":\"assumed_research\"},"
        "\"limitations\":[\"Assumed pure CH4/O2 single-phase liquid reference, not measured engine inlet data.\","
        "\"Bilinear interpolation within the pinned rectangle; no flash, extrapolation, pump or cycle solve.\","
        "\"EOS density mass and CEA chemical enthalpy mass conventions are returned separately.\","
        "\"HEOS ideal cp differs from NASA9 after the single ideal-zero alignment.\"]}\n",
        rp_liquid_feed_dataset_id(), query.fluid_id, query.temperature_k, query.pressure_pa,
        state.density_kg_per_m3, state.h_j_per_mol, state.h_j_per_kg,
        state.eos_molar_mass_kg_per_mol, state.chemical_molar_mass_kg_per_mol,
        rp_liquid_feed_reference_sha256()) < 0 || fflush(stdout) != 0) {
        (void)fputs("io_error: Cannot write liquid feed JSON report.\n", stderr);
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
        (void)puts("       rocketperf combustion hp-liquid cea-v3.3.4-ch4l-o2l-assigned-v1 liquid CH4(L) O2(L) P_PA OF 111.643 90.170");
        (void)puts("       rocketperf combustion frozen-liquid cea-v3.3.4-ch4l-o2l-assigned-v1 liquid CH4(L) O2(L) P_PA OF 111.643 90.170 AREA_RATIO AMBIENT_PA THROAT_M2");
        (void)puts("       rocketperf combustion hp-liquid-state DATASET BASIS liquid TF_K PF_PA TO_K PO_PA PC_PA OF");
        (void)puts("       rocketperf combustion frozen-liquid-state DATASET BASIS liquid TF_K PF_PA TO_K PO_PA PC_PA OF AREA_RATIO AMBIENT_PA THROAT_M2");
        (void)puts("       rocketperf thermo SPECIES TEMPERATURE_K (p_ref=100000 Pa, no equilibrium)");
        (void)puts("       rocketperf liquid-feed coolprop710-cea334-liquid-molar-v1 Methane|Oxygen liquid T_K P_PA (reference table)");
        (void)puts("       rocketperf study prescribed-cycle CASE.ini FIELD CSV (finite-step study, not engine optimization)");
        (void)puts("       rocketperf study propellants CH4_OF RP1_OF AREA_RATIO AMBIENT_PA (Pc=10MPa, At=0.01m2, fixed declared inlets)");
        (void)puts("       rocketperf study propellants --case CASE.ini");
        (void)puts("       rocketperf combustion hp-rp1 cea-v3.3.4-rp1-o2l-assigned-v1 liquid RP-1 O2(L) 10000000 OF 298.15 90.170");
        (void)puts("       rocketperf combustion frozen-rp1 cea-v3.3.4-rp1-o2l-assigned-v1 liquid RP-1 O2(L) 10000000 OF 298.15 90.170 AREA_RATIO AMBIENT_PA THROAT_M2");
        (void)puts("Usage: rocketperf run CASE.ini\n       rocketperf study area-ratio-ambient CASE.ini [--area-ratios CSV] [--ambient-pressures CSV]\n       rocketperf --version\nThe L0 model accepts synthetic benchmarks/research scenarios, not verified engine datasets.");
        return 0;
    }
    if (argc == 4 && strcmp(argv[1], "thermo") == 0) {
        return thermo_main(argv[2], argv[3]);
    }
    if (argc >= 2 && strcmp(argv[1], "liquid-feed") == 0) {
        return liquid_feed_main(argc - 2, &argv[2]);
    }
    if (argc >= 2 && strcmp(argv[1], "combustion") == 0) {
        return rp_cli_combustion(argc - 2, &argv[2]);
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
    if (argc >= 3 && strcmp(argv[1], "study") == 0 && strcmp(argv[2], "propellants") == 0) {
        if (argc >= 4 && strcmp(argv[3], "--case") == 0) {
            if (argc != 5) {
                (void)fputs("Usage: rocketperf study propellants --case CASE.ini\n", stderr);
                return 2;
            }
            return rp_cli_propellant_case(argv[4]);
        }
        return rp_cli_propellants(argc - 3, &argv[3]);
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
