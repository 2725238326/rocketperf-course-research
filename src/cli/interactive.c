#include "interactive.h"
#include "arguments.h"
#include "text_report.h"
#include "rocketperf/combustion.h"
#include "rocketperf/frozen_nozzle.h"
#include "rocketperf/liquid_combustion.h"
#include "rocketperf/liquid_feed.h"
#include "rocketperf/liquid_nozzle.h"
#include "rocketperf/nozzle.h"
#include "rocketperf/propellant_study.h"
#include "rocketperf/thermo.h"
#include "rocketperf/version.h"

#include <ctype.h>
#include <stdio.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#endif

#define RP_MENU_LINE 128U

typedef enum { RP_PROMPT_VALUE = 1, RP_PROMPT_CANCEL = -1, RP_PROMPT_EOF = 0 } RpPromptStatus;

/* Reads one stdin line; 1=line, 0=EOF. The trailing newline is stripped. */
static int menu_read_line(char *buffer, size_t capacity)
{
    size_t length;
    if (fgets(buffer, (int)capacity, stdin) == NULL) { return 0; }
    length = strlen(buffer);
    while (length > 0U && (buffer[length - 1U] == '\n' || buffer[length - 1U] == '\r')) {
        buffer[--length] = '\0';
    }
    return 1;
}

static int canceled(const char *text)
{
    return text[0] == 'q' || text[0] == 'Q';
}

/* Prints "  label (unit) [default]: " and reads a line; empty keeps default,
 * q/Q cancels, EOF returns RP_PROMPT_EOF. */
static RpPromptStatus prompt_raw(const char *label, const char *unit, const char *fallback,
                                 char *buffer, size_t capacity)
{
    if (unit != NULL && unit[0] != '\0') {
        (void)fprintf(stdout, "  %s (%s) [%s]: ", label, unit, fallback);
    } else {
        (void)fprintf(stdout, "  %s [%s]: ", label, fallback);
    }
    (void)fflush(stdout);
    if (!menu_read_line(buffer, capacity)) { return RP_PROMPT_EOF; }
    if (canceled(buffer)) { return RP_PROMPT_CANCEL; }
    return RP_PROMPT_VALUE;
}

static RpPromptStatus prompt_number(const char *label, const char *unit, double fallback,
                                    double *output)
{
    char buffer[RP_MENU_LINE];
    char fallback_text[32];
    (void)snprintf(fallback_text, sizeof(fallback_text), "%.6g", fallback);
    for (;;) {
        const RpPromptStatus status = prompt_raw(label, unit, fallback_text, buffer, sizeof(buffer));
        const char *next;
        double value;
        if (status != RP_PROMPT_VALUE) { return status; }
        if (buffer[0] == '\0') { *output = fallback; return RP_PROMPT_VALUE; }
        if (rp_cli_parse_decimal(buffer, &next, &value)) {
            while (isspace((unsigned char)*next)) { ++next; }
            if (*next == '\0') { *output = value; return RP_PROMPT_VALUE; }
        }
        (void)fputs("  无效数值,请重新输入 (q 取消)。\n", stdout);
    }
}

static RpPromptStatus prompt_choice(const char *label, int minimum, int maximum, int *output)
{
    double value;
    const RpPromptStatus status = prompt_number(label, "", (double)minimum, &value);
    if (status != RP_PROMPT_VALUE) { return status; }
    if (value < (double)minimum || value > (double)maximum || value != (double)(int)value) {
        (void)fputs("  选项超出范围。\n", stdout);
        return RP_PROMPT_CANCEL;
    }
    *output = (int)value;
    return RP_PROMPT_VALUE;
}

static RpPromptStatus prompt_word(const char *label, const char *fallback,
                                  char *output, size_t capacity)
{
    char buffer[RP_MENU_LINE];
    const RpPromptStatus status = prompt_raw(label, "", fallback, buffer, sizeof(buffer));
    if (status != RP_PROMPT_VALUE) { return status; }
    if (buffer[0] == '\0') {
        if (strlen(fallback) >= capacity) { return RP_PROMPT_CANCEL; }
        strcpy(output, fallback);
        return RP_PROMPT_VALUE;
    }
    if (strlen(buffer) >= capacity) {
        (void)fputs("  输入过长。\n", stdout);
        return RP_PROMPT_CANCEL;
    }
    strcpy(output, buffer);
    return RP_PROMPT_VALUE;
}

