#include "case_file.h"
#include "rocketperf/version.h"
#include "rocketperf/numeric.h"

#include <stddef.h>
#include <stdint.h>
#include <math.h>
#include <string.h>

static int bounded_text(const char *text, size_t capacity)
{
    return text[0] != '\0' && memchr(text, '\0', capacity) != NULL;
}

static int valid_case(const RpCase *study)
{
    const RpNozzleInput *v = &study->input;
    return bounded_text(study->id, sizeof(study->id)) &&
           bounded_text(study->kind, sizeof(study->kind)) &&
           bounded_text(study->source_ref, sizeof(study->source_ref)) &&
           (strcmp(study->kind, "synthetic_benchmark") == 0 || strcmp(study->kind, "research_scenario") == 0) &&
           rp_isfinite(v->gamma) && v->gamma > 1.0 && v->gamma <= 2.0 &&
           rp_isfinite(v->gas_constant_j_kg_k) && v->gas_constant_j_kg_k > 0.0 &&
           rp_isfinite(v->stagnation_temperature_k) && v->stagnation_temperature_k > 0.0 &&
           rp_isfinite(v->stagnation_pressure_pa) && v->stagnation_pressure_pa > 0.0 &&
           rp_isfinite(v->throat_area_m2) && v->throat_area_m2 > 0.0 &&
           rp_isfinite(v->area_ratio) && v->area_ratio >= 1.0 && v->area_ratio <= 1e4 &&
           rp_isfinite(v->ambient_pressure_pa) && v->ambient_pressure_pa >= 0.0;
}

static int valid_result(const RpNozzleResult *v)
{
    const double values[] = {v->exit_mach, v->exit_temperature_k, v->exit_pressure_pa,
        v->exit_velocity_m_s, v->exit_area_m2, v->characteristic_velocity_m_s,
        v->mass_flow_kg_s, v->thrust_n, v->thrust_coefficient, v->specific_impulse_s};
    for (size_t i = 0U; i < sizeof(values) / sizeof(values[0]); ++i) {
        if (!rp_isfinite(values[i]) || values[i] <= 0.0) { return 0; }
    }
    return v->exit_mach >= 1.0 && v->root_iterations <= 100000U &&
           rp_isfinite(v->relative_area_residual) && v->relative_area_residual >= 0.0 &&
           v->relative_area_residual <= 1e-8;
}

static void quoted(FILE *stream, const char *text)
{
    (void)fputc('"', stream);
    for (const char *p = text; *p != '\0'; ++p) {
        const unsigned char c = (unsigned char)*p;
        if (c < 0x20U) { (void)fprintf(stream, "\\u%04x", (unsigned int)c); }
        else {
            if (*p == '"' || *p == '\\') { (void)fputc('\\', stream); }
            (void)fputc(c, stream);
        }
    }
    (void)fputc('"', stream);
}

static void write_input_fields(FILE *stream, const RpNozzleInput *input, int include_area_ambient)
{
    (void)fprintf(stream, "    \"gamma\": %.17g,\n    \"gas_constant_j_kg_k\": %.17g,\n    \"stagnation_temperature_k\": %.17g,\n    \"stagnation_pressure_pa\": %.17g,\n    \"throat_area_m2\": %.17g",
                  input->gamma, input->gas_constant_j_kg_k,
                  input->stagnation_temperature_k, input->stagnation_pressure_pa,
                  input->throat_area_m2);
    if (include_area_ambient) {
        (void)fprintf(stream, ",\n    \"area_ratio\": %.17g,\n    \"ambient_pressure_pa\": %.17g",
                      input->area_ratio, input->ambient_pressure_pa);
    }
    (void)fputc('\n', stream);
}

static void write_result_fields(FILE *stream, const RpNozzleResult *result)
{
    (void)fprintf(stream, "      \"exit_mach\": %.17g,\n      \"exit_temperature_k\": %.17g,\n      \"exit_pressure_pa\": %.17g,\n      \"exit_velocity_m_s\": %.17g,\n      \"exit_area_m2\": %.17g,\n      \"characteristic_velocity_m_s\": %.17g,\n      \"mass_flow_kg_s\": %.17g,\n      \"thrust_n\": %.17g,\n      \"thrust_coefficient\": %.17g,\n      \"specific_impulse_s\": %.17g\n",
                  result->exit_mach, result->exit_temperature_k, result->exit_pressure_pa,
                  result->exit_velocity_m_s, result->exit_area_m2, result->characteristic_velocity_m_s,
                  result->mass_flow_kg_s, result->thrust_n, result->thrust_coefficient,
                  result->specific_impulse_s);
}

