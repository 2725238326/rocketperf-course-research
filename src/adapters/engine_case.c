#include "engine_case.h"
#include "case_file.h"
#include "case_text.h"
#include "combustion_report.h"
#include "text_report.h"
#include "rocketperf/liquid_feed.h"
#include "rocketperf/version.h"

#include <stddef.h>
#include <string.h>

typedef struct { const char *name; size_t offset; } EngineField;
#define INPUT(member) {#member, offsetof(RpEngineCycleCase, input) + offsetof(RpEngineCycleInput, member)}
#define PUMP(propellant, member) {#propellant "_pump_" #member, offsetof(RpEngineCycleCase, input) + offsetof(RpEngineCycleInput, propellant) + offsetof(RpCyclePropellant, pump) + offsetof(RpLiquidPumpInput, member)}
#define CASE(member) {#member, offsetof(RpEngineCycleCase, member)}
static const EngineField fields[] = {
    INPUT(total_mass_flow_kg_per_s), INPUT(overall_oxidizer_fuel_ratio),
    PUMP(fuel, inlet_pressure_pa), PUMP(fuel, outlet_pressure_pa), PUMP(fuel, efficiency),
    PUMP(oxidizer, inlet_pressure_pa), PUMP(oxidizer, outlet_pressure_pa), PUMP(oxidizer, efficiency),
    CASE(fuel_temperature_k), CASE(oxidizer_temperature_k), CASE(fuel_density_override_kg_per_m3),
    INPUT(chamber_pressure_pa), INPUT(main_area_ratio), INPUT(preburner_pressure_pa), INPUT(preburner_oxidizer_fuel_ratio),
    INPUT(turbine_outlet_pressure_pa), INPUT(turbine_efficiency), INPUT(shaft_efficiency), INPUT(auxiliary_power_w),
    INPUT(maximum_branch_fraction), INPUT(pump_to_chamber_drop_pa), INPUT(pump_to_preburner_drop_pa),
    INPUT(return_pressure_drop_pa), INPUT(branch_area_ratio), INPUT(branch_axial_projection), INPUT(ambient_pressure_pa)
};
#undef INPUT
#undef PUMP
#undef CASE
static const char *const metadata[] = {"schema_version", "case_id", "case_kind", "model", "object_ref", "source_ref", "cycle_evidence", "feed_model", "staged_combustion"};
#define FIELD_COUNT (sizeof(fields) / sizeof(fields[0]))
#define META_COUNT (sizeof(metadata) / sizeof(metadata[0]))

static RpStatus metadata_value(RpEngineCycleCase *study, size_t field, const char *value, unsigned int line, RpError *error)
{
    char *target = NULL;
    size_t capacity = 0U;
    switch (field) {
    case 0U: if (strcmp(value, "1") != 0) { goto invalid; } break;
    case 1U: if (!rp_text_identifier(value)) { goto invalid; } target = study->id; capacity = sizeof(study->id); break;
    case 2U: if (strcmp(value, "research_scenario") != 0) { goto invalid; } break;
    case 3U: if (strcmp(value, RP_ADIABATIC_CYCLE_MODEL) != 0) { goto invalid; } break;
    case 4U: if (!rp_text_identifier(value)) { goto invalid; } target = study->object_ref; capacity = sizeof(study->object_ref); break;
    case 5U: target = study->source_ref; capacity = sizeof(study->source_ref); break;
    case 6U:
        if (strcmp(value, "family_supported") != 0 && strcmp(value, "unresolved_scenario") != 0 && strcmp(value, "method_only") != 0) { goto invalid; }
        target = study->cycle_evidence; capacity = sizeof(study->cycle_evidence); break;
    case 7U:
        if (strcmp(value, "methane_liquid_table") != 0 && strcmp(value, "rp1_assigned") != 0) { goto invalid; }
        target = study->feed_model; capacity = sizeof(study->feed_model); break;
    case 8U:
        if (strcmp(value, "true") == 0) { study->input.staged_combustion = true; }
        else if (strcmp(value, "false") == 0) { study->input.staged_combustion = false; }
        else { goto invalid; }
        break;
    default: goto invalid;
    }
    if (target != NULL) {
        if (!rp_text_ascii(value, capacity)) { goto invalid; }
        (void)snprintf(target, capacity, "%s", value);
    }
    return RP_OK;
invalid:
    return rp_text_parse_failure(error, line, "Invalid cycle metadata, model, category or boolean.");
}