static void print_failure(RpStatus status, const RpError *error)
{
    (void)fprintf(stdout, "  失败 (%s): %s\n", rp_status_name(status), error->message);
}

static int report_failed(void)
{
    return ferror(stdout) != 0;
}

/* Shared fixed-geometry tail: chamber result -> frozen nozzle -> text. */
static int write_chamber_and_nozzle(const RpCombustionResult *chamber,
                                    double area_ratio, double ambient_pa, double throat_m2,
                                    const char *limit)
{
    RpFrozenNozzleInput nozzle = {0};
    RpFrozenNozzleFixedResult geometry;
    RpError error = {0};
    RpStatus status;
    if (!rp_text_mixture(stdout, "燃烧室产物", &chamber->gas) ||
        !rp_text_chamber_diagnostics(stdout, chamber)) { return -1; }
    nozzle.chamber_temperature_k = chamber->gas.temperature_k;
    nozzle.chamber_pressure_pa = chamber->gas.pressure_pa;
    memcpy(nozzle.mole_fractions, chamber->gas.mole_fractions, sizeof(nozzle.mole_fractions));
    nozzle.area_ratio = area_ratio;
    nozzle.ambient_pressure_pa = ambient_pa;
    status = rp_nozzle_solve_frozen_fixed_area(&nozzle, throat_m2, NULL, &geometry, &error);
    if (status == RP_OUT_OF_DOMAIN) {
        /* Back pressure outside the attached domain: answer with the regime
         * assessment instead of a bare rejection. */
        RpFrozenNozzleRegimeResult domain;
        RpError regime_error = {0};
        if (rp_nozzle_assess_frozen(&nozzle, throat_m2, NULL, &domain, &regime_error) != RP_OK) {
            print_failure(status, &error);
            return 0;
        }
        if (!rp_text_frozen_regime(stdout, &nozzle, &domain) ||
            !rp_text_note(stdout, limit)) { return -1; }
        return 0;
    }
    if (status != RP_OK) { print_failure(status, &error); return 0; }
    if (!rp_text_frozen_nozzle(stdout, &geometry.nozzle) ||
        !rp_text_fixed_geometry(stdout, &geometry) ||
        !rp_text_note(stdout, limit)) { return -1; }
    return 0;
}

static RpPromptStatus flow_continuous_liquid(void)
{
    double tf, pf, to, po, pc, of, ar, pa, at;
    RpContinuousLiquidFeed feed = {0};
    RpContinuousLiquidFixedResult result;
    RpError error = {0};
    RpStatus status;
#define P(field, label, unit, fallback) \
    { const RpPromptStatus s = prompt_number(label, unit, fallback, &field); \
      if (s != RP_PROMPT_VALUE) { return s; } }
    P(tf, "燃料温度 Tf", "K", 120.0) P(pf, "燃料压力 Pf", "MPa", 10.0)
    P(to, "氧化剂温度 To", "K", 100.0) P(po, "氧化剂压力 Po", "MPa", 10.0)
    P(pc, "燃烧室压力 Pc", "MPa", 10.0) P(of, "氧燃比 O/F", "", 3.4)
    P(ar, "喷管面积比 Ae/At", "", 10.0) P(pa, "环境背压 pa", "kPa", 0.0)
    P(at, "喉部面积 At", "m2", 0.01)
#undef P
    feed.dataset_id = rp_liquid_feed_dataset_id();
    feed.enthalpy_basis_id = rp_liquid_feed_enthalpy_basis_id();
    feed.fuel_phase = RP_LIQUID_SINGLE_PHASE; feed.oxidizer_phase = RP_LIQUID_SINGLE_PHASE;
    feed.fuel_temperature_k = tf; feed.fuel_pressure_pa = pf * 1e6;
    feed.oxidizer_temperature_k = to; feed.oxidizer_pressure_pa = po * 1e6;
    feed.product_pressure_pa = pc * 1e6; feed.oxidizer_fuel_mass_ratio = of;
    if (!rp_text_heading(stdout, "连续液态 CH4/O2 推力室") ||
        fprintf(stdout, "  输入: Tf=%.6g K, Pf=%.6g MPa, To=%.6g K, Po=%.6g MPa, "
                "Pc=%.6g MPa, O/F=%.6g, Ae/At=%.6g, pa=%.6g kPa, At=%.6g m2\n",
                tf, pf, to, po, pc, of, ar, pa, at) < 0) { return RP_PROMPT_EOF; }
    status = rp_ch4_o2_continuous_liquid_hp_fixed_area(&feed, ar, pa * 1e3, at,
                                                     NULL, NULL, &result, &error);
    if (status != RP_OK) { print_failure(status, &error); return RP_PROMPT_VALUE; }
    if (!rp_text_liquid_state(stdout, "燃料入口", &result.hp.inlet.fuel) ||
        !rp_text_liquid_state(stdout, "氧化剂入口", &result.hp.inlet.oxidizer) ||
        fprintf(stdout, "  入口混合焓 %.6g J/kg\n", result.hp.inlet.mixture_h_j_per_kg) < 0 ||
        write_chamber_and_nozzle(&result.hp.chamber, ar, pa * 1e3, at,
            "单相查表入口非泵后/喷注可行性;Q=0;九气相+燃烧室冻结喷管。") != 0) {
        return report_failed() ? RP_PROMPT_EOF : RP_PROMPT_VALUE;
    }
    return RP_PROMPT_VALUE;
}