RpStatus rp_case_write_json(FILE *stream, const RpCase *study,
                            const RpNozzleResult *result, RpError *error)
{
    if (stream == NULL || study == NULL || result == NULL) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Report stream, case and result are required.");
    }
    if (!valid_case(study) || !valid_result(result)) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Report metadata, input or result is invalid.");
    }
    (void)fprintf(stream, "{\n  \"schema_version\": 1,\n  \"program_version\": \"%s\",\n  \"model\": \"%s\",\n  \"case\": {\"id\": ", RP_VERSION, RP_IDEAL_NOZZLE_MODEL);
    quoted(stream, study->id);
    (void)fputs(", \"kind\": ", stream);
    quoted(stream, study->kind);
    (void)fputs(", \"source_ref\": ", stream);
    quoted(stream, study->source_ref);
    (void)fputs("},\n  \"inputs\": {\n", stream);
    (void)fprintf(stream, "    \"gamma\": %.17g,\n    \"gas_constant_j_kg_k\": %.17g,\n    \"stagnation_temperature_k\": %.17g,\n    \"stagnation_pressure_pa\": %.17g,\n    \"area_ratio\": %.17g,\n    \"throat_area_m2\": %.17g,\n    \"ambient_pressure_pa\": %.17g\n  },\n",
                  study->input.gamma, study->input.gas_constant_j_kg_k,
                  study->input.stagnation_temperature_k, study->input.stagnation_pressure_pa,
                  study->input.area_ratio, study->input.throat_area_m2, study->input.ambient_pressure_pa);
    (void)fputs("  \"results\": {\n", stream);
    (void)fprintf(stream, "    \"exit_mach\": %.17g,\n    \"exit_temperature_k\": %.17g,\n    \"exit_pressure_pa\": %.17g,\n    \"exit_velocity_m_s\": %.17g,\n    \"exit_area_m2\": %.17g,\n    \"characteristic_velocity_m_s\": %.17g,\n    \"mass_flow_kg_s\": %.17g,\n    \"thrust_n\": %.17g,\n    \"thrust_coefficient\": %.17g,\n    \"specific_impulse_s\": %.17g\n  },\n",
                  result->exit_mach, result->exit_temperature_k, result->exit_pressure_pa,
                  result->exit_velocity_m_s, result->exit_area_m2, result->characteristic_velocity_m_s,
                  result->mass_flow_kg_s, result->thrust_n, result->thrust_coefficient, result->specific_impulse_s);
    (void)fprintf(stream, "  \"diagnostics\": {\"root_iterations\": %u, \"relative_area_residual\": %.17g},\n",
                  result->root_iterations, result->relative_area_residual);
    (void)fputs("  \"limitations\": [\"ideal constant-gamma gas\", \"steady one-dimensional choked flow\", \"matched or underexpanded only\", \"no chemistry, losses, cycle, cooling, separation or reuse prediction\"]\n}\n", stream);
    if (ferror(stream)) { return rp_error_set(error, RP_IO_ERROR, "Cannot write JSON report."); }
    rp_error_clear(error);
    return RP_OK;
}