static RpStatus build_propellants(RpEngineCycleCase *study, RpError *error)
{
    RpCyclePropellant *fuel = &study->input.fuel;
    RpCyclePropellant *oxidizer = &study->input.oxidizer;
    RpLiquidFeedQuery query = {rp_liquid_feed_dataset_id(), "Oxygen", RP_LIQUID_SINGLE_PHASE,
                               study->oxidizer_temperature_k, oxidizer->pump.inlet_pressure_pa};
    RpLiquidFeedState oxygen, methane;
    RpStatus status = rp_liquid_feed_evaluate(&query, &oxygen, error);
    if (status != RP_OK) { return status; }
    fuel->basis = RP_ENTHALPY_NASA9_CEA_V334;
    oxidizer->basis = RP_ENTHALPY_NASA9_CEA_V334;
    oxidizer->pump.density_kg_per_m3 = oxygen.density_kg_per_m3;
    oxidizer->elements_kmol_per_kg[2] = 2.0 / rp_thermo_find_species("O2")->molar_mass_kg_per_kmol;
    if (strcmp(study->feed_model, "methane_liquid_table") == 0) {
        if (study->fuel_density_override_kg_per_m3 != 0.0) {
            return rp_error_set(error, RP_OUT_OF_DOMAIN, "Methane liquid-table feed does not accept a density override.");
        }
        query.fluid_id = "Methane";
        query.temperature_k = study->fuel_temperature_k;
        query.pressure_pa = fuel->pump.inlet_pressure_pa;
        status = rp_liquid_feed_evaluate(&query, &methane, error);
        if (status != RP_OK) { return status; }
        fuel->pump.density_kg_per_m3 = methane.density_kg_per_m3;
        fuel->pump.inlet_h_j_per_kg = methane.h_j_per_kg;
        oxidizer->pump.inlet_h_j_per_kg = oxygen.h_j_per_kg;
        fuel->elements_kmol_per_kg[0] = 1.0 / rp_thermo_find_species("CH4")->molar_mass_kg_per_kmol;
        fuel->elements_kmol_per_kg[1] = 4.0 * fuel->elements_kmol_per_kg[0];
    } else {
        const RpKeroseneAnchorFeed anchor = {rp_kerosene_dataset_id(), {1e7, 2.6, "RP-1", "O2(L)",
                                              study->fuel_temperature_k, study->oxidizer_temperature_k, RP_FEED_LIQUID}};
        RpAnchorInlet inlet;
        status = rp_kerosene_anchor_inlet(&anchor, &inlet, error);
        if (status != RP_OK) { return status; }
        if (study->fuel_density_override_kg_per_m3 <= 0.0) {
            return rp_error_set(error, RP_INVALID_ARGUMENT, "RP-1 cycle requires an explicitly assumed positive fuel density.");
        }
        fuel->pump.density_kg_per_m3 = study->fuel_density_override_kg_per_m3;
        fuel->pump.inlet_h_j_per_kg = inlet.fuel_h_j_per_kg;
        oxidizer->pump.inlet_h_j_per_kg = inlet.oxidizer_h_j_per_kg;
        for (unsigned int e = 0U; e < RP_CHO_ELEMENT_COUNT; ++e) {
            fuel->elements_kmol_per_kg[e] = (1.0 + 2.6) * inlet.element_inventory_kmol_per_kg[e] - 2.6 * oxidizer->elements_kmol_per_kg[e];
        }
        /* Exact absence of oxygen in the assigned C1H1.95 fuel avoids subtractive
         * roundoff masquerading as a negative elemental amount. */
        fuel->elements_kmol_per_kg[2] = 0.0;
    }
    return RP_OK;
}