static RpPromptStatus flow_anchor_liquid(void)
{
    double pc, of, ar, pa, at;
    RpCh4O2AnchorFeed feed = {0};
    RpAnchorInlet inlet = {0};
    RpCombustionResult chamber;
    RpError error = {0};
    RpStatus status;
#define P(field, label, unit, fallback) \
    { const RpPromptStatus s = prompt_number(label, unit, fallback, &field); \
      if (s != RP_PROMPT_VALUE) { return s; } }
    P(pc, "燃烧室压力 Pc", "MPa", 10.0) P(of, "氧燃比 O/F", "", 3.4)
    P(ar, "喷管面积比 Ae/At", "", 10.0) P(pa, "环境背压 pa", "kPa", 0.0)
    P(at, "喉部面积 At", "m2", 0.01)
#undef P
    feed.pressure_pa = pc * 1e6; feed.oxidizer_fuel_mass_ratio = of;
    feed.fuel_anchor_id = "CH4(L)"; feed.oxidizer_anchor_id = "O2(L)";
    feed.fuel_temperature_k = 111.643; feed.oxidizer_temperature_k = 90.170;
    feed.phase = RP_FEED_LIQUID;
    if (!rp_text_heading(stdout, "固定锚点 CH4(L)/O2(L) 推力室") ||
        fprintf(stdout, "  输入: Pc=%.6g MPa, O/F=%.6g, Ae/At=%.6g, pa=%.6g kPa, At=%.6g m2; "
                "反应物固定 CH4(L)111.643K / O2(L)90.170K\n", pc, of, ar, pa, at) < 0) {
        return RP_PROMPT_EOF;
    }
    status = rp_ch4_o2_anchor_inlet(&feed, &inlet, &error);
    if (status == RP_OK) { status = rp_ch4_o2_equilibrium_hp_anchor(&feed, NULL, &chamber, &error); }
    if (status != RP_OK) { print_failure(status, &error); return RP_PROMPT_VALUE; }
    if (fprintf(stdout, "  入口混合焓 %.6g J/kg (指定化学焓)\n",
                inlet.mixture_h_j_per_kg) < 0 ||
        write_chamber_and_nozzle(&chamber, ar, pa * 1e3, at,
            "固定指定焓非液体物性;无泵/相变;九气相+燃烧室冻结喷管。") != 0) {
        return report_failed() ? RP_PROMPT_EOF : RP_PROMPT_VALUE;
    }
    return RP_PROMPT_VALUE;
}

