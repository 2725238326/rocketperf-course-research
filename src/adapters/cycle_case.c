#include "cycle_case.h"
#include "case_file.h"
#include "case_text.h"
#include "rocketperf/version.h"

#include <stddef.h>
#include <string.h>

typedef struct { const char *name; size_t offset; } CycleField;
#define FIELD(member) {#member, offsetof(RpCycleInput, member)}
#define PUMP(name, member) {#name "_" #member, offsetof(RpCycleInput, name) + offsetof(RpLiquidPumpInput, member)}
static const CycleField fields[] = {
    FIELD(total_mass_flow_kg_per_s), FIELD(overall_oxidizer_fuel_ratio),
    PUMP(fuel_pump, density_kg_per_m3), PUMP(fuel_pump, inlet_pressure_pa),
    PUMP(fuel_pump, outlet_pressure_pa), PUMP(fuel_pump, efficiency), PUMP(fuel_pump, inlet_h_j_per_kg),
    PUMP(oxidizer_pump, density_kg_per_m3), PUMP(oxidizer_pump, inlet_pressure_pa),
    PUMP(oxidizer_pump, outlet_pressure_pa), PUMP(oxidizer_pump, efficiency), PUMP(oxidizer_pump, inlet_h_j_per_kg),
    FIELD(chamber_pressure_pa), FIELD(chamber_temperature_k), FIELD(main_area_ratio),
    FIELD(generator_oxidizer_fuel_ratio), FIELD(generator_temperature_k),
    FIELD(turbine_inlet_pressure_pa), FIELD(turbine_outlet_pressure_pa), FIELD(turbine_efficiency),
    FIELD(shaft_efficiency), FIELD(auxiliary_power_w), FIELD(maximum_branch_fraction),
    FIELD(return_fraction), FIELD(return_pressure_drop_pa), FIELD(branch_area_ratio),
    FIELD(branch_axial_projection), FIELD(ambient_pressure_pa)
};
#undef FIELD
#undef PUMP
static const char *const metadata[] = {"schema_version", "case_id", "case_kind", "source_ref", "model"};
#define FIELD_COUNT (sizeof(fields) / sizeof(fields[0]))
#define META_COUNT (sizeof(metadata) / sizeof(metadata[0]))