RpStatus rp_engine_case_load(const char *path, RpEngineCycleCase *output, RpError *error)
{
    RpEngineCycleCase study = {0};
    unsigned char seen[META_COUNT + FIELD_COUNT] = {0};
    char buffer[512];
    unsigned int line = 0U;
    int line_status;
    RpStatus status = RP_OK;
    FILE *file;
    if (path == NULL || output == NULL) { return rp_error_set(error, RP_INVALID_ARGUMENT, "Engine case path and output are required."); }
    file = rp_fopen_utf8_read(path);
    if (file == NULL) { return rp_error_set(error, RP_IO_ERROR, "Cannot open engine cycle case."); }
    while ((line_status = rp_text_read_line(file, buffer, sizeof(buffer))) != 0) {
        char *text, *separator, *key, *value;
        size_t field, numeric;
        ++line;
        if (line > 128U || line_status < 0) { status = rp_text_parse_failure(error, line, "Line limits or embedded NUL."); break; }
        if (line == 1U) { rp_text_strip_bom(buffer); }
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
        if (field == META_COUNT + FIELD_COUNT || seen[field] != 0U) { status = rp_text_parse_failure(error, line, "Unknown or duplicate field."); break; }
        if (field < META_COUNT) { status = metadata_value(&study, field, value, line, error); }
        else {
            double number;
            if (!rp_text_decimal(value, &number)) { status = rp_text_parse_failure(error, line, "Expected finite decimal SI value."); }
            else { memcpy((unsigned char *)&study + fields[field - META_COUNT].offset, &number, sizeof(number)); }
        }
        if (status != RP_OK) { break; }
        seen[field] = 1U;
    }
    if (status == RP_OK && ferror(file)) { status = rp_error_set(error, RP_IO_ERROR, "Cannot read engine cycle case."); }
    if (fclose(file) != 0 && status == RP_OK) { status = rp_error_set(error, RP_IO_ERROR, "Cannot close engine cycle case."); }
    if (status != RP_OK) { return status; }
    for (size_t i = 0U; i < META_COUNT + FIELD_COUNT; ++i) {
        if (!seen[i]) { return rp_text_parse_failure(error, line, "Missing required field(s)."); }
    }
    status = build_propellants(&study, error);
    if (status != RP_OK) { return status; }
    *output = study; rp_error_clear(error); return RP_OK;
}

static int json_propellant(FILE *stream, const RpCyclePropellant *feed)
{
    return fprintf(stream, "{\"density_kg_per_m3\":%.17g,\"inlet_h_j_per_kg\":%.17g,\"basis\":\"NASA9_CEA_v334\","
                   "\"elements_kmol_per_kg\":[%.17g,%.17g,%.17g]}", feed->pump.density_kg_per_m3,
                   feed->pump.inlet_h_j_per_kg, feed->elements_kmol_per_kg[0], feed->elements_kmol_per_kg[1], feed->elements_kmol_per_kg[2]) >= 0;
}

static int json_pump(FILE *stream, const RpLiquidPumpResult *pump)
{
    return fprintf(stream, "{\"specific_work_j_per_kg\":%.17g,\"shaft_power_w\":%.17g,\"outlet_h_j_per_kg\":%.17g,\"energy_residual_w\":%.17g}",
                   pump->specific_work_j_per_kg, pump->shaft_power_w, pump->outlet_h_j_per_kg, pump->energy_residual_w) >= 0;
}

static int json_hp(FILE *stream, const RpCombustionResult *hp)
{
    return fputs("{\"gas\":", stream) >= 0 && rp_report_write_mixture(stream, &hp->gas) &&
        rp_report_write_diagnostics(stream, hp) && fputc('}', stream) != EOF;
}

static int json_nozzle(FILE *stream, const RpFrozenNozzleResult *nozzle)
{
    return fputs("{\"chamber\":", stream) >= 0 && rp_report_write_mixture(stream, &nozzle->chamber) &&
        rp_report_write_frozen_report(stream, nozzle) && fputc('}', stream) != EOF;
}

#define BALANCE(member) {#member, offsetof(RpCycleResult, member)}
static const EngineField balance_fields[] = {
    BALANCE(fuel_mass_flow_kg_per_s), BALANCE(oxidizer_mass_flow_kg_per_s), BALANCE(branch_mass_flow_kg_per_s),
    BALANCE(branch_fuel_mass_flow_kg_per_s), BALANCE(branch_oxidizer_mass_flow_kg_per_s), BALANCE(returned_mass_flow_kg_per_s),
    BALANCE(external_mass_flow_kg_per_s), BALANCE(main_mass_flow_kg_per_s), BALANCE(main_fuel_mass_flow_kg_per_s),
    BALANCE(main_oxidizer_mass_flow_kg_per_s), BALANCE(main_oxidizer_fuel_ratio), BALANCE(turbine_power_w), BALANCE(pump_power_w),
    BALANCE(mechanical_loss_w), BALANCE(generator_heat_w), BALANCE(chamber_heat_w), BALANCE(inlet_enthalpy_rate_w), BALANCE(exit_total_enthalpy_rate_w),
    BALANCE(main_throat_area_m2), BALANCE(branch_throat_area_m2), BALANCE(main_thrust_n), BALANCE(branch_thrust_n), BALANCE(total_thrust_n),
    BALANCE(main_effective_velocity_m_per_s), BALANCE(engine_effective_velocity_m_per_s), BALANCE(engine_specific_impulse_s),
    BALANCE(mass_residual_kg_per_s), BALANCE(shaft_residual_w), BALANCE(energy_residual_w),
    BALANCE(mass_relative_residual), BALANCE(shaft_relative_residual), BALANCE(energy_relative_residual)
};
#undef BALANCE