static RpPromptStatus flow_kerosene(void)
{
    double of, ar, pa, at;
    RpKeroseneAnchorFeed feed = {0};
    RpAnchorInlet inlet = {0};
    RpCombustionResult chamber;
    RpError error = {0};
    RpStatus status;
    (void)fputs("  固定 RP-1 方法: Pc=10 MPa, RP-1 298.15 K, O2(L) 90.170 K, O/F 2.2..4.0。\n", stdout);
#define P(field, label, unit, fallback) \
    { const RpPromptStatus s = prompt_number(label, unit, fallback, &field); \
      if (s != RP_PROMPT_VALUE) { return s; } }
    P(of, "氧燃比 O/F", "", 2.6)
    P(ar, "喷管面积比 Ae/At", "", 10.0) P(pa, "环境背压 pa", "kPa", 0.0)
    P(at, "喉部面积 At", "m2", 0.01)
#undef P
    feed.dataset_id = rp_kerosene_dataset_id();
    feed.reactants.pressure_pa = 1e7; feed.reactants.oxidizer_fuel_mass_ratio = of;
    feed.reactants.fuel_anchor_id = "RP-1"; feed.reactants.oxidizer_anchor_id = "O2(L)";
    feed.reactants.fuel_temperature_k = 298.15; feed.reactants.oxidizer_temperature_k = 90.170;
    feed.reactants.phase = RP_FEED_LIQUID;
    if (!rp_text_heading(stdout, "固定 RP-1/O2(L) 推力室") ||
        fprintf(stdout, "  输入: O/F=%.6g, Ae/At=%.6g, pa=%.6g kPa, At=%.6g m2\n",
                of, ar, pa, at) < 0) { return RP_PROMPT_EOF; }
    status = rp_kerosene_anchor_inlet(&feed, &inlet, &error);
    if (status == RP_OK) { status = rp_kerosene_equilibrium_hp_anchor(&feed, NULL, &chamber, &error); }
    if (status != RP_OK) { print_failure(status, &error); return RP_PROMPT_VALUE; }
    if (fprintf(stdout, "  入口混合焓 %.6g J/kg (指定化学焓)\n",
                inlet.mixture_h_j_per_kg) < 0 ||
        write_chamber_and_nozzle(&chamber, ar, pa * 1e3, at,
            "RP-1为具名替代物非国产煤油批次;富燃/凝聚相在方法域外。") != 0) {
        return report_failed() ? RP_PROMPT_EOF : RP_PROMPT_VALUE;
    }
    return RP_PROMPT_VALUE;
}

static RpPromptStatus flow_gas_feed(void)
{
    double pc, of, tf, to, ar, pa, at;
    RpCh4O2Feed feed = {0};
    RpCombustionResult chamber;
    RpError error = {0};
    RpStatus status;
#define P(field, label, unit, fallback) \
    { const RpPromptStatus s = prompt_number(label, unit, fallback, &field); \
      if (s != RP_PROMPT_VALUE) { return s; } }
    P(pc, "燃烧室压力 Pc", "MPa", 10.0) P(of, "氧燃比 O/F", "", 3.4)
    P(tf, "气态甲烷温度 Tf", "K", 300.0) P(to, "气态氧温度 To", "K", 300.0)
    P(ar, "喷管面积比 Ae/At", "", 10.0) P(pa, "环境背压 pa", "kPa", 0.0)
    P(at, "喉部面积 At", "m2", 0.01)
#undef P
    feed.pressure_pa = pc * 1e6; feed.oxidizer_fuel_mass_ratio = of;
    feed.fuel_temperature_k = tf; feed.oxidizer_temperature_k = to;
    feed.phase = RP_FEED_GAS;
    if (!rp_text_heading(stdout, "气态 CH4/O2 推力室") ||
        fprintf(stdout, "  输入: Pc=%.6g MPa, O/F=%.6g, Tf=%.6g K, To=%.6g K, "
                "Ae/At=%.6g, pa=%.6g kPa, At=%.6g m2\n", pc, of, tf, to, ar, pa, at) < 0) {
        return RP_PROMPT_EOF;
    }
    status = rp_ch4_o2_equilibrium_hp(&feed, NULL, &chamber, &error);
    if (status != RP_OK) { print_failure(status, &error); return RP_PROMPT_VALUE; }
    if (write_chamber_and_nozzle(&chamber, ar, pa * 1e3, at,
            "气态入口非真实供给状态;Q=0;九气相+燃烧室冻结喷管。") != 0) {
        return report_failed() ? RP_PROMPT_EOF : RP_PROMPT_VALUE;
    }
    return RP_PROMPT_VALUE;
}

static RpPromptStatus flow_chamber_performance(void)
{
    int method;
    const RpPromptStatus status = prompt_choice(
        "  入口方法 [1连续液态CH4/O2 2固定CH4(L)锚点 3固定RP-1 4气态CH4/O2]", 1, 4, &method);
    if (status != RP_PROMPT_VALUE) { return status; }
    switch (method) {
        case 1: return flow_continuous_liquid();
        case 2: return flow_anchor_liquid();
        case 3: return flow_kerosene();
        default: return flow_gas_feed();
    }
}

