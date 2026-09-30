#include "case_file.h"
#include "rocketperf/version.h"

static void quoted(FILE *stream, const char *text)
{
    (void)fputc('"', stream);
    for (const char *p = text; *p != '\0'; ++p) {
        if (*p == '"' || *p == '\\') { (void)fputc('\\', stream); }
        (void)fputc((unsigned char)*p, stream);
    }
    (void)fputc('"', stream);
}

RpStatus rp_case_write_json(FILE *stream, const RpCase *study,
                            const RpNozzleResult *result, RpError *error)
{
    if (stream == NULL || study == NULL || result == NULL) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Report stream, case and result are required.");
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