static int json_report(FILE *stream, const RpEngineCycleCase *study, const RpEngineCycleResult *result)
{
    const RpCycleResult *balance = &result->balance;
    if (fprintf(stream, "{\"schema_version\":1,\"program_version\":\"%s\",\"model\":\"%s\",\"dataset_id\":\"%s\","
                       "\"architecture\":\"%s\",\"case\":{\"id\":", RP_VERSION, RP_ADIABATIC_CYCLE_MODEL, rp_thermo_dataset_id(),
                       study->input.staged_combustion ? "all_oxidizer_staged_combustion" : "gas_generator_external") < 0 ||
        !rp_text_write_json_string(stream, study->id) || fputs(",\"kind\":\"research_scenario\",\"object_ref\":", stream) < 0 || !rp_text_write_json_string(stream, study->object_ref) ||
        fputs(",\"cycle_evidence\":", stream) < 0 || !rp_text_write_json_string(stream, study->cycle_evidence) ||
        fputs(",\"source_ref\":", stream) < 0 || !rp_text_write_json_string(stream, study->source_ref) || fputs("},\"inputs\":{\"feed_model\":", stream) < 0 ||
        !rp_text_write_json_string(stream, study->feed_model) || fprintf(stream, ",\"staged_combustion\":%s", study->input.staged_combustion ? "true" : "false") < 0) { return 0; }
    for (size_t i = 0U; i < FIELD_COUNT; ++i) {
        double value;
        memcpy(&value, (const unsigned char *)study + fields[i].offset, sizeof(value));
        if (fprintf(stream, ",\"%s\":%.17g", fields[i].name, value) < 0) { return 0; }
    }
    if (fputs("},\"feed_states\":{\"fuel\":", stream) < 0 || !json_propellant(stream, &study->input.fuel) ||
        fputs(",\"oxidizer\":", stream) < 0 || !json_propellant(stream, &study->input.oxidizer) ||
        fputs("},\"pumps\":{\"fuel\":", stream) < 0 || !json_pump(stream, &balance->fuel_pump) ||
        fputs(",\"oxidizer\":", stream) < 0 || !json_pump(stream, &balance->oxidizer_pump) ||
        fputs("},\"preburner\":", stream) < 0 || !json_hp(stream, &result->preburner) ||
        fputs(",\"chamber\":", stream) < 0 || !json_hp(stream, &result->chamber) ||
        fputs(",\"turbine\":{\"inlet\":", stream) < 0 || !rp_report_write_mixture(stream, &balance->turbine.inlet) ||
        fputs(",\"isentropic_outlet\":", stream) < 0 || !rp_report_write_mixture(stream, &balance->turbine.isentropic_outlet) ||
        fputs(",\"outlet\":", stream) < 0 || !rp_report_write_mixture(stream, &balance->turbine.outlet) ||
        fprintf(stream, ",\"specific_work_j_per_kg\":%.17g,\"efficiency_residual_j_per_kg\":%.17g,\"entropy_generation_j_per_kg_k\":%.17g},\"main_nozzle\":",
                balance->turbine.specific_work_j_per_kg, balance->turbine.efficiency_residual_j_per_kg, balance->turbine.entropy_generation_j_per_kg_k) < 0 ||
        !json_nozzle(stream, &balance->main_nozzle) || fputs(",\"branch_nozzle\":", stream) < 0) { return 0; }
    if (balance->branch_nozzle_active ? !json_nozzle(stream, &balance->branch_nozzle) : fputs("null", stream) < 0) { return 0; }
    if (fputs(",\"balance\":{", stream) < 0) { return 0; }
    for (size_t i = 0U; i < sizeof(balance_fields) / sizeof(balance_fields[0]); ++i) {
        double value;
        memcpy(&value, (const unsigned char *)balance + balance_fields[i].offset, sizeof(value));
        if (fprintf(stream, "%s\"%s\":%.17g", i == 0U ? "" : ",", balance_fields[i].name, value) < 0) { return 0; }
    }
    return fprintf(stream, "},\"mixing\":{\"h_j_per_kg\":%.17g,\"elements_kmol_per_kg\":[%.17g,%.17g,%.17g]},"
                   "\"diagnostics\":{\"preburner_enthalpy_residual_w\":%.17g,\"chamber_enthalpy_residual_w\":%.17g,"
                   "\"exit_element_relative_residual\":[%.17g,%.17g,%.17g],\"turbine_pressure_iterations\":%u},"
                   "\"limitations\":[\"Research inputs, not calibrated flight-engine performance.\","
                   "\"Nine ideal CHO gases, HP 1000..6000 K; no carbon condensation or low-temperature preburner coverage.\","
                   "\"Constant-density pumps, frozen turbine/nozzles, single shaft, Q=0; no cooling, maps or transients.\","
                   "\"RP-1 is an assigned surrogate; its feed enthalpies have no liquid pressure correction.\","
                   "\"Separate external nozzle does not reproduce TQ-15A extension mixing.\","
                   "\"Mass flow sizes nozzle geometry; matched/underexpanded domain only.\"]}\n",
                   result->main_inlet_h_j_per_kg, result->main_elements_kmol_per_kg[0], result->main_elements_kmol_per_kg[1], result->main_elements_kmol_per_kg[2],
                   result->preburner_enthalpy_residual_w, result->chamber_enthalpy_residual_w,
                   result->exit_element_relative_residual[0], result->exit_element_relative_residual[1], result->exit_element_relative_residual[2],
                   result->turbine_pressure_iterations) >= 0;
}