static RpPromptStatus flow_propellant_compare(void)
{
    double ch4_of, rp1_of, ar, pa;
    RpPropellantComparisonInput input = {0};
    RpPropellantComparisonResult result;
    RpError error = {0};
    RpStatus status;
#define P(field, label, unit, fallback) \
    { const RpPromptStatus s = prompt_number(label, unit, fallback, &field); \
      if (s != RP_PROMPT_VALUE) { return s; } }
    P(ch4_of, "甲烷氧燃比 O/F", "", 3.4) P(rp1_of, "RP-1氧燃比 O/F", "", 2.6)
    P(ar, "喷管面积比 Ae/At", "", 10.0) P(pa, "环境背压 pa", "kPa", 0.0)
#undef P
    input.methane = (RpContinuousLiquidFeed){rp_liquid_feed_dataset_id(),
        rp_liquid_feed_enthalpy_basis_id(), RP_LIQUID_SINGLE_PHASE, RP_LIQUID_SINGLE_PHASE,
        120.0, 1e7, 100.0, 1e7, 1e7, ch4_of};
    input.kerosene = (RpKeroseneAnchorFeed){rp_kerosene_dataset_id(),
        {1e7, rp1_of, "RP-1", "O2(L)", 298.15, 90.170, RP_FEED_LIQUID}};
    input.area_ratio = ar; input.ambient_pressure_pa = pa * 1e3; input.throat_area_m2 = 0.01;
    status = rp_propellant_compare_fixed(&input, NULL, NULL, &result, &error);
    if (status != RP_OK) { print_failure(status, &error); return RP_PROMPT_VALUE; }
    if (!rp_text_propellant_comparison(stdout, &input, &result)) { return RP_PROMPT_EOF; }
    return RP_PROMPT_VALUE;
}

static RpPromptStatus flow_gas_hp(void)
{
    double pc, of, tf, to;
    RpCh4O2Feed feed = {0};
    RpCombustionResult chamber;
    RpError error = {0};
    RpStatus status;
#define P(field, label, unit, fallback) \
    { const RpPromptStatus s = prompt_number(label, unit, fallback, &field); \
      if (s != RP_PROMPT_VALUE) { return s; } }
    P(pc, "燃烧室压力 Pc", "MPa", 10.0) P(of, "氧燃比 O/F", "", 3.4)
    P(tf, "气态甲烷温度 Tf", "K", 300.0) P(to, "气态氧温度 To", "K", 300.0)
#undef P
    feed.pressure_pa = pc * 1e6; feed.oxidizer_fuel_mass_ratio = of;
    feed.fuel_temperature_k = tf; feed.oxidizer_temperature_k = to;
    feed.phase = RP_FEED_GAS;
    if (!rp_text_heading(stdout, "气态 CH4/O2 绝热燃烧 HP") ||
        fprintf(stdout, "  输入: Pc=%.6g MPa, O/F=%.6g, Tf=%.6g K, To=%.6g K\n",
                pc, of, tf, to) < 0) { return RP_PROMPT_EOF; }
    status = rp_ch4_o2_equilibrium_hp(&feed, NULL, &chamber, &error);
    if (status != RP_OK) { print_failure(status, &error); return RP_PROMPT_VALUE; }
    if (!rp_text_mixture(stdout, "燃烧室产物", &chamber.gas) ||
        !rp_text_chamber_diagnostics(stdout, &chamber) ||
        !rp_text_note(stdout, "九种中性气相受限产物;Q=0;无喷管/整机闭合。")) {
        return RP_PROMPT_EOF;
    }
    return RP_PROMPT_VALUE;
}

static RpPromptStatus flow_thermo(void)
{
    char species[32];
    double temperature;
    const RpNasa9Species *entry;
    RpThermoState state;
    RpError error = {0};
    RpStatus status;
    (void)fputs("  可查物种: H2 O2 N2 H2O CO CO2 CH4 H O OH\n", stdout);
    { const RpPromptStatus s = prompt_word("物种", "H2O", species, sizeof(species));
      if (s != RP_PROMPT_VALUE) { return s; } }
    { const RpPromptStatus s = prompt_number("温度 T", "K", 300.0, &temperature);
      if (s != RP_PROMPT_VALUE) { return s; } }
    entry = rp_thermo_find_species(species);
    if (entry == NULL) {
        (void)fputs("  失败 (out_of_domain): 固定数据集中无此物种。\n", stdout);
        return RP_PROMPT_VALUE;
    }
    status = rp_nasa9_evaluate(entry, temperature, &state, &error);
    if (status != RP_OK) { print_failure(status, &error); return RP_PROMPT_VALUE; }
    if (!rp_text_thermo_state(stdout, entry, temperature, &state) ||
        !rp_text_note(stdout, "单物种标准态理想气体物性;非燃烧平衡。")) {
        return RP_PROMPT_EOF;
    }
    return RP_PROMPT_VALUE;
}