RpStatus rp_case_write_study_json(FILE *stream, const RpCase *study,
                                  const RpNozzleStudyGrid *grid,
                                  const RpNozzleStudyPoint *points,
                                  size_t point_count, RpError *error)
{
    if (stream == NULL || study == NULL || grid == NULL || points == NULL ||
        grid->area_ratios == NULL || grid->ambient_pressures_pa == NULL ||
        grid->area_ratio_count == 0U || grid->ambient_pressure_count == 0U || point_count == 0U) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Study report, case, grid and points are required.");
    }
    if (grid->area_ratio_count > SIZE_MAX / grid->ambient_pressure_count ||
        point_count != grid->area_ratio_count * grid->ambient_pressure_count) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Study report point count does not match the Cartesian grid.");
    }
    if (!valid_case(study)) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Study report metadata or input is invalid.");
    }
    for (size_t i = 0U; i < grid->area_ratio_count; ++i) {
        if (!rp_isfinite(grid->area_ratios[i]) || grid->area_ratios[i] < 1.0 || grid->area_ratios[i] > 1e4) {
            return rp_error_set(error, RP_INVALID_ARGUMENT, "Study report has an invalid area-ratio grid.");
        }
    }
    for (size_t j = 0U; j < grid->ambient_pressure_count; ++j) {
        if (!rp_isfinite(grid->ambient_pressures_pa[j]) || grid->ambient_pressures_pa[j] < 0.0) {
            return rp_error_set(error, RP_INVALID_ARGUMENT, "Study report has an invalid pressure grid.");
        }
    }
    for (size_t i = 0U; i < point_count; ++i) {
        if (points[i].status < RP_OK || points[i].status > RP_PARSE_ERROR ||
            points[i].area_ratio != grid->area_ratios[i / grid->ambient_pressure_count] ||
            points[i].ambient_pressure_pa != grid->ambient_pressures_pa[i % grid->ambient_pressure_count] ||
            (points[i].status == RP_OK && !valid_result(&points[i].result)) ||
            (points[i].status != RP_OK && !bounded_text(points[i].message, sizeof(points[i].message)))) {
            return rp_error_set(error, RP_INVALID_ARGUMENT, "Study report contains an invalid point status or diagnostic.");
        }
    }
    (void)fprintf(stream, "{\n  \"schema_version\": 1,\n  \"program_version\": \"%s\",\n  \"study\": {\"id\": \"S1_area_ratio_ambient\", \"model\": \"%s\", \"case_id\": ", RP_VERSION, RP_IDEAL_NOZZLE_MODEL);
    quoted(stream, study->id);
    (void)fputs(", \"kind\": ", stream);
    quoted(stream, study->kind);
    (void)fputs(", \"source_ref\": ", stream);
    quoted(stream, study->source_ref);
    (void)fputs("},\n  \"base_inputs\": {\n", stream);
    write_input_fields(stream, &study->input, 0);
    (void)fputs("  },\n  \"grid\": {\n    \"area_ratios\": [", stream);
    for (size_t i = 0U; i < grid->area_ratio_count; ++i) {
        if (i != 0U) { (void)fputs(", ", stream); }
        (void)fprintf(stream, "%.17g", grid->area_ratios[i]);
    }
    (void)fputs("],\n    \"ambient_pressures_pa\": [", stream);
    for (size_t j = 0U; j < grid->ambient_pressure_count; ++j) {
        if (j != 0U) { (void)fputs(", ", stream); }
        (void)fprintf(stream, "%.17g", grid->ambient_pressures_pa[j]);
    }
    (void)fputs("],\n    \"ordering\": \"area_ratio_outer_ambient_pressure_inner\"\n  },\n  \"points\": [\n", stream);
    for (size_t i = 0U; i < point_count; ++i) {
        const RpNozzleStudyPoint *point = &points[i];
        if (i != 0U) { (void)fputs(",\n", stream); }
        (void)fprintf(stream, "    {\"area_ratio\": %.17g, \"ambient_pressure_pa\": %.17g, \"status\": \"%s\"",
                      point->area_ratio, point->ambient_pressure_pa, rp_status_name(point->status));
        if (point->status == RP_OK) {
            (void)fputs(", \"results\": {\n", stream);
            write_result_fields(stream, &point->result);
            (void)fprintf(stream, "    }, \"diagnostics\": {\"root_iterations\": %u, \"relative_area_residual\": %.17g}",
                          point->result.root_iterations, point->result.relative_area_residual);
        } else {
            (void)fputs(", \"error\": ", stream);
            quoted(stream, point->message);
        }
        (void)fputc('}', stream);
    }
    (void)fputs("\n  ],\n  \"limitations\": [\"L0 ideal constant-gamma gas\", \"steady one-dimensional choked flow\", \"each point reports matched/underexpanded domain status\", \"no chemistry, losses, cycle, cooling, separation or reuse prediction\", \"research scenario inputs are not verified engine data\"]\n}\n", stream);
    if (ferror(stream)) { return rp_error_set(error, RP_IO_ERROR, "Cannot write study JSON report."); }
    rp_error_clear(error);
    return RP_OK;
}