static int text_report(FILE *stream, const RpEngineCycleCase *study, const RpEngineCycleResult *result)
{
    const RpCycleResult *balance = &result->balance;
    return rp_text_heading(stream, study->input.staged_combustion ? "富氧补燃循环 · 绝热研究算例" : "燃气发生器开式循环 · 绝热研究算例") &&
        fprintf(stream, "  算例: %s\n  研究对象: %s\n  循环证据: %s\n  来源: %s\n  入口模型: %s\n",
                study->id, study->object_ref, study->cycle_evidence, study->source_ref, study->feed_model) >= 0 &&
        rp_text_value(stream, "预燃室/发生器温度", result->preburner.gas.temperature_k, "K") &&
        rp_text_value(stream, "主燃烧室温度", result->chamber.gas.temperature_k, "K") &&
        rp_text_value(stream, "涡轮出口压力", balance->turbine.outlet.pressure_pa / 1e6, "MPa") &&
        rp_text_value(stream, "泵轴功率", balance->pump_power_w / 1e6, "MW") &&
        rp_text_value(stream, "发生器/预燃室流量", balance->branch_mass_flow_kg_per_s, "kg/s") &&
        rp_text_value(stream, "回流主室流量", balance->returned_mass_flow_kg_per_s, "kg/s") &&
        rp_text_value(stream, "外排流量", balance->external_mass_flow_kg_per_s, "kg/s") &&
        rp_text_value(stream, "主室总流量(含回流)", balance->main_mass_flow_kg_per_s, "kg/s") &&
        rp_text_value(stream, "主路推力", balance->main_thrust_n / 1e3, "kN") &&
        rp_text_value(stream, "外排轴向推力", balance->branch_thrust_n / 1e3, "kN") &&
        rp_text_value(stream, "整机研究推力", balance->total_thrust_n / 1e3, "kN") &&
        rp_text_value(stream, "整机研究比冲", balance->engine_specific_impulse_s, "s") &&
        rp_text_value(stream, "求得主喉面积", balance->main_throat_area_m2, "m2") &&
        rp_text_value(stream, "轴功残差", balance->shaft_residual_w, "W") &&
        rp_text_value(stream, "全局能量残差(Q=0)", balance->energy_residual_w, "W") &&
        rp_text_note(stream, "型号用于构型背景；数值输入为独立研究假设，非首飞实机性能。") &&
        rp_text_note(stream, "九气相HP限1000–6000 K；恒密度泵/冻结膨胀，不含冷却、凝聚碳、起动和寿命。") &&
        rp_text_note(stream, "RP-1是指定替代物；长十乙二级循环身份待核；TQ-15A延伸段混合尚未模拟。");
}

RpStatus rp_engine_case_run(const char *path, FILE *stream, int text_mode, RpError *error)
{
    RpEngineCycleCase study;
    RpEngineCycleResult result;
    RpStatus status;
    if (stream == NULL) { return rp_error_set(error, RP_INVALID_ARGUMENT, "Engine report stream is required."); }
    status = rp_engine_case_load(path, &study, error);
    if (status == RP_OK) { status = rp_engine_cycle_solve(&study.input, NULL, NULL, &result, error); }
    if (status != RP_OK) { return status; }
    if (!(text_mode ? text_report(stream, &study, &result) : json_report(stream, &study, &result))) {
        return rp_error_set(error, RP_IO_ERROR, "Cannot write engine cycle report.");
    }
    rp_error_clear(error); return RP_OK;
}