static RpStatus assign_metadata(RpCycleCase *study, size_t field, const char *value,
                                 unsigned int line, RpError *error)
{
    switch (field) {
    case 0U:
        if (strcmp(value, "1") != 0) { return rp_text_parse_failure(error, line, "Unsupported schema_version."); }
        break;
    case 1U:
        if (!rp_text_identifier(value)) { return rp_text_parse_failure(error, line, "Invalid lowercase ASCII case_id."); }
        (void)snprintf(study->id, sizeof(study->id), "%s", value); break;
    case 2U:
        if (strcmp(value, "synthetic_benchmark") != 0 && strcmp(value, "research_scenario") != 0) {
            return rp_text_parse_failure(error, line, "Only synthetic_benchmark or research_scenario is supported.");
        }
        (void)snprintf(study->kind, sizeof(study->kind), "%s", value); break;
    case 3U:
        if (!rp_text_ascii(value, sizeof(study->source_ref))) { return rp_text_parse_failure(error, line, "Invalid printable ASCII source_ref."); }
        (void)snprintf(study->source_ref, sizeof(study->source_ref), "%s", value); break;
    case 4U:
        if (strcmp(value, RP_PRESCRIBED_CYCLE_MODEL) != 0) { return rp_text_parse_failure(error, line, "Unsupported cycle model."); }
        break;
    default: return rp_text_parse_failure(error, line, "Internal metadata mapping error.");
    }
    return RP_OK;
}
RpStatus rp_cycle_case_load(const char *utf8_path, RpCycleCase *output, RpError *error)
{
    RpCycleCase study = {0};
    unsigned char seen[FIELD_COUNT + META_COUNT] = {0};
    char buffer[512];
    unsigned int line = 0U;
    int line_status;
    RpStatus status = RP_OK;
    FILE *file;
    if (utf8_path == NULL || output == NULL) { return rp_error_set(error, RP_INVALID_ARGUMENT, "Cycle path and output are required."); }
    file = rp_fopen_utf8_read(utf8_path);
    if (file == NULL) { return rp_error_set(error, RP_IO_ERROR, "Cannot open cycle case file."); }
    while ((line_status = rp_text_read_line(file, buffer, sizeof(buffer))) != 0) {
        char *text, *separator, *key, *value;
        size_t field, numeric;
        ++line;
        if (line > 128U || line_status < 0) { status = rp_text_parse_failure(error, line, "Line limits or embedded NUL."); break; }
        if (line == 1U && strlen(buffer) >= 3U && memcmp(buffer, "\xEF\xBB\xBF", 3U) == 0) {
            memmove(buffer, buffer + 3, strlen(buffer) - 2U);
        }
        text = rp_text_trim(buffer);
        if (*text == '\0' || *text == '#') { continue; }
        separator = strchr(text, '=');
        if (separator == NULL) { status = rp_text_parse_failure(error, line, "Expected key=value."); break; }
        *separator = '\0'; key = rp_text_trim(text); value = rp_text_trim(separator + 1);
        for (field = 0U; field < META_COUNT; ++field) { if (strcmp(key, metadata[field]) == 0) { break; } }
        if (field == META_COUNT) {
            for (numeric = 0U; numeric < FIELD_COUNT; ++numeric) { if (strcmp(key, fields[numeric].name) == 0) { break; } }
            field += numeric;
        }
        if (field == META_COUNT + FIELD_COUNT) { status = rp_text_parse_failure(error, line, "Unknown field."); break; }
        if (seen[field] != 0U) { status = rp_text_parse_failure(error, line, "Duplicate field."); break; }
        if (field < META_COUNT) { status = assign_metadata(&study, field, value, line, error); }
        else {
            double number;
            if (!rp_text_decimal(value, &number)) { status = rp_text_parse_failure(error, line, "Expected finite decimal SI value."); }
            else { memcpy((unsigned char *)&study.input + fields[field - META_COUNT].offset, &number, sizeof(number)); }
        }
        if (status != RP_OK) { break; }
        seen[field] = 1U;
    }
    if (status == RP_OK && ferror(file)) { status = rp_error_set(error, RP_IO_ERROR, "Cannot read cycle case file."); }
    if (fclose(file) != 0 && status == RP_OK) { status = rp_error_set(error, RP_IO_ERROR, "Cannot close cycle case file."); }
    if (status != RP_OK) { return status; }
    for (size_t field = 0U; field < META_COUNT + FIELD_COUNT; ++field) {
        if (!seen[field]) { return rp_text_parse_failure(error, line, "Missing required field(s)."); }
    }
    *output = study; rp_error_clear(error); return RP_OK;
}
static int write_string(FILE *stream, const char *value)
{
    if (fputc('"', stream) == EOF) { return 0; }
    for (const char *p = value; *p != '\0'; ++p) {
        if ((*p == '"' || *p == '\\') && fputc('\\', stream) == EOF) { return 0; }
        if (fputc((unsigned char)*p, stream) == EOF) { return 0; }
    }
    return fputc('"', stream) != EOF;
}
static int write_gas(FILE *stream, const RpGasMixture *gas)
{
    if (fprintf(stream, "{\"temperature_k\":%.17g,\"pressure_pa\":%.17g,\"h_j_per_kg\":%.17g,"
                        "\"s_j_per_kg_k\":%.17g,\"cp_frozen_j_per_kg_k\":%.17g,\"mole_fractions\":{",
                gas->temperature_k, gas->pressure_pa, gas->h_j_per_kg, gas->s_j_per_kg_k, gas->cp_frozen_j_per_kg_k) < 0) { return 0; }
    for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
        if (fprintf(stream, "%s\"%s\":%.17g", i == 0U ? "" : ",", rp_cho_species_id(i), gas->mole_fractions[i]) < 0) { return 0; }
    }
    return fputs("}}", stream) >= 0;
}
static int write_pump(FILE *stream, const RpLiquidPumpResult *pump)
{
    return fprintf(stream, "{\"specific_work_j_per_kg\":%.17g,\"shaft_power_w\":%.17g,"
                           "\"outlet_h_j_per_kg\":%.17g,\"energy_residual_w\":%.17g}",
        pump->specific_work_j_per_kg, pump->shaft_power_w, pump->outlet_h_j_per_kg, pump->energy_residual_w) >= 0;
}
static int write_station(FILE *stream, const RpFrozenFlowStation *station)
{
    return fputs("{\"gas\":", stream) >= 0 && write_gas(stream, &station->gas) &&
        fprintf(stream, ",\"velocity_m_per_s\":%.17g,\"mass_flux_kg_per_m2_s\":%.17g,\"mach\":%.17g,"
                        "\"energy_residual_j_per_kg\":%.17g,\"entropy_residual_j_per_kg_k\":%.17g}",
            station->velocity_m_per_s, station->mass_flux_kg_per_m2_s, station->mach,
            station->energy_residual_j_per_kg, station->entropy_residual_j_per_kg_k) >= 0;
}
static int write_nozzle(FILE *stream, const RpFrozenNozzleResult *nozzle)
{
    return fputs("{\"chamber\":", stream) >= 0 && write_gas(stream, &nozzle->chamber) &&
        fputs(",\"throat\":", stream) >= 0 && write_station(stream, &nozzle->throat) &&
        fputs(",\"exit\":", stream) >= 0 && write_station(stream, &nozzle->exit) &&
        fprintf(stream, ",\"effective_velocity_m_per_s\":%.17g,\"cstar_m_per_s\":%.17g,"
                        "\"continuity_relative_residual\":%.17g,\"sonic_relative_residual\":%.17g}",
            nozzle->effective_velocity_m_per_s, nozzle->cstar_m_per_s,
            nozzle->continuity_relative_residual, nozzle->sonic_relative_residual) >= 0;
}
static int write_report(FILE *stream, const RpCycleCase *study, const RpCycleResult *result)
{
    if (fprintf(stream, "{\"schema_version\":1,\"program_version\":\"%s\",\"model\":\"%s\",\"dataset_id\":\"%s\","
                        "\"boundary\":\"pump_inlets_to_two_nozzle_exits_auxiliary_shaft_and_mechanical_heat\",\"case\":{\"id\":",
        RP_VERSION, RP_PRESCRIBED_CYCLE_MODEL, rp_thermo_dataset_id()) < 0 || !write_string(stream, study->id) ||
        fputs(",\"kind\":", stream) < 0 || !write_string(stream, study->kind) ||
        fputs(",\"source_ref\":", stream) < 0 || !write_string(stream, study->source_ref) ||
        fputs("},\"inputs\":{", stream) < 0) { return 0; }
    for (size_t i = 0U; i < FIELD_COUNT; ++i) {
        double value;
        memcpy(&value, (const unsigned char *)&study->input + fields[i].offset, sizeof(value));
        if (fprintf(stream, "%s\"%s\":%.17g", i == 0U ? "" : ",", fields[i].name, value) < 0) { return 0; }
    }
    if (fprintf(stream, "},\"flows\":{\"fuel_mass_flow_kg_per_s\":%.17g,\"oxidizer_mass_flow_kg_per_s\":%.17g,"
        "\"branch_mass_flow_kg_per_s\":%.17g,\"branch_fuel_mass_flow_kg_per_s\":%.17g,\"branch_oxidizer_mass_flow_kg_per_s\":%.17g,"
        "\"main_mass_flow_kg_per_s\":%.17g,\"main_fuel_mass_flow_kg_per_s\":%.17g,\"main_oxidizer_mass_flow_kg_per_s\":%.17g,"
        "\"main_oxidizer_fuel_ratio\":%.17g,\"external_mass_flow_kg_per_s\":%.17g,\"returned_mass_flow_kg_per_s\":%.17g},"
        "\"pumps\":{\"fuel\":", result->fuel_mass_flow_kg_per_s, result->oxidizer_mass_flow_kg_per_s,
        result->branch_mass_flow_kg_per_s, result->branch_fuel_mass_flow_kg_per_s, result->branch_oxidizer_mass_flow_kg_per_s,
        result->main_mass_flow_kg_per_s, result->main_fuel_mass_flow_kg_per_s, result->main_oxidizer_mass_flow_kg_per_s,
        result->main_oxidizer_fuel_ratio, result->external_mass_flow_kg_per_s, result->returned_mass_flow_kg_per_s) < 0 ||
        !write_pump(stream, &result->fuel_pump) || fputs(",\"oxidizer\":", stream) < 0 || !write_pump(stream, &result->oxidizer_pump) ||
        fputs("},\"turbine\":{\"inlet\":", stream) < 0 || !write_gas(stream, &result->turbine.inlet) ||
        fputs(",\"isentropic_outlet\":", stream) < 0 || !write_gas(stream, &result->turbine.isentropic_outlet) ||
        fputs(",\"outlet\":", stream) < 0 || !write_gas(stream, &result->turbine.outlet) ||
        fprintf(stream, ",\"specific_work_j_per_kg\":%.17g,\"entropy_generation_j_per_kg_k\":%.17g,"
                        "\"efficiency_residual_j_per_kg\":%.17g},\"main_nozzle\":",
            result->turbine.specific_work_j_per_kg, result->turbine.entropy_generation_j_per_kg_k, result->turbine.efficiency_residual_j_per_kg) < 0 ||
        !write_nozzle(stream, &result->main_nozzle) || fputs(",\"branch_nozzle\":", stream) < 0) { return 0; }
    if (result->branch_nozzle_active ? !write_nozzle(stream, &result->branch_nozzle) : fputs("null", stream) < 0) { return 0; }
    return fprintf(stream, ",\"performance\":{\"main_thrust_n\":%.17g,\"branch_thrust_n\":%.17g,\"total_thrust_n\":%.17g,"
        "\"main_throat_area_m2\":%.17g,\"branch_throat_area_m2\":%.17g,\"main_effective_velocity_m_per_s\":%.17g,"
        "\"engine_effective_velocity_m_per_s\":%.17g,\"engine_specific_impulse_s\":%.17g},"
        "\"energy\":{\"pump_power_w\":%.17g,\"turbine_power_w\":%.17g,\"mechanical_loss_w\":%.17g,"
        "\"generator_required_heat_w\":%.17g,\"chamber_required_heat_w\":%.17g,"
        "\"inlet_enthalpy_rate_w\":%.17g,\"exit_total_enthalpy_rate_w\":%.17g},"
        "\"diagnostics\":{\"mass_residual_kg_per_s\":%.17g,\"shaft_residual_w\":%.17g,\"energy_residual_w\":%.17g,"
        "\"mass_relative_residual\":%.17g,\"shaft_relative_residual\":%.17g,\"energy_relative_residual\":%.17g},"
        "\"limitations\":[\"Prescribed thermal states and feed density/enthalpy, not an adiabatic or real-engine cycle.\","
        "\"Required heat exchange is inferred bookkeeping, not independently validated combustion heat.\","
        "\"No turbine return, liquid property solver, condensed phase, cooling, transient or pump maps.\","
        "\"Matched/underexpanded inviscid frozen nozzles only; no shocks or separation.\"]}\n",
        result->main_thrust_n, result->branch_thrust_n, result->total_thrust_n,
        result->main_throat_area_m2, result->branch_throat_area_m2, result->main_effective_velocity_m_per_s,
        result->engine_effective_velocity_m_per_s, result->engine_specific_impulse_s,
        result->pump_power_w, result->turbine_power_w, result->mechanical_loss_w,
        result->generator_heat_w, result->chamber_heat_w, result->inlet_enthalpy_rate_w, result->exit_total_enthalpy_rate_w,
        result->mass_residual_kg_per_s, result->shaft_residual_w, result->energy_residual_w,
        result->mass_relative_residual, result->shaft_relative_residual, result->energy_relative_residual) >= 0;
}
RpStatus rp_cycle_case_run(const char *utf8_path, FILE *stream, RpError *error)
{
    RpCycleCase study;
    RpCycleResult result;
    RpStatus status;
    if (stream == NULL) { return rp_error_set(error, RP_INVALID_ARGUMENT, "Cycle output stream is required."); }
    status = rp_cycle_case_load(utf8_path, &study, error);
    if (status == RP_OK) { status = rp_cycle_solve_prescribed(&study.input, NULL, &result, error); }
    if (status != RP_OK) { return status; }
    if (!write_report(stream, &study, &result)) { return rp_error_set(error, RP_IO_ERROR, "Cannot write cycle JSON report."); }
    rp_error_clear(error); return RP_OK;
}