static RpPromptStatus flow_liquid_feed(void)
{
    int fluid;
    double temperature, pressure;
    RpLiquidFeedQuery query = {0};
    RpLiquidFeedState state;
    RpError error = {0};
    RpStatus status;
    { const RpPromptStatus s = prompt_choice("流体 [1 Methane 2 Oxygen]", 1, 2, &fluid);
      if (s != RP_PROMPT_VALUE) { return s; } }
    { const RpPromptStatus s = prompt_number("温度 T", "K", fluid == 1 ? 120.0 : 100.0,
                                           &temperature);
      if (s != RP_PROMPT_VALUE) { return s; } }
    { const RpPromptStatus s = prompt_number("压力 p", "MPa", 10.0, &pressure);
      if (s != RP_PROMPT_VALUE) { return s; } }
    query.dataset_id = rp_liquid_feed_dataset_id();
    query.fluid_id = fluid == 1 ? "Methane" : "Oxygen";
    query.phase = RP_LIQUID_SINGLE_PHASE;
    query.temperature_k = temperature; query.pressure_pa = pressure * 1e6;
    status = rp_liquid_feed_evaluate(&query, &state, &error);
    if (status != RP_OK) { print_failure(status, &error); return RP_PROMPT_VALUE; }
    if (!rp_text_liquid_state(stdout, fluid == 1 ? "甲烷" : "氧", &state) ||
        !rp_text_note(stdout, "单相离线参考表:CH4 100-140K/O2 80-110K,1-20MPa;无闪蒸/泵。")) {
        return RP_PROMPT_EOF;
    }
    return RP_PROMPT_VALUE;
}

static RpPromptStatus flow_ideal_nozzle(void)
{
    RpNozzleInput input = {0};
    RpNozzleResult result;
    RpError error = {0};
    RpStatus status;
#define P(field, label, unit, fallback) \
    { const RpPromptStatus s = prompt_number(label, unit, fallback, &field); \
      if (s != RP_PROMPT_VALUE) { return s; } }
    P(input.gamma, "比热比 gamma", "", 1.4)
    P(input.gas_constant_j_kg_k, "气体常数 R", "J/(kg·K)", 287.0)
    P(input.stagnation_temperature_k, "总温 T0", "K", 300.0)
    P(input.stagnation_pressure_pa, "总压 P0", "MPa", 1.0)
    P(input.throat_area_m2, "喉部面积 At", "m2", 0.001)
    P(input.area_ratio, "面积比 Ae/At", "", 1.6875)
    P(input.ambient_pressure_pa, "环境背压 pa", "kPa", 0.0)
#undef P
    input.stagnation_pressure_pa *= 1e6; input.ambient_pressure_pa *= 1e3;
    status = rp_nozzle_solve_ideal(&input, NULL, &result, &error);
    if (status == RP_OUT_OF_DOMAIN) {
        RpNozzleRegimeResult domain;
        RpError regime_error = {0};
        if (rp_nozzle_assess_ideal(&input, NULL, &domain, &regime_error) != RP_OK) {
            print_failure(status, &error);
            return RP_PROMPT_VALUE;
        }
        if (!rp_text_ideal_regime(stdout, &input, &domain)) { return RP_PROMPT_EOF; }
        return RP_PROMPT_VALUE;
    }
    if (status != RP_OK) { print_failure(status, &error); return RP_PROMPT_VALUE; }
    if (!rp_text_ideal_result(stdout, &input, &result)) { return RP_PROMPT_EOF; }
    return RP_PROMPT_VALUE;
}

int rp_cli_cases(FILE *stream)
{
    return fputs(
        "内置算例 (.ini, 研究/教学场景;非真实型号输入):\n"
        "  cases/benchmarks/air_mach2_vacuum.ini   L0理想喷管 Mach2真空基准\n"
        "      rocketperf run cases/benchmarks/air_mach2_vacuum.ini\n"
        "  cases/benchmarks/air_mach2_ambient.ini  L0理想喷管 大气背压基准\n"
        "      rocketperf run cases/benchmarks/air_mach2_ambient.ini\n"
        "  cases/benchmarks/prescribed_cycle.ini   给定热状态外排循环原型\n"
        "      rocketperf cycle prescribed cases/benchmarks/prescribed_cycle.ini\n"
        "  cases/research/propellant_comparison.ini  甲烷/RP-1同几何成对算例\n"
        "      rocketperf study propellants --case cases/research/propellant_comparison.ini\n"
        "  cases/research/s1_area_ratio_ambient.ini  面积比-背压网格研究\n"
        "      rocketperf study area-ratio-ambient cases/research/s1_area_ratio_ambient.ini\n"
        "  cases/research/s3_sealevel_regime.ini      海平面过膨胀域评估(研究场景)\n"
        "      rocketperf nozzle regime cases/research/s3_sealevel_regime.ini\n",
        stream) >= 0 && fflush(stream) == 0;
}

static void print_menu(void)
{
    (void)fprintf(stdout,
        "\n================ rocketperf %s 交互模式 ================\n"
        "  课程方法算例计算;非真实型号性能验证。q 取消当前输入。\n"
        "  [1] 推力室性能 (入口方法 -> Tc,c*,mdot,F,Isp)\n"
        "  [2] 甲烷 / RP-1 同条件对比\n"
        "  [3] 气态 CH4/O2 绝热燃烧 HP\n"
        "  [4] NASA9 物性查询\n"
        "  [5] 液体入口状态查询 (CH4/O2 单相表)\n"
        "  [6] 理想气体喷管 L0 (教学算例)\n"
        "  [7] 内置算例清单\n"
        "  [0] 退出\n", RP_VERSION);
}

RpConsoleCodepage rp_cli_console_utf8(void)
{
#ifdef _WIN32
    const RpConsoleCodepage previous = {GetConsoleOutputCP(), GetConsoleCP()};
    (void)SetConsoleOutputCP(CP_UTF8);
    (void)SetConsoleCP(CP_UTF8);
    return previous;
#else
    const RpConsoleCodepage previous = {0U, 0U};
    return previous;
#endif
}

void rp_cli_console_restore(RpConsoleCodepage previous)
{
#ifdef _WIN32
    (void)SetConsoleOutputCP(previous.output_cp);
    (void)SetConsoleCP(previous.input_cp);
#else
    (void)previous;
#endif
}

int rp_cli_interactive(void)
{
    char line[RP_MENU_LINE];
    const RpConsoleCodepage previous = rp_cli_console_utf8();
    (void)fputs("rocketperf 交互模式:输入数字选择功能,参数行直接回车取默认值。\n", stdout);
    for (;;) {
        int choice = -1;
        RpPromptStatus status;
        print_menu();
        (void)fputs("选择 [0-7]: ", stdout);
        (void)fflush(stdout);
        if (!menu_read_line(line, sizeof(line))) { break; }
        if (canceled(line)) { break; }
        if (line[0] == '\0') { continue; }
        {
            const char *next;
            double value;
            if (!rp_cli_parse_decimal(line, &next, &value) || *next != '\0' ||
                value != (double)(int)value || value < 0.0 || value > 7.0) {
                (void)fputs("  无效选择。\n", stdout);
                continue;
            }
            choice = (int)value;
        }
        switch (choice) {
            case 0: status = RP_PROMPT_EOF; break;
            case 1: status = flow_chamber_performance(); break;
            case 2: status = flow_propellant_compare(); break;
            case 3: status = flow_gas_hp(); break;
            case 4: status = flow_thermo(); break;
            case 5: status = flow_liquid_feed(); break;
            case 6: status = flow_ideal_nozzle(); break;
            default:
                if (!rp_cli_cases(stdout)) { status = RP_PROMPT_EOF; }
                else { status = RP_PROMPT_VALUE; }
                break;
        }
        if (status == RP_PROMPT_EOF || report_failed()) { break; }
    }
    (void)fputs("退出交互模式。\n", stdout);
    (void)fflush(stdout);
    rp_cli_console_restore(previous);
    return 0;
}
